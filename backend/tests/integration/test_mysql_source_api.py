import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from sgtrace_app.config import Settings
from sgtrace_app.infrastructure.db.models import Base
from sgtrace_app.main import create_app


pytestmark = pytest.mark.skipif(
    os.environ.get("MYSQL_INTEGRATION") != "1",
    reason="set MYSQL_INTEGRATION=1 to run the local MySQL source API smoke test",
)


def test_source_api_reads_local_mysql_without_mutating_it(tmp_path, monkeypatch):
    asyncio.run(_run(tmp_path, monkeypatch))


async def _run(tmp_path, monkeypatch):
    db_path = tmp_path / "formal.db"
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{db_path}",
        storage_root=tmp_path / "storage",
        app_secret="test",
        max_material_bytes=1024,
        job_poll_interval_seconds=1,
        allowed_origins=(),
    )
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
    app = create_app(settings)
    with TestClient(app) as client:
        created = client.post("/api/v1/sources", json={
            "name": "本机 MySQL",
            "kind": "mysql",
            "database": "yx186",
        })
        assert created.status_code == 201
        source_id = created.json()["id"]
        assert client.post(f"/api/v1/sources/{source_id}/test").status_code == 200
        refreshed = client.post(f"/api/v1/sources/{source_id}/refresh", json={})
        assert refreshed.status_code == 200
        tables = client.get(f"/api/v1/sources/{source_id}/snapshots/1/tables").json()["items"]
        assert len(tables) >= 10
        assert any(table["name"] == "C_CONS" for table in tables)
