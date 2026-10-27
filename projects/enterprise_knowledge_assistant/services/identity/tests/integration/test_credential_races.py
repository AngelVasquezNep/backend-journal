"""Real credential fences serialize racing initial-password changes and in-flight logins."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient
from sqlalchemy import Engine, text


def test_racing_password_changes_issue_one_surviving_session(
    identity_client: TestClient, migration_engine: Engine
) -> None:
    """Serialize two initial-password changes; the losing session fails its credential-version fence."""
    logins = [
        identity_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.test", "password": "Initial-password-123"},
            headers={"Origin": "http://localhost:8080"},
        )
        for _ in range(2)
    ]

    def change(index: int) -> int:
        """Use an independent initial-password session and its matching synchronizer value."""
        with TestClient(identity_client.app) as client:
            return client.put(
                "/api/v1/auth/password",
                json={
                    "current_password": "Initial-password-123",
                    "new_password": "Replacement-password-" + str(index),
                },
                headers={
                    "Origin": "http://localhost:8080",
                    "Cookie": "taskify_session="
                    + str(logins[index].cookies.get("taskify_session")),
                    "X-CSRF-Token": logins[index].json()["csrf_token"],
                },
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(change, (0, 1)))
    assert sorted(results) == [200, 401]
    with migration_engine.connect() as connection:
        assert connection.execute(text("SELECT credential_version FROM accounts")).scalar() == 2
        assert (
            connection.execute(
                text("SELECT count(*) FROM login_sessions WHERE revoked_at IS NULL")
            ).scalar()
            == 1
        )


def test_inflight_old_password_login_cannot_survive_change(
    identity_client: TestClient, identity_service, monkeypatch
) -> None:
    """Pause verification while it owns the account lock; a later password change must revoke it."""
    first = identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "Initial-password-123"},
        headers={"Origin": "http://localhost:8080"},
    )
    verified, release, changing = Event(), Event(), Event()
    original = identity_service.passwords.verify

    def gated(password: str, encoded: str | None) -> bool:
        """Pause one successful check without altering hash behavior or logging credentials."""
        result = original(password, encoded)
        if result and not verified.is_set():
            verified.set()
            assert release.wait(5)
        return result

    monkeypatch.setattr(identity_service.passwords, "verify", gated)

    def login():
        """Submit a real login in a separate request/transaction."""
        with TestClient(identity_client.app) as client:
            return client.post(
                "/api/v1/auth/login",
                json={"email": "admin@example.test", "password": "Initial-password-123"},
                headers={"Origin": "http://localhost:8080"},
            )

    def change():
        """Initiate a change with the earlier restricted session using an independent transport."""
        changing.set()
        with TestClient(identity_client.app) as client:
            return client.put(
                "/api/v1/auth/password",
                json={
                    "current_password": "Initial-password-123",
                    "new_password": "Replacement-password-123",
                },
                headers={
                    "Origin": "http://localhost:8080",
                    "Cookie": "taskify_session=" + str(first.cookies.get("taskify_session")),
                    "X-CSRF-Token": first.json()["csrf_token"],
                },
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        logged = executor.submit(login)
        assert verified.wait(5)
        changed = executor.submit(change)
        assert changing.wait(5)
        release.set()
        old = logged.result(timeout=10)
        assert old.status_code == 200
        assert changed.result(timeout=10).status_code == 200
    with TestClient(identity_client.app) as client:
        assert (
            client.get(
                "/api/v1/auth/session",
                headers={"Cookie": "taskify_session=" + str(old.cookies.get("taskify_session"))},
            ).status_code
            == 401
        )


def test_internal_background_activity_does_not_refresh_idle(
    identity_client: TestClient, identity_service, clock
) -> None:
    """A worker validates a stored session reference without extending its inactivity lifetime."""
    first = identity_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "Initial-password-123"},
        headers={"Origin": "http://localhost:8080"},
    )
    identity_client.put(
        "/api/v1/auth/password",
        json={
            "current_password": "Initial-password-123",
            "new_password": "Replacement-password-123",
        },
        headers={"Origin": "http://localhost:8080", "X-CSRF-Token": first.json()["csrf_token"]},
    )
    resolved = identity_service.resolve(token=identity_client.cookies.get("taskify_session"))
    clock.advance(1740)
    response = identity_client.post(
        "/internal/v1/sessions/resolve",
        json={
            "login_session_id": str(resolved.session.id),
            "require_csrf": False,
            "require_password_changed": True,
            "activity": "background",
        },
        headers={"Authorization": "Bearer chat-worker-" + "x" * 32},
    )
    assert response.status_code == 200
    assert response.json()["csrf_valid"] is None
    clock.advance(60)
    assert identity_client.get("/api/v1/auth/session").status_code == 401
