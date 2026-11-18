import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from sgtrace_app.infrastructure.db.models import Base
from sgtrace_app.infrastructure.db.session import create_session_factory
from sgtrace_app.main import app
from sgtrace_app.api.dependencies import get_session
from sgtrace_app.infrastructure.storage.local import LocalStorage
from sgtrace_app.api.dependencies import get_storage
from auth_helpers import sign_in


def test_ddl_source_refresh_and_schema_browser(tmp_path):
    asyncio.run(_run(tmp_path))


async def _run(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = create_session_factory(engine)

    async def session_override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_storage] = lambda: LocalStorage(tmp_path / "storage")
    ddl = "CREATE TABLE yx186.C_CONS (CONS_ID BIGINT NOT NULL COMMENT '客户标识', CONS_NO VARCHAR(30) COMMENT '户号', PRIMARY KEY (CONS_ID)) COMMENT='用电客户';"
    try:
        with TestClient(app) as client:
            sign_in(client)
            created = client.post("/api/v1/sources", json={"name": "DDL 文件", "kind": "ddl", "database": "yx186"})
            assert created.status_code == 201
            source_id = created.json()["id"]
            refreshed = client.post(f"/api/v1/sources/{source_id}/refresh", json={"ddl": ddl})
            assert refreshed.status_code == 200
            tables = client.get(f"/api/v1/sources/{source_id}/snapshots/1/tables").json()
            assert tables["items"][0]["name"] == "C_CONS"
            columns = client.get(f"/api/v1/sources/{source_id}/snapshots/1/tables/C_CONS/columns").json()
            assert columns["items"][1]["comment"] == "户号"
            materials = client.get("/api/v1/materials")
            assert materials.status_code == 200
            uploaded = client.post(
                "/api/v1/materials",
                content="业务字段说明".encode(),
                headers={"X-Material-Name": "%E8%AF%B4%E6%98%8E.md", "X-Material-Category": "document"},
            )
            assert uploaded.status_code == 201
            assert client.get("/api/v1/materials").json()["items"][0]["name"] == "说明.md"
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_storage, None)
        await engine.dispose()
