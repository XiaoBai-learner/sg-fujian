from collections.abc import AsyncIterator
import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..config import Settings
from ..infrastructure.db.session import create_session_factory
from ..infrastructure.storage import LocalStorage

_session_dependency = None
_storage_dependency = None


async def get_session() -> AsyncIterator[AsyncSession]:
    if _session_dependency is not None:
        async for session in _session_dependency():
            yield session
        return
    raise HTTPException(status_code=503, detail={"code": "database_not_configured", "message": "正式服务数据库尚未配置"})


def get_storage() -> LocalStorage:
    if _storage_dependency is not None:
        return _storage_dependency()
    raise HTTPException(status_code=503, detail={"code": "storage_not_configured", "message": "正式服务存储尚未配置"})


def configure_session_dependency(settings: Settings):
    global _session_dependency, _storage_dependency
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = create_session_factory(engine)

    async def dependency() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    _session_dependency = dependency
    _storage_dependency = lambda: LocalStorage(settings.storage_root)
    return dependency
