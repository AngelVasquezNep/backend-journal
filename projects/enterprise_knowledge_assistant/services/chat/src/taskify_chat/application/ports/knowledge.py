"""Chat-owned evidence and source contracts; Knowledge remains the only content authority."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping, Protocol
from uuid import UUID


@dataclass(frozen=True)
class Evidence:
    """One current authorized chunk; text and locator are untrusted provider input data."""

    chunk_id: UUID
    item_id: UUID
    revision_id: UUID
    title: str
    text: str
    locator: Mapping[str, object]
    similarity: float


@dataclass(frozen=True)
class SearchResult:
    """Active retrieval metadata from this attempt, including a successful empty search."""

    pipeline_version: str
    retrieval_config_version: str
    candidates: tuple[Evidence, ...]


@dataclass(frozen=True)
class CitationKey:
    """Exact item/revision/chunk membership; caller locators and URLs confer no authority."""

    item_id: UUID
    revision_id: UUID
    chunk_id: UUID


@dataclass(frozen=True)
class SourceStatus:
    """Server-resolved source availability; unavailable sources have no active link."""

    key: CitationKey
    availability: Literal["current", "unavailable"]
    label: str | None
    locator: Mapping[str, object] | None
    resource_url: str | None


@dataclass(frozen=True)
class SourceSnapshot:
    """One release/history snapshot; a release result is single-use within a live SQL fence."""

    validated_at: datetime
    all_current: bool
    sources: tuple[SourceStatus, ...]


class KnowledgeGateway(Protocol):
    """Resolve authority online through Knowledge; empty evidence differs from an outage."""

    def search(self, login_session_id: UUID, query: str, request_id: UUID) -> SearchResult:
        """Search the accepting session's current company; never request a pinned retrieval version."""
        ...

    def validate(
        self,
        login_session_id: UUID,
        citations: tuple[CitationKey, ...],
        purpose: Literal["release", "history"],
        request_id: UUID,
    ) -> SourceSnapshot:
        """Batch-check exact sources atomically; failures raise safe dependency/authentication errors."""
        ...
