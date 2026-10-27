"""Citation identities and original locators are saved only after a fresh authorized source snapshot."""

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from taskify_chat.domain.conversation import ownership, utc


@dataclass(frozen=True, kw_only=True)
class Citation:
    """Own-account evidence reference; never persist a model-supplied URL or replacement locator."""

    id: UUID
    company_id: UUID
    account_id: UUID
    assistant_message_id: UUID
    item_id: UUID
    revision_id: UUID
    chunk_id: UUID
    locator: Mapping[str, object]
    title_at_answer: str
    validated_at: datetime

    def __post_init__(self) -> None:
        """Require trusted identifiers, bounded labels and the original typed locator representation."""
        ownership(
            self.id,
            self.company_id,
            self.account_id,
            self.assistant_message_id,
            self.item_id,
            self.revision_id,
            self.chunk_id,
        )
        utc(self.validated_at)
        if (
            not self.title_at_answer
            or len(self.title_at_answer) > 200
            or self.locator.get("kind") not in ("text", "pdf", "docx", "image")
        ):
            raise ValueError("Invalid citation provenance.")
