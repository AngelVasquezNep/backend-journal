"""One immutable company/account-owned saved conversation per account, independent of login sessions."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID


def ownership(*ids: UUID) -> None:
    """Reject malformed authority identifiers before persistence or use in scoped queries."""
    if not all(isinstance(value, UUID) for value in ids):
        raise ValueError("Owned identifiers must be UUIDs.")


def utc(*values: datetime | None) -> None:
    """Require aware UTC values for persisted activity, lease and terminal timestamps."""
    if any(
        value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0))
        for value in values
    ):
        raise ValueError("Timestamps must be aware UTC.")


@dataclass(frozen=True, kw_only=True)
class Conversation:
    """Unique (company_id, account_id) and unique account ID; ownership cannot change."""

    id: UUID
    company_id: UUID
    account_id: UUID
    last_sequence: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Validate immutable ownership, nonnegative sequence and aware times."""
        ownership(self.id, self.company_id, self.account_id)
        if type(self.last_sequence) is not int or self.last_sequence < 0:
            raise ValueError("Invalid conversation sequence.")
        utc(self.created_at, self.updated_at)
