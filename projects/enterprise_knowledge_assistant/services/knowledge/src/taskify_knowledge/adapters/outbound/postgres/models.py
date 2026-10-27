"""Knowledge-owned ORM records mirror its migration and never cross the service boundary."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Own only Knowledge tables, including vectors; no Identity/Chat mapping is imported."""


class ItemRow(Base):
    """Map tenant-owned title, version and current/candidate revision pointers."""

    __tablename__ = "knowledge_items"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    company_id: Mapped[UUID]
    title: Mapped[str] = mapped_column(String)
    created_by: Mapped[UUID]
    active_revision_id: Mapped[UUID | None]
    candidate_revision_id: Mapped[UUID | None]
    version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RevisionRow(Base):
    """Map immutable private original identity and mutable processing/publication outcome."""

    __tablename__ = "knowledge_revisions"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    company_id: Mapped[UUID]
    item_id: Mapped[UUID]
    uploaded_by: Mapped[UUID]
    original_filename: Mapped[str] = mapped_column(String)
    media_type: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String)
    storage_key: Mapped[str] = mapped_column(String, unique=True)
    state: Mapped[str] = mapped_column(String)
    pipeline_version: Mapped[str] = mapped_column(String)
    error_code: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BlockRow(Base):
    """Map normalized text plus offset/page/section provenance for a single immutable revision."""

    __tablename__ = "extracted_blocks"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    company_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    ordinal: Mapped[int] = mapped_column(Integer)
    normalized_text: Mapped[str] = mapped_column(String)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_offset_map: Mapped[list[int]] = mapped_column(JSONB)
    extractor_version: Mapped[str] = mapped_column(String)


class ChunkRow(Base):
    """Map only finite same-space vectors attached to exact item/revision/block membership."""

    __tablename__ = "knowledge_chunks"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    company_id: Mapped[UUID]
    item_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    block_id: Mapped[UUID]
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String)
    token_count: Mapped[int] = mapped_column(Integer)
    locator: Mapped[dict[str, Any]] = mapped_column(JSONB)
    text_sha256: Mapped[str] = mapped_column(String)
    pipeline_version: Mapped[str] = mapped_column(String)
    embedding_model: Mapped[str] = mapped_column(String)
    dimensions: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))


class JobRow(Base):
    """Map durable ingestion state, attempt counters and fencing tokens, never browser secrets."""

    __tablename__ = "ingestion_jobs"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    company_id: Mapped[UUID]
    revision_id: Mapped[UUID]
    pipeline_version: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    attempt_count: Mapped[int] = mapped_column(Integer)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[UUID | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_version: Mapped[int] = mapped_column(Integer)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PipelineRow(Base):
    """Map immutable processing/vector-space configuration independently from Chat's model settings."""

    __tablename__ = "pipeline_configurations"
    version: Mapped[str] = mapped_column(String, primary_key=True)
    normalization_version: Mapped[str] = mapped_column(String)
    extractor_versions: Mapped[dict[str, str]] = mapped_column(JSONB)
    splitter_name: Mapped[str] = mapped_column(String)
    chunk_tokens: Mapped[int] = mapped_column(Integer)
    overlap_tokens: Mapped[int] = mapped_column(Integer)
    embedding_model: Mapped[str] = mapped_column(String)
    dimensions: Mapped[int] = mapped_column(Integer)
    tokenizer: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
