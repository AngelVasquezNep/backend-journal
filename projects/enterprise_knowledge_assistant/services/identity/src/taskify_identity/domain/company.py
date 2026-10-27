"""Company identity is committed atomically with its first administrator."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from taskify_identity.domain.values import Name, identifier


@dataclass(frozen=True)
class Company:
    """Name trimmed, 1–100 characters; first admin and company commit in one transaction."""

    id: UUID
    name: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate owned identity, canonical name and aware UTC creation time."""
        identifier(self.id)
        object.__setattr__(self, "name", Name(self.name).value)
        if self.created_at.tzinfo is None or self.created_at.utcoffset() != timedelta(0):
            raise ValueError("Company timestamps must be UTC.")
