"""Versioned immutable normalization, extraction, tokenization and embedding configuration."""

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from taskify_knowledge.domain.constraints import utc


@dataclass(frozen=True, kw_only=True)
class PipelineConfiguration:
    """Use NFC/newlines, recursive token splitting, 800/100 and text-embedding-3-small at 1536 dims."""

    version: str
    normalization_version: str
    extractor_versions: Mapping[str, str]
    splitter_name: str
    chunk_tokens: int
    overlap_tokens: int
    embedding_model: str
    dimensions: int
    tokenizer: str
    created_at: datetime

    def __post_init__(self) -> None:
        """Reject a silent pipeline/model-space change; upgrades require a new immutable version."""
        if not self.version or not self.normalization_version or not self.extractor_versions:
            raise ValueError("A pipeline requires immutable version metadata.")
        if (
            self.chunk_tokens,
            self.overlap_tokens,
            self.embedding_model,
            self.dimensions,
            self.tokenizer,
        ) != (800, 100, "text-embedding-3-small", 1536, "cl100k_base"):
            raise ValueError("The initial embedding pipeline configuration must remain consistent.")
        utc(self.created_at)
