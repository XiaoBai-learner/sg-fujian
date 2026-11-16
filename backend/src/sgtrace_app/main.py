"""正式 API 装配；业务接口实现后再在对应模块中注册。"""
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .api.v1.router import router as v1
from .api.dependencies import configure_session_dependency
from .config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(
        title="字段溯源工作台",
        version="1.0.0-dev",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    application.include_router(v1)
    if settings is not None:
        configure_session_dependency(settings)

    @application.get("/api/healthz", tags=["system"])
    def health():
        return {"status": "ok", "service": "sgtrace"}

    @application.get("/api/readyz", tags=["system"])
    async def ready():
        if settings is None:
            return {"status": "not_ready", "checks": {"database": "not_configured"}}
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return {"status": "ready", "checks": {"database": "ok", "storage": "ok"}}
        except Exception:
            return {"status": "not_ready", "checks": {"database": "unavailable"}}
        finally:
            await engine.dispose()

    return application


try:
    app = create_app(Settings.from_env())
except ValueError:
    app = create_app()
