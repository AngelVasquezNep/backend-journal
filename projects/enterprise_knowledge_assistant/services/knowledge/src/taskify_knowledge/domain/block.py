"""Extracted text retains page/section/line/image provenance and normalization-to-source positions."""

from dataclasses import dataclass
from uuid import UUID

from taskify_knowledge.domain.constraints import ids
from taskify_knowledge.domain.locators import Locator
from taskify_knowledge.domain.values import sequence


@dataclass(frozen=True, kw_only=True)
class ExtractedText:
    """Keep non-empty UTF-8 text, monotonic ordering and source offsets without changing originals."""

    ordinal: int
    normalized_text: str
    locator: Locator
    source_offset_map: tuple[int, ...]
    extractor_version: str

    def __post_init__(self) -> None:
        """Validate readable text, source positions and extractor identity before chunking."""
        sequence(self.ordinal)
        if not self.normalized_text.strip() or "\x00" in self.normalized_text:
            raise ValueError("A block must contain readable text.")
        self.normalized_text.encode("utf-8")
        if len(self.source_offset_map) != len(self.normalized_text) + 1 or any(
            type(v) is not int or v < 0 for v in self.source_offset_map
        ):
            raise ValueError("A block requires a complete source-offset map.")
        if (
            any(a > b for a, b in zip(self.source_offset_map, self.source_offset_map[1:]))
            or not self.extractor_version
        ):
            raise ValueError("Invalid source ordering or extractor version.")


@dataclass(frozen=True, kw_only=True)
class ExtractedBlock(ExtractedText):
    """Add service-owned company/revision identity to validated local extraction output."""

    id: UUID
    company_id: UUID
    revision_id: UUID

    def __post_init__(self) -> None:
        """Validate extraction and owned identifiers without importing a parser or database type."""
        super().__post_init__()
        ids(self.id, self.company_id, self.revision_id)
