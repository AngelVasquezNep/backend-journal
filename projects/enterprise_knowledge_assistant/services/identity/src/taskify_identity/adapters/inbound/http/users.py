"""Strict company-user mutation authenticates first-party admin sessions without ownership input."""

from typing import Annotated

from fastapi import APIRouter, Header, Request
from pydantic import BeforeValidator, Field

from taskify_identity.adapters.inbound.http.auth import cookie_token
from taskify_identity.adapters.inbound.http.common import StrictDTO, json_guard, origin_guard
from taskify_identity.adapters.outbound.settings import Settings
from taskify_identity.application.authenticate import IdentityService
from taskify_identity.application.create_user import create_user
from taskify_identity.domain.values import Name


def canonical_name(value: object) -> object:
    """Apply the documented post-trim name bound before DTO length checks, retaining control rejection."""
    return Name(value).value if isinstance(value, str) else value


class CreateUserInput(StrictDTO):
    """Accept exactly a name, email and secret initial password; reject company/role/unknown fields."""

    display_name: Annotated[
        str, BeforeValidator(canonical_name), Field(min_length=1, max_length=100)
    ]
    email: Annotated[str, Field(min_length=1, max_length=254)]
    initial_password: Annotated[str, Field(min_length=12, max_length=128, repr=False)]


def users_router(service: IdentityService, settings: Settings) -> APIRouter:
    """Bind the only public provisioning operation to server-derived user/company authority."""
    router = APIRouter(prefix="/api/v1")

    @router.post("/users", status_code=201)
    def create(
        body: CreateUserInput,
        request: Request,
        csrf: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
    ) -> dict[str, object]:
        """Create an initial-password user and explicitly serialize only the contracted Account fields."""
        origin_guard(request, settings.public_origin)
        json_guard(request)
        # Reject unauthenticated or restricted callers before performing expensive hashing.
        actor = service.resolve(
            token=cookie_token(request, settings),
            csrf=csrf or "",
            require_csrf=True,
            require_password_changed=True,
            activity="background",
        )
        if actor.account.role != "admin":
            from taskify_identity.domain.errors import ApplicationError

            raise ApplicationError("forbidden", "Only a company admin can create users.", 403)
        account = create_user(
            service,
            cookie_token(request, settings),
            csrf or "",
            body.display_name,
            body.email,
            body.initial_password,
        )
        return {
            "id": str(account.id),
            "company_id": str(account.company_id),
            "email": account.email,
            "display_name": account.display_name,
            "role": account.role,
            "must_change_password": account.must_change_password,
        }

    return router
