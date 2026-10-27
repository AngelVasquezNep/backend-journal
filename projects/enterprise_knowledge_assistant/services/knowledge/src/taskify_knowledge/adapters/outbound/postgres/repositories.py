"""Knowledge-owned persistence applies tenant context before all reads, ranking and publication."""

from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, and_, delete, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert

from taskify_knowledge.adapters.outbound.postgres.cursors import CursorCodec
from taskify_knowledge.adapters.outbound.postgres.models import (
    BlockRow,
    ChunkRow,
    ItemRow,
    JobRow,
    PipelineRow,
    RevisionRow,
)
from taskify_knowledge.adapters.outbound.postgres.unit_of_work import SqlUnitOfWork
from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.application.ports.knowledge_store import ItemPage, ItemView
from taskify_knowledge.domain.block import ExtractedBlock
from taskify_knowledge.domain.chunk import KnowledgeChunk
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.ingestion_job import IngestionJob
from taskify_knowledge.domain.item import KnowledgeItem
from taskify_knowledge.domain.pipeline import PipelineConfiguration
from taskify_knowledge.domain.revision import KnowledgeRevision
from taskify_knowledge.domain.values import Pagination


def item_value(row: ItemRow) -> KnowledgeItem:
    """Map and revalidate owned item state without returning ORM objects to core."""
    return KnowledgeItem(**{key: getattr(row, key) for key in KnowledgeItem.__dataclass_fields__})


def revision_value(row: RevisionRow) -> KnowledgeRevision:
    """Map a revision whose original identity is immutable at both domain/database boundaries."""
    return KnowledgeRevision(
        **{key: getattr(row, key) for key in KnowledgeRevision.__dataclass_fields__}
    )


def job_value(row: JobRow) -> IngestionJob:
    """Revalidate queue data, including ownership and recovered lease fencing/version fields."""
    return IngestionJob(**{key: getattr(row, key) for key in IngestionJob.__dataclass_fields__})


def block_data(value: ExtractedBlock) -> dict[str, Any]:
    """Serialize validated local provenance to owned JSON columns; omit absent locator fields."""
    result = asdict(value)
    result["locator"] = {key: part for key, part in result["locator"].items() if part is not None}
    return result


def chunk_data(value: KnowledgeChunk) -> dict[str, Any]:
    """Serialize one finite vector and exact source identity to the Knowledge-owned schema."""
    result = asdict(value)
    result["locator"] = {key: part for key, part in result["locator"].items() if part is not None}
    result["embedding"] = list(value.embedding)
    return result


