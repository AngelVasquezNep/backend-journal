"""Internal identity scopes do not let worker credentials refresh logins or accept two selectors."""

from fastapi.testclient import TestClient


def test_internal_requires_service_credentials_and_exact_selector(
    identity_client: TestClient,
) -> None:
    """Reject unauthenticated and malformed internal calls before resolving any account."""
    assert (
        identity_client.post(
            "/internal/v1/sessions/resolve",
            json={
                "session_token": "A" * 43,
                "activity": "background",
                "require_csrf": False,
                "require_password_changed": True,
            },
        ).status_code
        == 401
    )


def test_worker_cannot_claim_browser_activity(identity_client: TestClient) -> None:
    """Deny a valid worker credential when it requests user-activity refresh."""
    result = identity_client.post(
        "/internal/v1/sessions/resolve",
        json={
            "session_token": "A" * 43,
            "activity": "user_activity",
            "require_csrf": False,
            "require_password_changed": True,
        },
        headers={"Authorization": "Bearer " + "chat-worker-" + "x" * 32},
    )
    assert result.status_code == 403
