"""正式服务基线：仅验证真实入口，不引入 PoC 的角色或危险接口。"""
from fastapi.testclient import TestClient

from sgtrace_app.main import app


def test_formal_app_does_not_import_poc_runtime():
    import os
    import subprocess
    import sys
    env = {**os.environ, "PYTHONPATH": "backend/src"}
    result = subprocess.run(
        [sys.executable, "-c", "import sys; print(sys.path)"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "reference/poc" not in result.stdout


def test_health_is_served_by_the_product_application():
    with TestClient(app) as client:
        response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_retired_demo_routes_are_not_exposed():
    with TestClient(app) as client:
        assert client.post("/api/mysql/init").status_code == 404
        assert client.post("/api/app/login").status_code == 404
        assert client.get("/demo").status_code == 404
        assert client.post("/api/sources", json={}).status_code == 404
        assert client.post("/api/modeling/generate", json={}).status_code == 404
        assert client.post("/api/agent/chat", json={}).status_code == 404


def test_unimplemented_versioned_business_operations_do_not_return_fake_success():
    with TestClient(app) as client:
        assert client.post("/api/v1/modeling/generate", json={}).status_code == 404
        assert client.post("/api/v1/agent/chat", json={}).status_code == 404
