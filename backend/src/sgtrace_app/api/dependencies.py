from collections.abc import AsyncIterator
import os

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..config import Settings
from ..infrastructure.db.session import create_session_factory
from ..infrastructure.storage import LocalStorage

async def get_session() -> AsyncIterator[AsyncSession]:
    raise HTTPException(status_code=503, detail={"code": "database_not_configured", "message": "正式服务数据库尚未配置"})


def get_storage() -> LocalStorage:
    raise HTTPException(status_code=503, detail={"code": "storage_not_configured", "message": "正式服务存储尚未配置"})


def configure_session_dependency(settings: Settings):
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = create_session_factory(engine)

    async def dependency() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    return dependency


def configure_storage_dependency(settings: Settings):
    return lambda: LocalStorage(settings.storage_root)
