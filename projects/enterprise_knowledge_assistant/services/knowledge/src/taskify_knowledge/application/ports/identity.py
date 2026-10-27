"""Owned Identity contract DTOs; authentication authority never comes from request claims."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True)
class Principal:
    """Trusted online Identity result; login sessions are not saved conversations."""

    login_session_id: UUID
    account_id: UUID
    company_id: UUID
    role: Literal["admin", "user"]
    must_change_password: bool
    idle_expires_at: datetime
    csrf_valid: bool | None = None

    def __post_init__(self) -> None:
        """Fail closed on malformed identities, roles, timestamps or authentication flags."""
        if not all(
            isinstance(v, UUID) for v in (self.login_session_id, self.account_id, self.company_id)
        ):
            raise ValueError("Identity returned invalid identifiers.")
        if self.role not in ("admin", "user") or type(self.must_change_password) is not bool:
            raise ValueError("Identity returned invalid permissions.")
        if self.idle_expires_at.tzinfo is None or self.idle_expires_at.utcoffset() != timedelta(0):
            raise ValueError("Identity expiry must be UTC.")
        if self.csrf_valid is not None and type(self.csrf_valid) is not bool:
            raise ValueError("Identity returned an invalid CSRF result.")


@dataclass(frozen=True)
class SessionRequest:
    """Exactly one selector and handler-selected activity; secret values never appear in repr."""

    session_token: str | None = field(default=None, repr=False)
    login_session_id: UUID | None = None
    csrf_token: str | None = field(default=None, repr=False)
    require_csrf: bool = False
    require_password_changed: bool = True
    activity: Literal["user_activity", "poll", "background"] = "background"

    def __post_init__(self) -> None:
        """Validate selector exclusivity, token bounds and fixed receiving-handler policy."""
        if (self.session_token is None) == (self.login_session_id is None):
            raise ValueError("Exactly one session selector is required.")
        if self.session_token is not None and not re.fullmatch(
            r"[A-Za-z0-9_-]{43}", self.session_token
        ):
            raise ValueError("Invalid session selector.")
        if self.login_session_id is not None and not isinstance(self.login_session_id, UUID):
            raise ValueError("Invalid session selector.")
        if type(self.require_csrf) is not bool or type(self.require_password_changed) is not bool:
            raise ValueError("Session policies must be boolean.")
        if self.activity not in ("user_activity", "poll", "background"):
            raise ValueError("Invalid session activity.")
        if self.csrf_token is not None and (
            not isinstance(self.csrf_token, str) or not 1 <= len(self.csrf_token) <= 256
        ):
            raise ValueError("Invalid CSRF token.")
        if self.require_csrf and not self.csrf_token:
            raise ValueError("A CSRF token is required.")


class SessionValidator(Protocol):
    """Resolve each session online; do not cache valid identities or silently refresh workers."""

    def resolve(self, request: SessionRequest, request_id: UUID) -> Principal:
        """Return a trusted principal or raise an explicit authentication/dependency failure."""
        ...
