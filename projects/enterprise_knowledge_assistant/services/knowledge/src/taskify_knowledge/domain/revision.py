"""Immutable file identity and explicit processing/publication lifecycle for one knowledge revision."""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from taskify_knowledge.domain.constraints import digest, ids, utc
from taskify_knowledge.domain.values import FileMetadata


@dataclass(frozen=True, kw_only=True)
class KnowledgeRevision:
    """Keep original identity immutable and at most one processing candidate per item.

    Immutable file identity; size 1–20,971,520 bytes; matching supported content/extension;
    unique private storage key; no more than one candidate processing revision/item.
    """

    id: UUID
    company_id: UUID
    item_id: UUID
    uploaded_by: UUID
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    storage_key: str
    state: Literal["processing", "ready", "failed", "superseded", "cancelled"]
    pipeline_version: str
    error_code: str | None = None
    created_at: datetime
    ready_at: datetime | None = None

    def __post_init__(self) -> None:
        """Revalidate file metadata and server-owned key without opening or changing the original."""
        ids(self.id, self.company_id, self.item_id, self.uploaded_by)
        FileMetadata(self.original_filename, self.size_bytes, self.media_type)
        digest(self.sha256)
        if not re.fullmatch(r"[0-9a-f]{32}", self.storage_key):
            raise ValueError("Invalid private object identity.")
        if (
            self.state not in ("processing", "ready", "failed", "superseded", "cancelled")
            or not self.pipeline_version
        ):
            raise ValueError("Invalid revision lifecycle metadata.")
        utc(self.created_at, self.ready_at)


ERROR_MESSAGES = {
    "unreadable_file": "The file does not contain readable supported text.",
    "protected_file": "Upload an unprotected copy of this document.",
    "corrupt_file": "The file could not be read. Upload a valid copy.",
    "resource_limit": "The file exceeds a processing resource limit. Use a smaller or simpler file.",
    "invalid_encoding": "Text files must use UTF-8 encoding.",
    "processing_unavailable": "Processing is temporarily unavailable. Please try another upload.",
    "configuration_changed": "Processing configuration changed. Please try another upload.",
    "original_changed": "The original file could not be verified. Please upload it again.",
}
