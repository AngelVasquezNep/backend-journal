"""US2 storage/security tests cover lockout, old-session invalidation and account fencing."""

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text


def test_five_failures_pause_known_and_unknown_accounts(identity_client: TestClient) -> None:
    """Persist failure accounting for every normalized email without revealing account existence."""
    for email in ("admin@example.test", "unknown@example.test"):
        for _ in range(4):
            response = identity_client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "Wrong-password-123"},
                headers={"Origin": "http://localhost:8080"},
            )
            assert response.status_code == 401
        paused = identity_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Wrong-password-123"},
            headers={"Origin": "http://localhost:8080"},
        )
        assert paused.status_code == 429
        assert int(paused.headers["Retry-After"]) == 900


def test_password_change_revokes_all_prior_sessions(identity_client: TestClient) -> None:
    """Invalidate both initial-password sessions and reject replay of the pre-change cookie."""
    body = {"email": "admin@example.test", "password": "Initial-password-123"}
    headers = {"Origin": "http://localhost:8080"}
    assert identity_client.post("/api/v1/auth/login", json=body, headers=headers).status_code == 200
    first = identity_client.cookies.get("taskify_session")
    second = identity_client.post("/api/v1/auth/login", json=body, headers=headers)
    csrf = second.json()["csrf_token"]
    response = identity_client.put(
        "/api/v1/auth/password",
        json={"current_password": "Initial-password-123", "new_password": "Changed-password-456"},
        headers={**headers, "X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    identity_client.cookies.set("taskify_session", first or "", domain="testserver.local", path="/")
    assert identity_client.get("/api/v1/auth/session").status_code == 401


def test_idle_expiry_is_exact(identity_client: TestClient, clock) -> None:
    """Reject now - last_activity_at >= 30 minutes, even before any cleanup worker runs."""
    assert (
        identity_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.test", "password": "Initial-password-123"},
            headers={"Origin": "http://localhost:8080"},
        ).status_code
        == 200
    )
    clock.advance(1800)
    assert identity_client.get("/api/v1/auth/session").status_code == 401


def test_duplicate_provisioning_rolls_back_new_company(
    identity_service, migration_engine: Engine
) -> None:
    """A globally duplicate normalized email must not leave an orphan company."""
    import pytest

    from taskify_identity.application.provision_admin import provision_admin
    from taskify_identity.domain.errors import ApplicationError

    with migration_engine.connect() as connection:
        before = connection.execute(text("SELECT count(*) FROM companies")).scalar()
    with pytest.raises(ApplicationError):
        provision_admin(
            identity_service.store,
            identity_service.passwords,
            identity_service.clock,
            identity_service.ids,
            company_name="Rolled back company",
            company_id=None,
            display_name="Duplicate",
            email="ADMIN@example.test",
            password="Initial-password-123",
        )
    with migration_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM companies")).scalar() == before
