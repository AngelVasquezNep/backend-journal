"""Strict HTTP boundaries, safe correlation/errors and nonpublic health; never log content."""

import logging
import time
from collections.abc import Callable
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint

from taskify_chat.adapters.inbound.http.health import install_metrics, metrics
from taskify_chat.domain.errors import ApplicationError

logger = logging.getLogger("taskify.http")


class StrictDTO(BaseModel):
    """Reject unknown fields and implicit primitive coercion at every JSON mutation boundary."""

    model_config = ConfigDict(extra="forbid", strict=True)


def request_id(request: Request) -> UUID:
    """Return the safe generated/request correlation UUID installed by the middleware."""
    value: UUID = request.state.request_id
    return value


def origin_guard(request: Request, public_origin: str) -> None:
    """Require exact configured browser Origin; subdomains and substring matches are forbidden."""
    if request.headers.get("origin") != public_origin:
        raise ApplicationError("forbidden", "This request origin is not allowed.", 403)


def json_guard(request: Request) -> None:
    """Reject form login and unexpected media types before accepting browser JSON mutations."""
    if request.headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
        raise ApplicationError("invalid_request", "Send this request as application/json.", 400)


def safe_error(
    request: Request,
    code: str,
    message: str,
    status: int,
    details: list[dict[str, str]] | None = None,
) -> JSONResponse:
    """Render only public corrective fields; provider/parser/input representations never escape."""
    return JSONResponse(
        {
            "code": code,
            "message": message,
            "request_id": str(request_id(request)),
            "details": details or [],
        },
        status_code=status,
        headers={"Cache-Control": "no-store"},
    )


def install_boundaries(app: FastAPI) -> None:
    """Install redacted error/latency handling; stack traces and request bodies stay private."""
    install_http_errors(app)

    @app.middleware("http")
    async def boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Attach bounded correlation and no-store headers without logging cookies, text or paths."""
        try:
            correlation = UUID(request.headers.get("x-request-id", ""))
        except (ValueError, AttributeError):
            correlation = uuid4()
        request.state.request_id = correlation
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            # Do not let default exception logging echo request or dependency diagnostics.
            response = safe_error(
                request,
                "dependency_unavailable",
                "A required service is temporarily unavailable.",
                503,
            )
        metrics.request(response.status_code, time.monotonic() - started)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-ID"] = str(correlation)
        response.headers["X-Content-Type-Options"] = "nosniff"
        # logger.info(
        #     "request_id=%s method=%s status=%s elapsed_ms=%d",
        #     correlation,
        #     request.method,
        #     response.status_code,
        #     int((time.monotonic() - started) * 1000),
        # )
        return response

    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, error: ApplicationError) -> JSONResponse:
        """Map only typed safe application failures; no underlying exception chain is exposed."""
        return safe_error(request, error.code, error.message, error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        """Return field locations without rejected values, parser messages or secret inputs."""
        unknown = any(item["type"] == "extra_forbidden" for item in error.errors())
        details = [
            {
                "field": ".".join(str(v) for v in item["loc"]),
                "message": "Check this field against the documented input limits.",
            }
            for item in error.errors()
        ]
        return safe_error(
            request,
            "invalid_request" if unknown else "validation_failed",
            "Check the submitted fields and their permitted limits.",
            400 if unknown and not request.url.path.startswith("/internal/") else 422,
            details,
        )


def install_health(app: FastAPI, ready: Callable[[], None]) -> None:
    """Add nonpublic process/storage checks; readiness must never invoke a paid provider API."""
    install_metrics(app)

    @app.get("/health/live", include_in_schema=False)
    def live() -> dict[str, str]:
        """Confirm the process is serving, without touching storage or external providers."""
        return {"status": "live"}

    @app.get("/health/ready", include_in_schema=False)
    def readiness() -> dict[str, str]:
        """Check local configuration and required owned storage; exceptions become safe 503s."""
        try:
            ready()
        except Exception:
            metrics.readiness(False)
            raise
        metrics.readiness(True)
        return {"status": "ready"}


def install_http_errors(app: FastAPI) -> None:
    """Map framework/parser HTTP errors to the same safe public shape without their raw detail."""

    @app.exception_handler(StarletteHTTPException)
    async def transport_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        """Preserve standard client statuses and redact diagnostics; dependency failures are retryable."""
        status = 503 if error.status_code >= 500 else error.status_code
        code = {
            401: "authentication_required",
            403: "forbidden",
            404: "not_found",
            413: "file_too_large",
            422: "validation_failed",
            503: "dependency_unavailable",
        }.get(status, "invalid_request")
        return safe_error(
            request, code, "The request could not be completed. Check its format and retry.", status
        )
