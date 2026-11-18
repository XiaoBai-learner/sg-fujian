"""Exercise account lifecycle on an isolated, disposable local MySQL database."""
import asyncio
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

from sgtrace_app.config import Settings
from sgtrace_app.infrastructure.db.models import Base
from sgtrace_app.main import create_app

pytestmark = pytest.mark.skipif(os.environ.get("MYSQL_INTEGRATION") != "1", reason="requires local MySQL")


def test_mysql_account_creation_login_logout_and_duplicates(tmp_path):
    name = "sgtrace_auth_test_" + uuid4().hex[:10]
    url = URL.create("mysql+asyncmy", username=os.environ["MYSQL_USER"], password=os.environ.get("MYSQL_PASSWORD", ""),
                     host=os.environ.get("MYSQL_HOST", "127.0.0.1"), port=int(os.environ.get("MYSQL_PORT", "3306")),
                     database=name)

    async def database(create):
        engine = create_async_engine(url.set(database="mysql"))
        try:
            async with engine.begin() as connection:
                await connection.execute(text(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4" if create else f"DROP DATABASE `{name}`"))
        finally:
            await engine.dispose()
        if create:
            engine = create_async_engine(url)
            try:
                async with engine.begin() as connection:
                    await connection.run_sync(Base.metadata.create_all)
            finally:
                await engine.dispose()

    asyncio.run(database(True))
    try:
        settings = Settings(url.render_as_string(hide_password=False), tmp_path / "storage", "", 1000, 1, ())
        password = "integration-mysql-4829"
        with TestClient(create_app(settings)) as client:
            setup = client.post("/api/v1/auth/setup", json={
                "username": "first", "display_name": "首个成员", "password": password,
            }, headers={"X-Requested-With": "SGTrace"})
            assert setup.status_code == 201, setup.text
            client.headers["X-CSRF-Token"] = setup.json()["csrf_token"]
            created = client.post("/api/v1/accounts", json={
                "username": "second", "display_name": "第二成员", "password": password,
            })
            assert created.status_code == 201, created.text
            assert created.json()["created_at"]
            assert client.post("/api/v1/accounts", json={
                "username": "SECOND", "display_name": "重复", "password": password,
            }).status_code == 409
            assert client.post("/api/v1/auth/logout").status_code == 204
            logged_in = client.post("/api/v1/auth/login", json={"username": "second", "password": password},
                                    headers={"X-Requested-With": "SGTrace"})
            assert logged_in.status_code == 200, logged_in.text
            assert len(client.get("/api/v1/accounts").json()["items"]) == 2
    finally:
        asyncio.run(database(False))
