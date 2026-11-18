import asyncio
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from sgtrace_app.config import Settings
from sgtrace_app.infrastructure.db.models import Base, UserModel
from sgtrace_app.main import create_app

PASSWORD = "testing-password-8025"


def make_client(tmp_path):
    settings = Settings(f"sqlite+aiosqlite:///{tmp_path}/auth.db", tmp_path / "storage", "", 2000000, 1, ())

    async def create_tables():
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_tables())
    return TestClient(create_app(settings)), settings


def setup(client):
    response = client.post("/api/v1/auth/setup", json={
        "username": "owner", "display_name": "项目成员", "password": PASSWORD,
    }, headers={"X-Requested-With": "SGTrace"})
    assert response.status_code == 201, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response.json()


def test_all_business_routes_require_login_and_setup_has_no_defaults(tmp_path):
    client, _ = make_client(tmp_path)
    with client:
        assert client.get("/api/v1/auth/status").json() == {"initialized": False}
        for route in ("/api/v1/sources", "/api/v1/materials", "/api/v1/modeling/runs",
                      "/api/v1/modeling/active", "/api/v1/accounts", "/api/openapi.json"):
            assert client.get(route).status_code == 401, route
        assert client.post("/api/v1/modeling/trace", json={"fields": ["户号"]}).status_code == 401
        assert client.get("/api/healthz").status_code == 200
        session = setup(client)
        assert session["user"]["username"] == "owner"
        assert "password" not in session["user"] and "password_hash" not in session["user"]
        assert client.get("/api/v1/modeling/active").json() is None
        assert client.get("/api/v1/materials").json()["items"] == []
        assert client.get("/api/v1/sources").json()["items"] == []
        assert client.post("/api/v1/auth/setup", json={
            "username": "other", "display_name": "其他", "password": PASSWORD,
        }, headers={"X-Requested-With": "SGTrace"}).status_code == 409


def test_cookie_csrf_logout_and_password_change_revoke_sessions(tmp_path):
    client, _ = make_client(tmp_path)
    with client:
        setup(client)
        cookie = client.cookies.get("sgtrace_session")
        assert cookie and PASSWORD not in cookie
        client.headers.pop("X-CSRF-Token")
        assert client.post("/api/v1/sources", json={"name": "source", "kind": "ddl"}).status_code == 403
        session = client.get("/api/v1/auth/session").json()
        client.headers["X-CSRF-Token"] = session["csrf_token"]
        assert client.post("/api/v1/auth/logout").status_code == 204
        assert client.get("/api/v1/modeling/active").status_code == 401
        client.cookies.set("sgtrace_session", cookie)
        assert client.get("/api/v1/auth/session").status_code == 401
        client.cookies.clear()
        login = client.post("/api/v1/auth/login", json={"username": "owner", "password": PASSWORD},
                            headers={"X-Requested-With": "SGTrace"})
        assert login.status_code == 200
        assert "httponly" in login.headers["set-cookie"].lower()
        assert "samesite=strict" in login.headers["set-cookie"].lower()
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        old_cookie = client.cookies.get("sgtrace_session")
        changed = client.post("/api/v1/auth/password", json={
            "current_password": PASSWORD, "new_password": "new-secure-password-5566",
        })
        assert changed.status_code == 204
        client.cookies.set("sgtrace_session", old_cookie)
        assert client.get("/api/v1/auth/session").status_code == 401


def test_accounts_share_permissions_and_disable_revokes_access(tmp_path):
    client, _ = make_client(tmp_path)
    with client:
        owner = setup(client)["user"]
        created = client.post("/api/v1/accounts", json={
            "username": "member", "display_name": "成员二", "password": PASSWORD,
        })
        assert created.status_code == 201, created.text
        member = created.json()
        assert client.post("/api/v1/accounts", json={
            "username": "MEMBER", "display_name": "重复账户", "password": PASSWORD,
        }).status_code == 409
        assert client.patch(f'/api/v1/accounts/{owner["id"]}', json={"active": False}).status_code == 422
        assert client.patch(f'/api/v1/accounts/{member["id"]}', json={"display_name": "新名称"}).status_code == 200
        assert client.patch(f'/api/v1/accounts/{member["id"]}', json={"active": False}).status_code == 200
        client.post("/api/v1/auth/logout")
        denied = client.post("/api/v1/auth/login", json={"username": "member", "password": PASSWORD},
                             headers={"X-Requested-With": "SGTrace"})
        assert denied.status_code == 401
        login = client.post("/api/v1/auth/login", json={"username": "owner", "password": PASSWORD},
                            headers={"X-Requested-With": "SGTrace"})
        client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
        client.patch(f'/api/v1/accounts/{member["id"]}', json={"active": True})
        client.post("/api/v1/auth/logout")
        login = client.post("/api/v1/auth/login", json={"username": "member", "password": PASSWORD},
                            headers={"X-Requested-With": "SGTrace"})
        assert login.status_code == 200
        assert client.get("/api/v1/accounts").status_code == 200
        assert client.get("/api/v1/modeling/runs").status_code == 200


