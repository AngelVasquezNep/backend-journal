"""Owned Knowledge persistence ports preserve atomic publication and lease fences."""

from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.domain.block import ExtractedBlock
from taskify_knowledge.domain.chunk import KnowledgeChunk
from taskify_knowledge.domain.ingestion_job import IngestionJob
from taskify_knowledge.domain.item import KnowledgeItem
from taskify_knowledge.domain.pipeline import PipelineConfiguration
from taskify_knowledge.domain.revision import KnowledgeRevision
from taskify_knowledge.domain.values import Pagination


@dataclass(frozen=True)
class ItemView:
    """Canonical item with exact current/candidate revisions; no storage key is a public DTO field."""

    item: KnowledgeItem
    current_revision: KnowledgeRevision | None
    candidate_revision: KnowledgeRevision | None

    @property
    def availability(self) -> str:
        """Keep the last ready revision usable while a replacement processes or fails."""
        if self.current_revision is not None and self.current_revision.state == "ready":
            return "ready"
        return (
            "failed"
            if self.candidate_revision is not None and self.candidate_revision.state == "failed"
            else "processing"
        )


@dataclass(frozen=True)
class ItemPage:
    """An owner/query-scoped immutable page of visible knowledge items."""

    items: tuple[ItemView, ...]
    next_cursor: str | None


class KnowledgeTransaction(Protocol):
    """One company-scoped transaction; no parser/provider work may hold its row locks."""

    def __enter__(self) -> Self:
        """Install trusted transaction-local company context and return this owned repository."""
        ...

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Rollback uncommitted changes and return a reset connection to its pool."""
        ...

    def commit(self) -> None:
        """Atomically persist validated state transitions and release the transaction."""
        ...

    def item(self, item_id: UUID, *, lock: bool = False) -> KnowledgeItem | None:
        """Return only an owned item, optionally locking it for publication/mutation."""
        ...

    def revision(self, revision_id: UUID) -> KnowledgeRevision | None:
        """Return an owned immutable original/revision record without following replacement pointers."""
        ...

    def view(self, item: KnowledgeItem) -> ItemView:
        """Resolve exact current/candidate revision pointers inside the same transaction."""
        ...

    def page(self, actor: Principal, pagination: Pagination) -> ItemPage:
        """Filter tenant/current availability before paging; decode only actor/query-scoped cursors."""
        ...

    def save_item(self, item: KnowledgeItem) -> None:
        """Stage an owned canonical item; composite revision ownership constraints apply."""
        ...

    def save_revision(self, revision: KnowledgeRevision) -> None:
        """Stage lifecycle metadata while preserving immutable original identity."""
        ...

    def save_job(self, job: IngestionJob) -> None:
        """Stage one logical ingestion job/revision/pipeline with explicit retry state."""
        ...

    def live_job(self, job: IngestionJob, now: datetime) -> bool:
        """Lock and require current owner/version/unexpired lease before any terminal write."""
        ...

    def cancel_jobs(self, revision_id: UUID) -> None:
        """Cancel queued/running owned candidate jobs under consistent item-before-job lock ordering."""
        ...

    def retire_revision(self, revision_id: UUID, storage_key: str) -> bool:
        """Lock and delete only obsolete derived data; retain immutable metadata and never restore availability."""
        ...

    def stage_chunks(
        self,
        revision_id: UUID,
        blocks: tuple[ExtractedBlock, ...],
        chunks: tuple[KnowledgeChunk, ...],
    ) -> None:
        """Idempotently stage all blocks/vectors before the candidate's atomic publication."""
        ...


class KnowledgeStore(Protocol):
    """Open company transactions and narrowly claim/heartbeat queue work, never cross service storage."""

    def transaction(self, company_id: UUID) -> KnowledgeTransaction:
        """Create a new owned transaction using a trusted principal or stored job owner."""
        ...

    def register_pipeline(self, pipeline: PipelineConfiguration) -> None:
        """Register immutable version metadata or reject a conflicting vector-space configuration."""
        ...

    def claim(self, worker_id: UUID, now: datetime) -> IngestionJob | None:
        """Atomically claim queued/expired work under a narrow unscoped function, then release locks."""
        ...

    def heartbeat(self, job: IngestionJob, now: datetime) -> bool:
        """Extend only a current live 120-second lease; stale owners must stop publishing."""
        ...

    def references_original(self, storage_key: str) -> bool:
        """Check one opaque owned key through a narrow cleanup function without listing tenant data."""
        ...

    def retirable_originals(self, before: datetime) -> tuple[tuple[UUID, UUID, str], ...]:
        """Return at most 100 stored obsolete company/revision/key triples for owned worker cleanup."""
        ...
