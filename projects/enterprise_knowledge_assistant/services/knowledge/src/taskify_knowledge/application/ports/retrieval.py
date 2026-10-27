"""Knowledge-owned retrieval/source values expose evidence without sharing runtime models with Chat."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from taskify_knowledge.domain.locators import Locator


@dataclass(frozen=True)
class EvidenceKey:
    """One exact item/revision/chunk triple; supplied locators or URLs cannot grant authority."""

    item_id: UUID
    revision_id: UUID
    chunk_id: UUID


@dataclass(frozen=True)
class RetrievedChunk:
    """One authorized current-ready source chunk and its server-owned original provenance."""

    key: EvidenceKey
    title: str
    text: str
    locator: Locator
    similarity: float


@dataclass(frozen=True)
class SearchPage:
    """Successful active retrieval metadata is mandatory even for an empty evidence page."""

    pipeline_version: str
    retrieval_config_version: str
    candidates: tuple[RetrievedChunk, ...]


@dataclass(frozen=True)
class CurrentSource:
    """Unavailable triples carry no foreign/private label, locator or source address."""

    key: EvidenceKey
    title: str | None
    locator: Locator | None
    resource_url: str | None


@dataclass(frozen=True)
class SourceBatch:
    """One transactional source snapshot, single-use for final response release."""

    validated_at: datetime
    sources: tuple[CurrentSource, ...]


class VectorSearch(Protocol):
    """Only Knowledge applies trusted company/current revision filtering before ranking."""

    def search(
        self, company: UUID, vector: tuple[float, ...], pipeline: str
    ) -> tuple[RetrievedChunk, ...]:
        """Exact cosine search returns at most 20 active-space owned chunks."""
        ...

    def validate(self, company: UUID, keys: tuple[EvidenceKey, ...]) -> tuple[CurrentSource, ...]:
        """Check every triple in one snapshot and construct exact-revision server URLs."""
        ...
