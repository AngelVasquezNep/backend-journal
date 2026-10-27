"""Revocable login sessions carry no authority beyond their current owned Account."""

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from uuid import UUID

from taskify_identity.domain.account import Account
from taskify_identity.domain.values import identifier


@dataclass(frozen=True, kw_only=True)
class LoginSession:
    """Store a unique token digest, current credential version and 30-minute idle boundary.

    Unique digest of a random 256-bit token; 30-minute idle expiry; account role/company
    resolved from Account; no access except auth/password/logout while initial password
    change is pending.
    """

    id: UUID
    account_id: UUID
    token_digest: str = field(repr=False)
    credential_version: int
    csrf_secret: str = field(repr=False)
    created_at: datetime
    last_activity_at: datetime
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        """Reject malformed token metadata and non-UTC times without revealing secret values."""
        identifier(self.id)
        identifier(self.account_id)
        if not re.fullmatch(r"[0-9a-f]{64}", self.token_digest) or len(self.csrf_secret) < 32:
            raise ValueError("Invalid session credential metadata.")
        if type(self.credential_version) is not int or self.credential_version < 1:
            raise ValueError("Invalid session credential version.")
        for value in (self.created_at, self.last_activity_at, self.revoked_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0)):
                raise ValueError("Session timestamps must be UTC.")

    def valid_for(self, account: Account, now: datetime) -> bool:
        """Reject now - last_activity_at >= 30 minutes, revocation and obsolete credential versions."""
        return (
            self.account_id == account.id
            and self.revoked_at is None
            and self.credential_version == account.credential_version
            and timedelta(0) <= now - self.last_activity_at < timedelta(minutes=30)
        )

    def touch(self, now: datetime) -> "LoginSession":
        """Return explicit user activity; polling/background callers must not invoke this method."""
        return replace(self, last_activity_at=now)
