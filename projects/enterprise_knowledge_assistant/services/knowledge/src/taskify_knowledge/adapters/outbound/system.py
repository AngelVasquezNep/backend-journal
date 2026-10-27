"""Knowledge clock/UUID adapters are owned locally and inject no shared service-domain package."""

from datetime import UTC, datetime
from uuid import UUID, uuid4


class SystemClock:
    """Provide aware UTC instants for leases, publication and source validation."""

    def now(self) -> datetime:
        """Return current UTC without changing any login/session activity."""
        return datetime.now(UTC)


class RandomIds:
    """Generate independent random identifiers for Knowledge-owned records."""

    def new(self) -> UUID:
        """Return a UUID; database uniqueness and composite ownership remain authoritative."""
        return uuid4()
