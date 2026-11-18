"""正式 API 装配；业务接口实现后再在对应模块中注册。"""
import os
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .api.v1.router import router as v1
from .api.dependencies import configure_session_dependency, configure_storage_dependency, get_session, get_storage
from .config import Settings
from .modules.identity.security import current_user


def create_app(settings: Settings | None = None) -> FastAPI:
    application = FastAPI(
        title="字段溯源工作台",
        version="1.0.0-dev",
        docs_url=None,
        openapi_url=None,
        redoc_url=None,
    )
    application.state.cookie_secure = os.environ.get("SGTRACE_COOKIE_SECURE") == "1"
    application.include_router(v1)
    if settings is not None:
        application.dependency_overrides[get_session] = configure_session_dependency(settings)
        application.dependency_overrides[get_storage] = configure_storage_dependency(settings)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Validation responses must never echo passwords or uploaded document bodies.
        return JSONResponse(status_code=422, content={"detail": {
            "code": "invalid_input", "message": "输入格式不合法，请检查字段长度与必填项",
            "fields": [".".join(str(part) for part in item["loc"]) for item in error.errors()],
        }})

    @application.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @application.get("/api/openapi.json", include_in_schema=False, dependencies=[Depends(current_user)])
    async def schema():
        return application.openapi()

    @application.get("/api/docs", include_in_schema=False, dependencies=[Depends(current_user)])
    async def api_docs():
        return get_swagger_ui_html(openapi_url="/api/openapi.json", title="字段溯源 API")

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
