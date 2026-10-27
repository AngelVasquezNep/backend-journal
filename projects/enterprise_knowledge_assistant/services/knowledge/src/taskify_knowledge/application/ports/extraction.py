"""Local extraction, chunking and embedding ports exchange plain owned domain values."""

from dataclasses import dataclass
from typing import Protocol

from taskify_knowledge.application.ports.storage import Original
from taskify_knowledge.domain.block import ExtractedBlock, ExtractedText
from taskify_knowledge.domain.locators import Locator


class TextExtractor(Protocol):
    """Extract original text/OCR with explicit resource limits and ordered source provenance."""

    def extract(self, original: Original) -> tuple[ExtractedText, ...]:
        """Return readable blocks or a typed permanent/transient processing failure."""
        ...


@dataclass(frozen=True)
class ChunkText:
    """Bounded pre-embedding text belongs to exactly one original page/section source block."""

    block: ExtractedBlock
    ordinal: int
    text: str
    token_count: int
    locator: Locator


class Chunker(Protocol):
    """Split within blocks under the immutable 800/100-token pipeline."""

    def split(self, blocks: tuple[ExtractedBlock, ...]) -> tuple[ChunkText, ...]:
        """Return nonempty <=800-token fragments without crossing source boundaries."""
        ...


class Embedder(Protocol):
    """Embed bounded texts in finite ordered vectors using exactly one configured vector space."""

    def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Return 1536-dimensional vectors in input order or an explicit safe provider failure."""
        ...
