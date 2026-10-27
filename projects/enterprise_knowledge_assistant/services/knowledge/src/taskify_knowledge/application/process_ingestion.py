"""Leased whole-revision processing runs outside transactions and publishes under a fresh fence."""

import hashlib
import logging
from dataclasses import replace
from datetime import timedelta

from taskify_knowledge.application.ports.storage import Original
from taskify_knowledge.application.service import KnowledgeService
from taskify_knowledge.domain.block import ExtractedBlock
from taskify_knowledge.domain.chunk import KnowledgeChunk
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.ingestion_job import MAX_INGESTION_ATTEMPTS, IngestionJob


def process(service: KnowledgeService, job: IngestionJob) -> bool:
    """Validate stored ownership, extract/embed outside locks, then atomically publish complete current data."""
    try:
        if job.pipeline_version != service.pipeline.version:
            raise ApplicationError(
                "configuration_changed", "Processing configuration changed.", 422
            )
        with service.store.transaction(job.company_id) as transaction:
            if not transaction.live_job(job, service.clock.now()):
                return False
            revision = transaction.revision(job.revision_id)
            item = transaction.item(revision.item_id) if revision else None
            if (
                revision is None
                or item is None
                or item.removed_at is not None
                or item.candidate_revision_id != revision.id
                or revision.state != "processing"
            ):
                return False
        original = Original(
            revision.storage_key,
            revision.original_filename,
            revision.media_type,
            revision.size_bytes,
            revision.sha256,
        )
        service.storage.verify(original)
        extracted = service.extractor.extract(original)
        blocks = tuple(
            ExtractedBlock(
                ordinal=value.ordinal,
                normalized_text=value.normalized_text,
                locator=value.locator,
                source_offset_map=value.source_offset_map,
                extractor_version=value.extractor_version,
                id=service.ids.new(),
                company_id=job.company_id,
                revision_id=revision.id,
            )
            for value in extracted
        )
        fragments = service.chunker.split(blocks)
        if not fragments:
            raise ApplicationError(
                "unreadable_file", "The file does not contain readable supported text.", 422
            )
        vectors = service.embedder.embed(tuple(value.text for value in fragments))
        if len(vectors) != len(fragments):
            raise ValueError("Embedding count mismatch.")
        chunks = tuple(
            KnowledgeChunk(
                id=service.ids.new(),
                company_id=job.company_id,
                item_id=item.id,
                revision_id=revision.id,
                block_id=fragment.block.id,
                ordinal=fragment.ordinal,
                text=fragment.text,
                token_count=fragment.token_count,
                locator=fragment.locator,
                text_sha256=hashlib.sha256(fragment.text.encode("utf-8")).hexdigest(),
                pipeline_version=service.pipeline.version,
                embedding_model=service.pipeline.embedding_model,
                dimensions=1536,
                embedding=vector,
            )
            for fragment, vector in zip(fragments, vectors, strict=True)
        )
        service.storage.verify(original)
        now = service.clock.now()
        with service.store.transaction(job.company_id) as transaction:
            current = transaction.item(item.id, lock=True)
            if not transaction.live_job(job, now):
                return False
            latest_revision = transaction.revision(revision.id)
            if (
                current is None
                or current.removed_at is not None
                or current.candidate_revision_id != revision.id
                or latest_revision is None
                or latest_revision.state != "processing"
            ):
                return False
            transaction.stage_chunks(revision.id, blocks, chunks)
            if current.active_revision_id:
                previous = transaction.revision(current.active_revision_id)
                if previous is not None:
                    transaction.save_revision(replace(previous, state="superseded"))
            transaction.save_revision(
                replace(latest_revision, state="ready", ready_at=now, error_code=None)
            )
            transaction.save_item(
                replace(
                    current,
                    active_revision_id=revision.id,
                    candidate_revision_id=None,
                    version=current.version + 1,
                    updated_at=now,
                )
            )
            transaction.save_job(
                replace(
                    job, state="succeeded", lease_owner=None, lease_until=None, last_error_code=None
                )
            )
            transaction.commit()
        logging.getLogger("taskify.ingestion").info(
            "ingestion_terminal outcome=ready chunks=%d attempt=%d", len(chunks), job.attempt_count
        )
        return True
    except ApplicationError as error:
        return failed(service, job, error.code, error.status >= 500)
    except Exception:
        return failed(service, job, "processing_unavailable", True)


def failed(service: KnowledgeService, job: IngestionJob, code: str, transient: bool) -> bool:
    """Persist bounded transient backoff or a safe permanent failure while retaining any old ready data."""
    from taskify_knowledge.domain.revision import ERROR_MESSAGES

    safe_code = code if code in ERROR_MESSAGES else "processing_unavailable"
    now = service.clock.now()
    with service.store.transaction(job.company_id) as transaction:
        revision = transaction.revision(job.revision_id)
        if revision is None:
            return False
        item = transaction.item(revision.item_id, lock=True)
        if not transaction.live_job(job, now):
            return False
        if item is None or item.removed_at is not None or revision.state != "processing":
            return False
        retry = transient and job.attempt_count < MAX_INGESTION_ATTEMPTS
        transaction.save_job(
            replace(
                job,
                state="queued" if retry else "failed",
                run_after=now + timedelta(seconds=2**job.attempt_count + service.retry_jitter())
                if retry
                else now,
                lease_owner=None,
                lease_until=None,
                last_error_code=safe_code,
            )
        )
        if not retry:
            transaction.save_revision(replace(revision, state="failed", error_code=safe_code))
        transaction.commit()
    logging.getLogger("taskify.ingestion").info(
        "ingestion_outcome state=%s code=%s attempt=%d",
        "queued" if retry else "failed",
        safe_code,
        job.attempt_count,
    )
    return True
