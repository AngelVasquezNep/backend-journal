"""Internal session resolution authenticates caller scopes before resolving browser/account authority."""

import hmac
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field, model_validator

from taskify_identity.adapters.inbound.http.common import StrictDTO
from taskify_identity.adapters.outbound.settings import Settings
from taskify_identity.application.authenticate import IdentityService
from taskify_identity.domain.errors import ApplicationError, AuthenticationRequired


class ResolutionInput(StrictDTO):
    """Exactly one selector and explicit CSRF/activity policies, accessible only to scoped services."""

    session_token: Annotated[str | None, Field(min_length=43, max_length=43, repr=False)] = None
    login_session_id: Annotated[UUID | None, Field(strict=False)] = None
    csrf_token: Annotated[str | None, Field(min_length=1, max_length=256, repr=False)] = None
    require_csrf: bool
    require_password_changed: bool
    activity: Literal["user_activity", "poll", "background"]

    @model_validator(mode="after")
    def selectors(self) -> "ResolutionInput":
        """Reject missing/double selectors and omitted required CSRF before domain resolution."""
        if (self.session_token is None) == (self.login_session_id is None) or (
            self.require_csrf and self.csrf_token is None
        ):
            raise ValueError("Exactly one selector and required CSRF must be supplied.")
        return self


def internal_router(service: IdentityService, settings: Settings) -> APIRouter:
    """Bind caller-specific service credentials with background-only worker capability."""
    router = APIRouter(prefix="/internal/v1/sessions")

    @router.post("/resolve", include_in_schema=False)
    def resolve(body: ResolutionInput, request: Request) -> dict[str, object]:
        """Resolve current identity online; never return raw browser, hash or stored CSRF secrets."""
        authorization = request.headers.get("authorization", "")
        if (
            not authorization.startswith("Bearer ")
            or not authorization.isascii()
            or len(authorization) > 512
        ):
            raise AuthenticationRequired()
        supplied = authorization[7:]
        caller = next(
            (
                name
                for name, token in settings.internal_credentials
                if hmac.compare_digest(supplied, token)
            ),
            None,
        )
        if caller is None:
            raise AuthenticationRequired()
        if caller.endswith("WORKER_CREDENTIAL") and (
            body.activity != "background" or body.login_session_id is None
        ):
            raise ApplicationError(
                "forbidden", "This service scope permits background session references only.", 403
            )
        if body.login_session_id is not None and body.activity != "background":
            raise ApplicationError(
                "forbidden", "Session references cannot refresh user activity.", 403
            )
        if not body.require_password_changed:
            raise ApplicationError(
                "password_change_required",
                "Protected service access requires a changed password.",
                403,
            )
        result = service.resolve(
            token=body.session_token,
            session_id=body.login_session_id,
            csrf=body.csrf_token,
            require_csrf=body.require_csrf,
            require_password_changed=True,
            activity=body.activity,
        )
        return {
            "login_session_id": str(result.session.id),
            "account_id": str(result.account.id),
            "company_id": str(result.account.company_id),
            "role": result.account.role,
            "must_change_password": result.account.must_change_password,
            "idle_expires_at": result.idle_expires_at.isoformat(),
            "csrf_valid": True if body.require_csrf else None,
        }

    return router
