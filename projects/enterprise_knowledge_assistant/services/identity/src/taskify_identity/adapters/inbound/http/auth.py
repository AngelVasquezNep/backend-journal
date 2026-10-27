"""Public first-party auth routes validate browser Origin, CSRF and strict input before mutation."""

from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, Response
from pydantic import Field

from taskify_identity.adapters.inbound.http.common import (
    StrictDTO,
    json_guard,
    origin_guard,
    safe_error,
)
from taskify_identity.adapters.outbound.settings import Settings
from taskify_identity.application.authenticate import IdentityService, LoginPaused, SessionResult
from taskify_identity.application.change_password import change_password
from taskify_identity.application.logout import logout
from taskify_identity.domain.errors import AuthenticationRequired


class LoginInput(StrictDTO):
    """Require bounded first-party credentials; unknown company/role/model fields are rejected."""

    email: Annotated[str, Field(min_length=1, max_length=254)]
    password: Annotated[str, Field(min_length=12, max_length=128, repr=False)]


class PasswordInput(StrictDTO):
    """Accept only current/new bounded passwords; no role/company or account selector exists."""

    current_password: Annotated[str, Field(min_length=12, max_length=128, repr=False)]
    new_password: Annotated[str, Field(min_length=12, max_length=128, repr=False)]


def session_body(result: SessionResult) -> dict[str, object]:
    """Select exact public fields explicitly; account hashes and session secrets are never serialized."""
    account = result.account
    return {
        "account": {
            "id": str(account.id),
            "company_id": str(account.company_id),
            "email": account.email,
            "display_name": account.display_name,
            "role": account.role,
            "must_change_password": account.must_change_password,
        },
        "csrf_token": result.csrf_token,
        "idle_expires_at": result.idle_expires_at.isoformat(),
    }


def cookie_token(request: Request, settings: Settings) -> str:
    """Read only the configured first-party cookie; identity headers and bearer tokens are ignored."""
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise AuthenticationRequired()
    return token


def issued_response(result: SessionResult, settings: Settings) -> JSONResponse:
    """Rotate a session cookie with production __Host flags and no Domain attribute."""
    response = JSONResponse(session_body(result))
    if result.token:
        response.set_cookie(
            settings.cookie_name,
            result.token,
            secure=settings.production,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


def auth_router(service: IdentityService, settings: Settings) -> APIRouter:
    """Bind the owned use cases; no admin provisioning, signup or foreign-account route is added."""
    router = APIRouter(prefix="/api/v1/auth")

    @router.post("/login")
    def login(body: LoginInput, request: Request) -> Response:
        """Validate exact Origin/JSON and return a generic credential failure or fresh login."""
        origin_guard(request, settings.public_origin)
        json_guard(request)
        try:
            return issued_response(service.login(body.email, body.password), settings)
        except LoginPaused as error:
            response = safe_error(request, error.code, error.message, error.status)
            response.headers["Retry-After"] = str(error.retry_after)
            return response

    @router.get("/session")
    def current(request: Request) -> dict[str, object]:
        """Recover own session/CSRF after explicit browser activity, including restricted first login."""
        return session_body(
            service.resolve(token=cookie_token(request, settings), activity="user_activity")
        )

    @router.put("/password")
    def password(
        body: PasswordInput,
        request: Request,
        csrf: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    ) -> Response:
        """Change the initial password and rotate the one replacement login atomically."""
        origin_guard(request, settings.public_origin)
        json_guard(request)
        return issued_response(
            change_password(
                service,
                cookie_token(request, settings),
                csrf or "",
                body.current_password,
                body.new_password,
            ),
            settings,
        )

    @router.post("/logout", status_code=204)
    def end(
        request: Request, csrf: Annotated[str | None, Header(alias="X-CSRF-Token")] = None
    ) -> Response:
        """Revoke the own login and expire its cookie while retaining saved conversation history."""
        origin_guard(request, settings.public_origin)
        logout(service, cookie_token(request, settings), csrf or "")
        response = Response(status_code=204)
        response.delete_cookie(
            settings.cookie_name,
            path="/",
            secure=settings.production,
            httponly=True,
            samesite="lax",
        )
        return response

    return router
