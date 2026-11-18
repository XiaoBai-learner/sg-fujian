from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import compare_digest, token_urlsafe
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_session
from ...infrastructure.db.models import UserModel, WorkspaceMemberModel
from .models import LoginSession

COOKIE = "sgtrace_session"
WORKSPACE = "local-workspace"
PASSWORD_HASHER = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = PASSWORD_HASHER.hash(token_urlsafe(32))


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def deny(status, code, message):
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


def user_view(user):
    return {"id": user.id, "username": user.username, "display_name": user.display_name,
            "active": user.active, "created_at": user.created_at}


async def password_matches(encoded, password):
    def verify():
        try:
            return PASSWORD_HASHER.verify(encoded or DUMMY_HASH, password)
        except (VerificationError, InvalidHashError):
            return False
    return await run_in_threadpool(verify)


def verify_origin(request):
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        deny(403, "cross_site_request", "请求来源不受信任")
    if origin:
        parsed = urlsplit(origin)
        if parsed.netloc != request.headers.get("host") or parsed.scheme not in {"http", "https"}:
            deny(403, "cross_site_request", "请求来源不受信任")


def verify_public_write(request):
    verify_origin(request)
    if request.headers.get("x-requested-with") != "SGTrace":
        deny(403, "invalid_request", "请从登录页面提交")


async def current_user(request: Request, session: AsyncSession = Depends(get_session)):
    raw = request.cookies.get(COOKIE, "")
    if len(raw) < 32 or len(raw) > 128:
        deny(401, "login_required", "请先登录")
    record = await session.get(LoginSession, sha256(raw.encode()).hexdigest())
    if record is None or record.expires_at <= now():
        deny(401, "session_expired", "登录已过期，请重新登录")
    user = await session.get(UserModel, record.user_id)
    member = await session.get(WorkspaceMemberModel, (WORKSPACE, record.user_id))
    if user is None or not user.active or member is None:
        deny(401, "account_unavailable", "账户已停用或无权访问工作区")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        verify_origin(request)
        csrf = request.headers.get("x-csrf-token", "")
        if not compare_digest(csrf, record.csrf_token):
            deny(403, "csrf_required", "会话校验失败，请刷新后重试")
    request.state.user = user
    request.state.csrf_token = record.csrf_token
    request.state.session_hash = record.token_hash
    return user


async def issue_session(session, user, response: Response, request: Request):
    await session.execute(delete(LoginSession).where(LoginSession.expires_at <= now()))
    raw = token_urlsafe(32)
    csrf = token_urlsafe(32)
    session.add(LoginSession(token_hash=sha256(raw.encode()).hexdigest(), user_id=user.id,
                             csrf_token=csrf, expires_at=now() + timedelta(hours=12)))
    # HTTPS deployments set SGTRACE_COOKIE_SECURE=1; local loopback HTTP remains usable.
    secure = request.app.state.cookie_secure
    response.set_cookie(COOKIE, raw, httponly=True, secure=secure, samesite="strict",
                        max_age=12 * 3600, path="/")
    return {"user": user_view(user), "csrf_token": csrf}
