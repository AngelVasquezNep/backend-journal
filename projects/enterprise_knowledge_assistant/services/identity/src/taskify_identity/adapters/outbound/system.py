"""Concrete time and UUID adapters are composed outside the framework-free core."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class SystemClock:
    """Supply aware UTC instants without affecting any account's activity timestamp."""

    def now(self) -> datetime:
        """Return process UTC time; callers decide whether the operation counts as user activity."""
        return datetime.now(UTC)


class RandomIds:
    """Generate independent random identifiers for owned entities and sessions."""

    def new(self) -> UUID:
        """Return a UUID; database constraints remain the authority on uniqueness."""
        return uuid4()