class SqlKnowledgeTransaction(SqlUnitOfWork):
    """Expose owned repositories inside the same transaction as trusted company context."""

    def __init__(self, engine: Engine, company_id: UUID, cursors: CursorCodec) -> None:
        """Store trusted scope and cursor authentication; no connection opens until entry."""
        super().__init__(engine, company_id)
        self.cursors = cursors

    def item(self, item_id: UUID, *, lock: bool = False) -> KnowledgeItem | None:
        """Return only a same-company item; publication/mutation requests acquire its row lock."""
        assert self.session is not None
        query = select(ItemRow).where(ItemRow.id == item_id, ItemRow.company_id == self.company_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalars(query).first()
        return item_value(row) if row else None

    def revision(self, revision_id: UUID) -> KnowledgeRevision | None:
        """Require company membership before returning exact original/revision metadata."""
        assert self.session is not None
        row = self.session.scalars(
            select(RevisionRow).where(
                RevisionRow.id == revision_id, RevisionRow.company_id == self.company_id
            )
        ).first()
        return revision_value(row) if row else None

    def view(self, item: KnowledgeItem) -> ItemView:
        """Hydrate only an item's exact owned current/candidate pointers."""
        return ItemView(
            item,
            self.revision(item.active_revision_id) if item.active_revision_id else None,
            self.revision(item.candidate_revision_id) if item.candidate_revision_id else None,
        )

    def cancel_jobs(self, revision_id: UUID) -> None:
        """Fence outstanding work before changing a candidate revision to cancelled."""
        assert self.session is not None
        self.session.execute(
            update(JobRow)
            .where(
                JobRow.revision_id == revision_id,
                JobRow.company_id == self.company_id,
                JobRow.state.in_(["queued", "running"]),
            )
            .values(state="cancelled", lease_owner=None, lease_until=None)
        )

    def retire_revision(self, revision_id: UUID, storage_key: str) -> bool:
        """Recheck obsolete visibility and queue state under the item lock before purging derived data."""
        assert self.session is not None
        revision = self.revision(revision_id)
        if revision is None or revision.storage_key != storage_key:
            return False
        item = self.item(revision.item_id, lock=True)
        if (
            item is None
            or item.active_revision_id == revision.id
            or (
                item.removed_at is None
                and revision.state not in ("superseded", "failed", "cancelled")
            )
        ):
            return False
        live = self.session.scalar(
            select(JobRow.id)
            .where(
                JobRow.company_id == self.company_id,
                JobRow.revision_id == revision.id,
                JobRow.state.in_(["queued", "running"]),
            )
            .limit(1)
        )
        if live is not None:
            return False
        self.session.execute(
            delete(ChunkRow).where(
                ChunkRow.company_id == self.company_id, ChunkRow.revision_id == revision.id
            )
        )
        self.session.execute(
            delete(BlockRow).where(
                BlockRow.company_id == self.company_id, BlockRow.revision_id == revision.id
            )
        )
        self.session.execute(
            text(
                "INSERT INTO retired_originals(revision_id,company_id,storage_key,purged_at) VALUES(:id,:company,:key,CURRENT_TIMESTAMP) ON CONFLICT(revision_id) DO NOTHING"
            ),
            {"id": revision.id, "company": self.company_id, "key": storage_key},
        )
        return True

    def page(self, actor: Principal, pagination: Pagination) -> ItemPage:
        """Apply company/current-ready filters before stable pagination and cursor signing."""
        assert self.session is not None
        query = select(ItemRow).where(
            ItemRow.company_id == self.company_id, ItemRow.removed_at.is_(None)
        )
        if actor.role != "admin":
            query = query.join(RevisionRow, ItemRow.active_revision_id == RevisionRow.id).where(
                RevisionRow.state == "ready", RevisionRow.company_id == actor.company_id
            )
        if pagination.cursor:
            created, last_id = self.cursors.decode(pagination.cursor, actor)
            query = query.where(
                or_(
                    ItemRow.created_at > created,
                    and_(ItemRow.created_at == created, ItemRow.id > last_id),
                )
            )
        rows = self.session.scalars(
            query.order_by(ItemRow.created_at, ItemRow.id).limit(pagination.limit + 1)
        ).all()
        selected = rows[: pagination.limit]
        cursor = (
            self.cursors.encode(actor, selected[-1].created_at, selected[-1].id)
            if len(rows) > pagination.limit and selected
            else None
        )
        return ItemPage(tuple(self.view(item_value(row)) for row in selected), cursor)

    def save_item(self, item: KnowledgeItem) -> None:
        """Stage canonical pointers/title/version; deferred constraints enforce revision membership."""
        assert self.session is not None
        self.session.merge(ItemRow(**asdict(item)))

    def save_revision(self, revision: KnowledgeRevision) -> None:
        """Stage state/error/readiness updates while database triggers reject original mutation."""
        assert self.session is not None
        self.session.merge(RevisionRow(**asdict(revision)))

    def save_job(self, job: IngestionJob) -> None:
        """Stage durable job transitions atomically with accepted revisions or publication."""
        assert self.session is not None
        self.session.merge(JobRow(**asdict(job)))

    def live_job(self, job: IngestionJob, now: datetime) -> bool:
        """Lock and verify latest unexpired owner/version so an obsolete worker cannot commit."""
        assert self.session is not None
        query = (
            select(JobRow.id)
            .where(
                JobRow.id == job.id,
                JobRow.company_id == self.company_id,
                JobRow.state == "running",
                JobRow.lease_version == job.lease_version,
                JobRow.lease_owner == job.lease_owner,
                JobRow.lease_until > now,
            )
            .with_for_update()
        )
        return self.session.scalar(query) is not None

    def stage_chunks(
        self,
        revision_id: UUID,
        blocks: tuple[ExtractedBlock, ...],
        chunks: tuple[KnowledgeChunk, ...],
    ) -> None:
        """Stage a complete unpublished revision idempotently; no ready revision is modified."""
        assert self.session is not None
        revision = self.revision(revision_id)
        if revision is None or revision.state != "processing" or not chunks:
            raise ApplicationError(
                "validation_failed", "Only complete processing revisions may publish.", 422
            )
        self.session.execute(
            delete(ChunkRow).where(
                ChunkRow.revision_id == revision_id, ChunkRow.company_id == self.company_id
            )
        )
        self.session.execute(
            delete(BlockRow).where(
                BlockRow.revision_id == revision_id, BlockRow.company_id == self.company_id
            )
        )
        self.session.execute(insert(BlockRow), [block_data(block) for block in blocks])
        self.session.execute(insert(ChunkRow), [chunk_data(chunk) for chunk in chunks])


class SqlKnowledgeStore:
    """Own the pool, immutable pipeline registration and narrow cross-company job claim functions."""

    def __init__(self, engine: Engine, cursors: CursorCodec) -> None:
        """Retain owned adapter dependencies; construction performs no data query."""
        self.engine = engine
        self.cursors = cursors

    def transaction(self, company_id: UUID) -> SqlKnowledgeTransaction:
        """Open a short company transaction from a trusted session or stored queue record."""
        return SqlKnowledgeTransaction(self.engine, company_id, self.cursors)

    def references_original(self, storage_key: str) -> bool:
        """Preserve every revision reference, including another tenant's failed/superseded original."""
        with self.engine.begin() as connection:
            return bool(
                connection.scalar(
                    text("SELECT taskify_original_referenced(:key)"), {"key": storage_key}
                )
            )

    def retirable_originals(self, before: datetime) -> tuple[tuple[UUID, UUID, str], ...]:
        """Enumerate a bounded obsolete cleanup batch through a narrowly granted owner-only function."""
        with self.engine.begin() as connection:
            rows = connection.execute(
                text("SELECT * FROM taskify_retirable_originals(:before)"), {"before": before}
            ).all()
            return tuple((row[0], row[1], row[2]) for row in rows)

    def register_pipeline(self, pipeline: PipelineConfiguration) -> None:
        """Register an immutable version; reject changes to an existing processing/vector space."""
        payload = asdict(pipeline)
        with self.engine.begin() as connection:
            connection.execute(
                insert(PipelineRow)
                .values(**payload)
                .on_conflict_do_nothing(index_elements=["version"])
            )
            row = (
                connection.execute(
                    select(PipelineRow.__table__).where(PipelineRow.version == pipeline.version)
                )
                .mappings()
                .one()
            )
            if any(row[key] != value for key, value in payload.items() if key != "created_at"):
                raise ApplicationError(
                    "dependency_unavailable",
                    "The processing pipeline configuration is incompatible.",
                    503,
                )

    def claim(self, worker_id: UUID, now: datetime) -> IngestionJob | None:
        """Claim queued/expired work in one short transaction and return only stored job authority."""
        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM taskify_claim_ingestion(:worker, :now)"),
                    {"worker": worker_id, "now": now},
                )
                .mappings()
                .first()
            )
            return IngestionJob(**row) if row else None

    def heartbeat(self, job: IngestionJob, now: datetime) -> bool:
        """Extend only a current valid lease through its narrowly granted queue function."""
        with self.engine.begin() as connection:
            return bool(
                connection.scalar(
                    text("SELECT taskify_heartbeat_ingestion(:id,:owner,:version,:now)"),
                    {
                        "id": job.id,
                        "owner": job.lease_owner,
                        "version": job.lease_version,
                        "now": now,
                    },
                )
            )
