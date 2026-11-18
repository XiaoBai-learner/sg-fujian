from datetime import timedelta
from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_session
from ...infrastructure.db.models import AuditEventModel, UserModel, WorkspaceMemberModel, WorkspaceModel
from ...modules.identity.models import LoginSession, LoginThrottle
from ...modules.identity.security import (
    COOKIE, WORKSPACE, PASSWORD_HASHER, current_user, deny, issue_session, now,
    password_matches, user_view, verify_public_write,
)

router = APIRouter(prefix="/auth", tags=["accounts"])
accounts = APIRouter(prefix="/accounts", tags=["accounts"], dependencies=[Depends(current_user)])


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class NewAccount(LoginInput):
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("display_name")
    @classmethod
    def name(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("显示名称不合法")
        return value


class AccountEdit(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    active: bool | None = None


class PasswordInput(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


def audit(session, actor, event, target):
    session.add(AuditEventModel(workspace_id=WORKSPACE, actor_id=actor, event_type=event,
                               object_type="account", object_id=target, payload_json={}))


async def initialized(session):
    return bool(await session.scalar(select(func.count()).select_from(UserModel).where(UserModel.password_hash.is_not(None))))


async def insert_account(session, body, user_id=None):
    user = UserModel(id=user_id or str(uuid4()), external_subject="local:" + body.username,
                     username=body.username, display_name=body.display_name,
                     password_hash=await run_in_threadpool(PASSWORD_HASHER.hash, body.password),
                     active=True, created_at=now())
    session.add(user)
    session.add(WorkspaceMemberModel(workspace_id=WORKSPACE, user_id=user.id))
    return user


@router.get("/status")
async def status(response: Response, session: AsyncSession = Depends(get_session)):
    response.headers["Cache-Control"] = "no-store"
    return {"initialized": await initialized(session)}


@router.post("/setup", status_code=201)
async def setup(body: NewAccount, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    verify_public_write(request)
    if await initialized(session):
        deny(409, "already_initialized", "账户已初始化，请登录")
    workspace = await session.get(WorkspaceModel, WORKSPACE)
    # Fixed first-account ID makes concurrent initialization conflict atomically.
    user = await insert_account(session, body, "00000000-0000-4000-8000-000000000001")
    if workspace is None:
        session.add(WorkspaceModel(id=WORKSPACE, name="营销域工作区", domain="marketing"))
    audit(session, user.id, "account_initialized", user.id)
    try:
        result = await issue_session(session, user, response, request)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        deny(409, "already_initialized", "账户已初始化，请登录")
    return result


@router.post("/login")
async def login(body: LoginInput, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    verify_public_write(request)
    peer = request.client.host if request.client else "unknown"
    keys = [sha256(value.encode()).hexdigest() for value in (f"user:{body.username}", f"peer:{peer}")]
    # Persistent counter; failed attempts survive restarts and do not trust proxy headers.
    for key, limit in zip(keys, (5, 30)):
        record = await session.get(LoginThrottle, key)
        if record and record.expires_at > now() and record.attempts >= limit:
            deny(429, "login_throttled", "登录尝试过多，请在 10 分钟后重试")
        if record is None:
            session.add(LoginThrottle(key=key, attempts=1, expires_at=now() + timedelta(minutes=10)))
        elif record.expires_at <= now():
            record.attempts = 1
            record.expires_at = now() + timedelta(minutes=10)
        else:
            await session.execute(update(LoginThrottle).where(LoginThrottle.key == key).values(attempts=LoginThrottle.attempts + 1))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        deny(429, "login_throttled", "登录请求重叠，请稍后重试")
    user = await session.scalar(select(UserModel).where(UserModel.username == body.username))
    valid = await password_matches(user.password_hash if user else None, body.password)
    if not valid or user is None or not user.active or await session.get(WorkspaceMemberModel, (WORKSPACE, user.id)) is None:
        deny(401, "invalid_credentials", "账号或密码不正确，或账户已停用")
    await session.execute(delete(LoginThrottle).where(LoginThrottle.key.in_(keys)))
    result = await issue_session(session, user, response, request)
    audit(session, user.id, "account_login", user.id)
    await session.commit()
    return result


@router.get("/session")
async def get_login_session(request: Request, response: Response, user=Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return {"user": user_view(user), "csrf_token": request.state.csrf_token}


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, user=Depends(current_user), session: AsyncSession = Depends(get_session)):
    await session.execute(delete(LoginSession).where(LoginSession.token_hash == request.state.session_hash))
    audit(session, user.id, "account_logout", user.id)
    await session.commit()
    response.delete_cookie(COOKIE, path="/")


@router.post("/password", status_code=204)
async def change_password(body: PasswordInput, response: Response, user=Depends(current_user), session: AsyncSession = Depends(get_session)):
    if not await password_matches(user.password_hash, body.current_password):
        deny(422, "password_mismatch", "当前密码不正确")
    user.password_hash = await run_in_threadpool(PASSWORD_HASHER.hash, body.new_password)
    await session.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    audit(session, user.id, "password_changed", user.id)
    await session.commit()
    response.delete_cookie(COOKIE, path="/")


@accounts.get("")
async def list_accounts(session: AsyncSession = Depends(get_session)):
    rows = (await session.scalars(select(UserModel).join(WorkspaceMemberModel, WorkspaceMemberModel.user_id == UserModel.id)
                                 .where(WorkspaceMemberModel.workspace_id == WORKSPACE, UserModel.username.is_not(None))
                                 .order_by(UserModel.created_at, UserModel.username))).all()
    return {"items": [user_view(user) for user in rows]}


@accounts.post("", status_code=201)
async def create_account(body: NewAccount, user=Depends(current_user), session: AsyncSession = Depends(get_session)):
    target = await insert_account(session, body)
    audit(session, user.id, "account_created", target.id)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        deny(409, "username_exists", "账号已存在")
    return user_view(target)


@accounts.patch("/{user_id}")
async def edit_account(user_id: str, body: AccountEdit, user=Depends(current_user), session: AsyncSession = Depends(get_session)):
    target = await session.get(UserModel, user_id)
    if target is None or await session.get(WorkspaceMemberModel, (WORKSPACE, user_id)) is None:
        deny(404, "account_missing", "账户不存在")
    if user_id == user.id and body.active is False:
        deny(422, "self_disable", "不能停用当前登录账户")
    if body.display_name is not None:
        name = body.display_name.strip()
        if not name or any(ord(c) < 32 for c in name):
            deny(422, "invalid_name", "显示名称不合法")
        target.display_name = name
    if body.active is not None:
        target.active = body.active
        if not body.active:
            await session.execute(delete(LoginSession).where(LoginSession.user_id == target.id))
    audit(session, user.id, "account_updated", target.id)
    await session.commit()
    return user_view(target)
