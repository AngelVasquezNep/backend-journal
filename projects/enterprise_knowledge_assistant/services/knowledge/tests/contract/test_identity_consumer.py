"""Provider-consumer session contracts: no cache, no worker activity, strict safe failures."""

from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from taskify_knowledge.adapters.outbound.http.identity import IdentityHTTP
from taskify_knowledge.application.ports.identity import SessionRequest
from taskify_knowledge.domain.errors import ApplicationError, DependencyUnavailable


def payload() -> dict[str, object]:
    """Create a contract-valid trusted response without any browser/CSRF secret."""
    return {
        "login_session_id": str(uuid4()),
        "account_id": str(uuid4()),
        "company_id": str(uuid4()),
        "role": "user",
        "must_change_password": False,
        "idle_expires_at": datetime.now(UTC).isoformat(),
        "csrf_valid": None,
    }


def test_online_resolution_and_poll_policy() -> None:
    """Make a fresh scoped request for every poll; no valid result is cached or touched as activity."""
    seen: list[httpx.Request] = []
    data = payload()

    def respond(request: httpx.Request) -> httpx.Response:
        """Record only in-memory test input and return the contract fixture."""
        seen.append(request)
        return httpx.Response(200, json=data)

    adapter = IdentityHTTP(
        "https://identity.example",
        "caller-credential",
        client=httpx.Client(transport=httpx.MockTransport(respond)),
    )
    request = SessionRequest(session_token="A" * 43, activity="poll")
    for _ in range(2):
        assert adapter.resolve(request, uuid4()).role == "user"
    assert len(seen) == 2
    assert seen[0].headers["authorization"] == "Bearer caller-credential"
    assert b'"activity":"poll"' in seen[0].content


def test_selector_exclusivity_and_worker_no_refresh() -> None:
    """Reject missing/double selectors and prevent a worker from pretending to be browser activity."""
    with pytest.raises(ValueError):
        SessionRequest()
    with pytest.raises(ValueError):
        SessionRequest(session_token="A" * 43, login_session_id=uuid4())
    adapter = IdentityHTTP("https://identity.example", "worker-credential", worker=True)
    with pytest.raises(ApplicationError) as error:
        adapter.resolve(SessionRequest(session_token="A" * 43, activity="user_activity"), uuid4())
    assert error.value.status == 403
    adapter.close()


@pytest.mark.parametrize(
    "status,data",
    [
        (503, {"message": "private-document-secret"}),
        (200, {"role": "owner"}),
        (200, {"csrf_valid": "true"}),
    ],
)
def test_malformed_or_unavailable_identity_fails_closed(
    status: int, data: dict[str, object]
) -> None:
    """Do not turn an outage or malformed principal into usable identity or diagnostic leakage."""
    adapter = IdentityHTTP(
        "https://identity.example",
        "caller-credential",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(status, json=data))
        ),
    )
    with pytest.raises(DependencyUnavailable) as error:
        adapter.resolve(SessionRequest(session_token="A" * 43), uuid4())
    assert "private-document-secret" not in str(error.value)


def test_authenticated_csrf_cannot_be_skipped_by_provider() -> None:
    """Require an explicit true CSRF result and a changed password before returning authority."""
    data = payload()
    adapter = IdentityHTTP(
        "https://identity.example",
        "caller-credential",
        client=httpx.Client(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
        ),
    )
    with pytest.raises(ApplicationError) as error:
        adapter.resolve(
            SessionRequest(session_token="A" * 43, require_csrf=True, csrf_token="test-csrf"),
            uuid4(),
        )
    assert error.value.code == "csrf_failed"
