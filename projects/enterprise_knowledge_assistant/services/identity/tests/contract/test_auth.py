"""FR-005/FR-006 public auth expectations use real owned storage and committed HTTP shapes."""

from fastapi.testclient import TestClient


def test_first_login_change_and_logout(identity_client: TestClient) -> None:
    """Return a restricted session, rotate it on password change and revoke it on logout."""
    login = identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "Initial-password-123"},
        headers={"Origin": "http://localhost:8080"},
    )
    assert login.status_code == 200
    assert login.json()["account"]["must_change_password"] is True
    assert set(login.json()) == {"account", "csrf_token", "idle_expires_at"}
    csrf = login.json()["csrf_token"]
    changed = identity_client.put(
        "/api/v1/auth/password",
        json={"current_password": "Initial-password-123", "new_password": "Changed-password-456"},
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": csrf},
    )
    assert changed.status_code == 200
    assert changed.json()["account"]["must_change_password"] is False
    assert changed.json()["csrf_token"] != csrf
    current = identity_client.get("/api/v1/auth/session")
    assert current.status_code == 200
    logout = identity_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": changed.json()["csrf_token"]},
    )
    assert logout.status_code == 204
    assert identity_client.get("/api/v1/auth/session").status_code == 401


def test_unknown_fields_csrf_origin_and_generic_credentials(identity_client: TestClient) -> None:
    """Reject bypasses/unknown fields and disclose no account existence on login failure."""
    valid = {"email": "admin@example.test", "password": "Initial-password-123"}
    assert identity_client.post("/api/v1/auth/login", json=valid).status_code == 403
    assert (
        identity_client.post(
            "/api/v1/auth/login",
            json={**valid, "company_id": "forged"},
            headers={"Origin": "http://localhost:8080"},
        ).status_code
        == 400
    )
    unknown = identity_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.test", "password": "Wrong-password-123"},
        headers={"Origin": "http://localhost:8080"},
    )
    wrong = identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "Wrong-password-123"},
        headers={"Origin": "http://localhost:8080"},
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["message"] == wrong.json()["message"]
