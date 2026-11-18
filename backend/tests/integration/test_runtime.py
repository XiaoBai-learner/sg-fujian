"""Use the configured app and real migrations, without dependency overrides."""
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient

from sgtrace_app.config import Settings
from sgtrace_app.main import create_app
from auth_helpers import sign_in


def test_configured_service_uses_migrated_database_and_survives_restart(tmp_path, monkeypatch):
    url = f"sqlite+aiosqlite:///{tmp_path / 'formal.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    subprocess.run([sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"], check=True)
    settings = Settings(url, tmp_path / "storage", "", 1000, 1, ())
    with TestClient(create_app(settings)) as client:
        sign_in(client)
        assert client.get("/api/readyz").status_code == 200
        created = client.post("/api/v1/sources", json={"name": "真实持久化", "kind": "ddl", "database": "demo"})
        assert created.status_code == 201
        assert client.get("/api/v1/sources").json()["items"][0]["name"] == "真实持久化"
    with TestClient(create_app(settings)) as client:
        sign_in(client)
        assert client.get("/api/v1/sources").json()["items"][0]["id"] == created.json()["id"]