def test_hash_storage_expiry_origin_checks_and_login_throttle(tmp_path):
    client, settings = make_client(tmp_path)
    with client:
        assert client.post("/api/v1/auth/setup", json={
            "username": "intruder", "display_name": "x", "password": PASSWORD,
        }, headers={"Origin": "https://evil.example", "X-Requested-With": "SGTrace"}).status_code == 403
        setup(client)

        async def inspect_and_expire():
            from sqlalchemy.ext.asyncio import async_sessionmaker
            from sgtrace_app.modules.identity.models import LoginSession
            engine = create_async_engine(settings.database_url)
            async with async_sessionmaker(engine)() as session:
                user = await session.scalar(select(UserModel).where(UserModel.username == "owner"))
                assert user.password_hash.startswith("$argon2id$") and PASSWORD not in user.password_hash
                record = await session.scalar(select(LoginSession))
                assert record.token_hash != client.cookies.get("sgtrace_session")
                record.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
                await session.commit()
            await engine.dispose()

        asyncio.run(inspect_and_expire())
        assert client.get("/api/v1/auth/session").status_code == 401
        for _ in range(5):
            assert client.post("/api/v1/auth/login", json={"username": "owner", "password": "incorrect"},
                               headers={"X-Requested-With": "SGTrace"}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"username": "owner", "password": PASSWORD},
                           headers={"X-Requested-With": "SGTrace"}).status_code == 429


def test_secure_cookie_restart_disabled_session_and_password_redaction(tmp_path, monkeypatch):
    monkeypatch.setenv("SGTRACE_COOKIE_SECURE", "1")
    client, settings = make_client(tmp_path)
    client.base_url = "https://testserver"
    with client:
        value = setup(client)
        cookie = client.cookies.get("sgtrace_session")
        invalid = client.post("/api/v1/accounts", json={
            "username": "bad", "display_name": "bad", "password": "short-pass",
        })
        assert invalid.status_code == 422
        assert "short-pass" not in invalid.text
        assert client.get("/api/v1/auth/session").status_code == 200
    with TestClient(create_app(settings), base_url="https://testserver") as restarted:
        restarted.cookies.set("sgtrace_session", cookie)
        assert restarted.get("/api/v1/auth/session").json()["user"]["id"] == value["user"]["id"]
        restarted.headers["X-CSRF-Token"] = value["csrf_token"]
        added = restarted.post("/api/v1/accounts", json={
            "username": "second", "display_name": "成员二", "password": PASSWORD,
        }).json()
        with TestClient(create_app(settings), base_url="https://testserver") as second:
            login = second.post("/api/v1/auth/login", json={"username": "second", "password": PASSWORD},
                                headers={"X-Requested-With": "SGTrace"})
            assert login.status_code == 200
            assert "; secure" in login.headers["set-cookie"].lower()
            assert second.get("/api/v1/modeling/active").status_code == 200
            assert restarted.patch(f'/api/v1/accounts/{added["id"]}', json={"active": False}).status_code == 200
            assert second.get("/api/v1/modeling/active").status_code == 401


def test_csrf_forgery_and_cross_site_login_are_denied(tmp_path):
    client, _ = make_client(tmp_path)
    with client:
        setup(client)
        assert client.post("/api/v1/sources", json={"kind": "ddl", "name": "x"},
                           headers={"X-CSRF-Token": "forged"}).status_code == 403
        assert client.post("/api/v1/sources", json={"kind": "ddl", "name": "x"},
                           headers={"Origin": "http://untrusted.example"}).status_code == 403
        assert client.post("/api/v1/auth/login", json={"username": "owner", "password": PASSWORD},
                           headers={"X-Requested-With": "SGTrace", "Sec-Fetch-Site": "cross-site"}).status_code == 403
