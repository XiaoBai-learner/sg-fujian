"""公网模式安全行为测试：认证、限流、禁用危险接口、信息脱敏、安全响应头。"""
import base64

import pytest
from fastapi.testclient import TestClient

from sgtrace import server

TOKEN = "test-token-not-real"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("SGTRACE_PUBLIC", "1")
    monkeypatch.setenv("SGTRACE_PUBLIC_TOKEN", TOKEN)
    server._auth_fails.clear()
    server._state["last_build"] = 0.0
    return TestClient(server.app)


def auth(user="demo", pwd=TOKEN):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()}


def test_requires_auth_everywhere(client):
    for path in ("/", "/api/status", "/static/app.js", "/api/samples", "/api/artifacts/ontology.ttl"):
        r = client.get(path)
        assert r.status_code == 401, path
        assert r.headers["www-authenticate"].startswith("Basic")
    assert client.get("/api/status", headers=auth(pwd="wrong")).status_code == 401
    assert client.get("/api/status", headers=auth(user="admin")).status_code == 401
    assert client.get("/api/status", headers={"Authorization": "Basic !!!"}).status_code == 401


def test_status_hides_internal_details(client):
    r = client.get("/api/status", headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert body["public"] is True
    assert body["ontowing"]["backend"] == ""
    assert body["mysql"]["target"] == "" and "error" not in body["mysql"]
    assert "/Users/" not in r.text


def test_dangerous_endpoints_disabled(client):
    assert client.post("/api/mysql/init", headers=auth()).status_code == 403
    assert client.get("/api/docs", headers=auth()).status_code == 404
    assert client.get("/api/openapi.json", headers=auth()).status_code == 404


def test_security_headers(client):
    r = client.get("/", headers=auth())
    assert r.status_code == 200
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_auth_failure_rate_limit(client):
    for _ in range(server.AUTH_FAIL_LIMIT):
        client.get("/api/status", headers={**auth(pwd="x"), "CF-Connecting-IP": "203.0.113.9"})
    r = client.get("/api/status", headers={**auth(), "CF-Connecting-IP": "203.0.113.9"})
    assert r.status_code == 429
    # 其他来源不受影响
    assert client.get("/api/status", headers={**auth(), "CF-Connecting-IP": "203.0.113.10"}).status_code == 200


def test_build_rate_limited(client):
    import time
    server._state["last_build"] = time.time()
    r = client.post("/api/build", json={"source": "ddl", "execute_r2rml": False, "evaluate": False}, headers=auth())
    assert r.status_code == 429


def test_qa_works_with_auth(client):
    r = client.post("/api/ask", json={"question": "户号属于什么表？"}, headers=auth())
    assert r.status_code == 200 and r.json()["answers"][0]["column"] == "yx186.C_CONS.CONS_NO"


def test_local_mode_unchanged(monkeypatch):
    monkeypatch.delenv("SGTRACE_PUBLIC", raising=False)
    c = TestClient(server.app)
    assert c.get("/api/status").status_code == 200
