"""FR-004 user creation contracts derive role/company only from the authenticated admin."""

from fastapi.testclient import TestClient

ORIGIN = {"Origin": "http://localhost:8080"}
INPUT = {
    "display_name": "Client User",
    "email": "user@example.test",
    "initial_password": "Initial-user-password-123",
}


def admin_headers(client: TestClient) -> dict[str, str]:
    """Complete real first login before exercising admin-only mutations."""
    logged = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "Initial-password-123"},
        headers=ORIGIN,
    )
    changed = client.put(
        "/api/v1/auth/password",
        json={
            "current_password": "Initial-password-123",
            "new_password": "Changed-admin-password-456",
        },
        headers={**ORIGIN, "X-CSRF-Token": logged.json()["csrf_token"]},
    )
    assert changed.status_code == 200
    return {**ORIGIN, "X-CSRF-Token": changed.json()["csrf_token"]}


def test_created_user_is_owned_restricted_and_can_complete_login(
    identity_client: TestClient,
) -> None:
    """Return only safe Account fields and require the new user to change the initial password."""
    headers = admin_headers(identity_client)
    owner = identity_client.get("/api/v1/auth/session").json()["account"]
    created = identity_client.post("/api/v1/users", json=INPUT, headers=headers)
    assert created.status_code == 201
    account = created.json()
    assert account["company_id"] == owner["company_id"]
    assert account["role"] == "user" and account["must_change_password"] is True
    assert set(account) == {
        "id",
        "company_id",
        "email",
        "display_name",
        "role",
        "must_change_password",
    }
    assert (
        identity_client.post(
            "/api/v1/users", json={**INPUT, "email": "USER@example.test"}, headers=headers
        ).status_code
        == 409
    )
    identity_client.post("/api/v1/auth/logout", headers=headers)
    login = identity_client.post(
        "/api/v1/auth/login",
        json={"email": INPUT["email"], "password": INPUT["initial_password"]},
        headers=ORIGIN,
    )
    restricted = {**ORIGIN, "X-CSRF-Token": login.json()["csrf_token"]}
    assert (
        identity_client.post(
            "/api/v1/users", json={**INPUT, "email": "next@example.test"}, headers=restricted
        ).status_code
        == 403
    )
    changed = identity_client.put(
        "/api/v1/auth/password",
        json={
            "current_password": INPUT["initial_password"],
            "new_password": "Changed-user-password-456",
        },
        headers=restricted,
    )
    assert changed.status_code == 200 and changed.json()["account"]["must_change_password"] is False
    assert (
        identity_client.post(
            "/api/v1/users",
            json={**INPUT, "email": "next@example.test"},
            headers={**ORIGIN, "X-CSRF-Token": changed.json()["csrf_token"]},
        ).status_code
        == 403
    )


def test_creation_rejects_role_company_csrf_and_initial_login(identity_client: TestClient) -> None:
    """Denied and invalid requests create no partial account or privileged override."""
    assert identity_client.post("/api/v1/users", json=INPUT, headers=ORIGIN).status_code == 401
    logged = identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "Initial-password-123"},
        headers=ORIGIN,
    )
    assert (
        identity_client.post(
            "/api/v1/users",
            json=INPUT,
            headers={**ORIGIN, "X-CSRF-Token": logged.json()["csrf_token"]},
        ).status_code
        == 403
    )
    changed = identity_client.put(
        "/api/v1/auth/password",
        json={
            "current_password": "Initial-password-123",
            "new_password": "Changed-admin-password-456",
        },
        headers={**ORIGIN, "X-CSRF-Token": logged.json()["csrf_token"]},
    )
    headers = {**ORIGIN, "X-CSRF-Token": changed.json()["csrf_token"]}
    assert identity_client.post("/api/v1/users", json=INPUT, headers=ORIGIN).status_code == 403
    assert (
        identity_client.post(
            "/api/v1/users", json=INPUT, headers={**headers, "Origin": "https://foreign.example"}
        ).status_code
        == 403
    )
    for override in (
        {"role": "admin"},
        {"company_id": changed.json()["account"]["company_id"]},
        {"extra": True},
    ):
        assert (
            identity_client.post(
                "/api/v1/users", json={**INPUT, **override}, headers=headers
            ).status_code
            == 400
        )
    assert (
        identity_client.post(
            "/api/v1/users", json={**INPUT, "initial_password": "short"}, headers=headers
        ).status_code
        == 422
    )
    assert identity_client.post("/api/v1/users", json=INPUT, headers=headers).status_code == 201


def test_display_name_maximum_is_measured_after_trimming(identity_client: TestClient) -> None:
    """One hundred Unicode characters remain valid with surrounding whitespace, without silent truncation."""
    headers = admin_headers(identity_client)
    created = identity_client.post(
        "/api/v1/users", json={**INPUT, "display_name": "  " + "é" * 100 + "  "}, headers=headers
    )
    assert created.status_code == 201 and created.json()["display_name"] == "é" * 100
