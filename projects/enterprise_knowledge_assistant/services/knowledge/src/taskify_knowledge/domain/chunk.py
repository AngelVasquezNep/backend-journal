"""Immutable bounded evidence chunks share one pipeline/model vector space and source block."""

import math
from dataclasses import dataclass
from uuid import UUID

from taskify_knowledge.domain.constraints import digest, ids
from taskify_knowledge.domain.locators import Locator
from taskify_knowledge.domain.values import sequence


@dataclass(frozen=True, kw_only=True)
class KnowledgeChunk:
    """Preserve non-empty <=800-token source text and exactly 1536 finite embedding dimensions.

    No page/section boundary crossing; 100-token overlap where possible; unique
    `(revision_id, pipeline_version, ordinal)`; model-space mismatches are explicit failures.
    """

    id: UUID
    company_id: UUID
    item_id: UUID
    revision_id: UUID
    block_id: UUID
    ordinal: int
    text: str
    token_count: int
    locator: Locator
    text_sha256: str
    pipeline_version: str
    embedding_model: str
    dimensions: int
    embedding: tuple[float, ...]

    def __post_init__(self) -> None:
        """Reject empty/oversized text, invalid positions and malformed/mismatched vector metadata."""
        ids(self.id, self.company_id, self.item_id, self.revision_id, self.block_id)
        sequence(self.ordinal)
        digest(self.text_sha256)
        if (
            not self.text.strip()
            or type(self.token_count) is not int
            or not 1 <= self.token_count <= 800
        ):
            raise ValueError("Chunks require 1–800 tokens of source text.")
        if (
            self.dimensions != 1536
            or len(self.embedding) != 1536
            or not all(math.isfinite(v) for v in self.embedding)
        ):
            raise ValueError("Chunks require 1536 finite embedding dimensions.")
        if not self.pipeline_version or self.embedding_model != "text-embedding-3-small":
            raise ValueError("Chunk and initial embedding pipeline must match.")
