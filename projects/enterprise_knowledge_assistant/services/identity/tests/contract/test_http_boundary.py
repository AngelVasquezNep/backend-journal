"""Transport tests reject unknown/coerced fields, bad origins and sensitive diagnostics."""

from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from taskify_identity.adapters.inbound.http.common import (
    StrictDTO,
    install_boundaries,
    install_health,
    origin_guard,
)


class Input(StrictDTO):
    """Strict example mutation body; the common layer must reject extras and coercion."""

    count: int


def app() -> FastAPI:
    """Compose a local fixture without auth bypasses, provider calls or persistent storage."""
    service = FastAPI()
    install_boundaries(service)
    install_health(service, lambda: None)

    @service.post("/check")
    def mutation(body: Input, request: Request) -> dict[str, int]:
        """Require an exact origin and return only the validated integer fixture."""
        origin_guard(request, "https://taskify.example")
        return {"count": body.count}

    @service.get("/broken")
    def broken() -> None:
        """Simulate a dependency failure containing a private diagnostic that must be discarded."""
        raise RuntimeError("private-password-or-document")

    return service


def test_strict_fields_and_safe_correlation() -> None:
    """Accept typed fields, reject extras/coercion, and replace an unsafe request identifier."""
    client = TestClient(app())
    good = client.post(
        "/check",
        json={"count": 1},
        headers={"Origin": "https://taskify.example", "X-Request-ID": "unsafe-input"},
    )
    assert good.status_code == 200
    UUID(good.headers["X-Request-ID"])
    assert good.headers["Cache-Control"] == "no-store"
    assert client.post("/check", json={"count": "1"}).status_code == 422
    extra = client.post("/check", json={"count": 1, "company_id": "forged"})
    assert extra.status_code == 400
    assert "forged" not in extra.text
    assert (
        client.post(
            "/check", json={"count": 1}, headers={"Origin": "https://taskify.example.evil"}
        ).status_code
        == 403
    )


def test_dependency_diagnostics_are_not_disclosed() -> None:
    """Report a safe retryable error; no private exception content reaches responses or normal logs."""
    response = TestClient(app()).get("/broken")
    assert response.status_code == 503
    assert "private-password-or-document" not in response.text
    assert set(response.json()) == {"code", "message", "request_id", "details"}


def test_health_is_local_and_nonbillable() -> None:
    """Liveness and readiness require no generation or embedding provider call."""
    client = TestClient(app())
    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").json() == {"status": "ready"}
