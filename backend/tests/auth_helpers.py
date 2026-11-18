"""Test helpers authenticate explicitly; production never has an auth bypass."""
TEST_PASSWORD = "integration-password-4721"


def sign_in(client):
    status = client.get("/api/v1/auth/status")
    assert status.status_code == 200, status.text
    route = "login" if status.json()["initialized"] else "setup"
    body = {"username": "tester", "password": TEST_PASSWORD}
    if route == "setup":
        body["display_name"] = "集成测试成员"
    response = client.post(f"/api/v1/auth/{route}", json=body, headers={"X-Requested-With": "SGTrace"})
    assert response.status_code in {200, 201}, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client
