"""Knowledge items retain a current ready revision while an optional candidate processes."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from taskify_knowledge.domain.constraints import ids, utc
from taskify_knowledge.domain.values import Title, positive_version


@dataclass(frozen=True, kw_only=True)
class KnowledgeItem:
    """Preserve title/ownership and atomic current pointers; removed items are never readable/searchable.

    Title trimmed 1–200 characters; current pointer must reference this item's ready revision;
    removed items are never readable/searchable; version increments on mutations.
    """

    id: UUID
    company_id: UUID
    title: str
    created_by: UUID
    active_revision_id: UUID | None = None
    candidate_revision_id: UUID | None = None
    version: int = 1
    created_at: datetime
    updated_at: datetime
    removed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate immutable ownership, canonical title and positive version before persistence."""
        ids(self.id, self.company_id, self.created_by)
        ids(
            *(
                value
                for value in (self.active_revision_id, self.candidate_revision_id)
                if value is not None
            )
        )
        utc(self.created_at, self.updated_at, self.removed_at)
        positive_version(self.version)
        object.__setattr__(self, "title", Title(self.title).value)
        if self.removed_at is not None and (
            self.active_revision_id is not None or self.candidate_revision_id is not None
        ):
            raise ValueError("Removed items cannot retain current or processing pointers.")
