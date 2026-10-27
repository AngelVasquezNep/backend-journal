"""Owned system clock and random identifiers are injected only at the Chat composition boundary."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class SystemClock:
    """Provide aware UTC without allowing model/client input to select persisted time."""

    def now(self) -> datetime:
        """Read current UTC time for exact inactivity and lease checks."""
        return datetime.now(UTC)


class RandomIds:
    """Generate opaque Chat-owned identifiers independent of browser authority."""

    def new(self) -> UUID:
        """Return a fresh random UUID; database uniqueness is still authoritative."""
        return uuid4()
