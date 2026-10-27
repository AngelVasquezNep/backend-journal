"""Identity HTTP consumer; every resolution is online, scoped and fail-closed."""

from dataclasses import asdict
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from taskify_chat.application.ports.identity import Principal, SessionRequest
from taskify_chat.domain.errors import (
    ApplicationError,
    AuthenticationRequired,
    DependencyUnavailable,
)


class PrincipalDTO(BaseModel):
    """Decode contract types while tolerating compatible additive response fields."""

    model_config = ConfigDict(strict=True, extra="ignore")
    login_session_id: UUID
    account_id: UUID
    company_id: UUID
    role: Literal["admin", "user"]
    must_change_password: bool
    idle_expires_at: datetime
    csrf_valid: bool | None


class IdentityHTTP:
    """Authenticate with a caller-specific credential; workers cannot refresh inactivity."""

    def __init__(
        self,
        url: str,
        credential: str,
        *,
        worker: bool = False,
        allow_insecure: bool = False,
        client: httpx.Client | None = None,
    ) -> None:
        """Configure bounded nonredirecting HTTP; allow plain HTTP only in explicit development."""
        parsed = urlparse(url)
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (parsed.scheme != "https" and not (allow_insecure and parsed.scheme == "http"))
        ):
            raise ValueError("Identity requires an authenticated TLS-capable service URL.")
        if not credential or any(c.isspace() for c in credential):
            raise ValueError("A scoped service credential is required.")
        self.url = url.rstrip("/")
        self.credential = credential
        self.worker = worker
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(3.0, connect=1.0), follow_redirects=False
        )

    def resolve(self, request: SessionRequest, request_id: UUID) -> Principal:
        """Resolve online without caching; distinguish invalid login, policy and dependency errors."""
        if self.worker and (request.activity != "background" or request.session_token is not None):
            raise ApplicationError(
                "forbidden", "Worker credentials permit background validation only.", 403
            )
        if not isinstance(request_id, UUID):
            raise ValueError("A valid correlation UUID is required.")
        payload = {
            k: (str(v) if isinstance(v, UUID) else v)
            for k, v in asdict(request).items()
            if v is not None
        }
        try:
            response = self.client.post(
                self.url + "/internal/v1/sessions/resolve",
                json=payload,
                headers={
                    "Authorization": "Bearer " + self.credential,
                    "X-Request-ID": str(request_id),
                },
            )
        except httpx.HTTPError:
            raise DependencyUnavailable() from None
        if response.status_code == 401:
            raise AuthenticationRequired()
        if response.status_code == 403:
            # Only known safe codes may leave the dependency boundary.
            try:
                code = response.json().get("code")
            except (ValueError, AttributeError):
                code = None
            safe_code = code if code in ("csrf_failed", "password_change_required") else "forbidden"
            raise ApplicationError(safe_code, "This operation is not permitted.", 403)
        if response.status_code != 200:
            raise DependencyUnavailable()
        try:
            data = PrincipalDTO.model_validate_json(response.content)
            if data.role not in ("admin", "user"):
                raise ValueError("Invalid role.")
            principal = Principal(
                data.login_session_id,
                data.account_id,
                data.company_id,
                data.role,
                data.must_change_password,
                data.idle_expires_at,
                data.csrf_valid,
            )
            if request.require_password_changed and principal.must_change_password:
                raise ApplicationError(
                    "password_change_required", "Change your initial password first.", 403
                )
            if request.require_csrf and principal.csrf_valid is not True:
                raise ApplicationError("csrf_failed", "Refresh the session and retry.", 403)
            return principal
        except (ValidationError, ValueError, TypeError):
            raise DependencyUnavailable() from None

    def close(self) -> None:
        """Release the owned HTTP connection pool; no session result is retained."""
        self.client.close()
