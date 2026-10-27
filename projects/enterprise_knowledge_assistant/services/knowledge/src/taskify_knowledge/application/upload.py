"""Accept a validated original and durable item/revision/job atomically within its company."""

from collections.abc import Callable, Iterable

from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.application.ports.knowledge_store import ItemView
from taskify_knowledge.application.service import KnowledgeService, allowed
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.ingestion_job import IngestionJob
from taskify_knowledge.domain.item import KnowledgeItem
from taskify_knowledge.domain.revision import KnowledgeRevision
from taskify_knowledge.domain.values import Title


def upload(
    service: KnowledgeService,
    actor: Principal,
    title: str,
    filename: str,
    media_type: str,
    content: Iterable[bytes],
    *,
    reauthorize: Callable[[], Principal] | None = None,
) -> ItemView:
    """Stage/validate before persistence; accepted work is durable before returning processing state."""
    allowed(actor, admin=True)
    try:
        canonical = Title(title).value
    except ValueError:
        raise ApplicationError(
            "validation_failed", "Titles must contain 1–200 characters and no controls.", 422
        ) from None
    original = service.storage.stage(filename, media_type, content)
    now = service.clock.now()
    item_id, revision_id = service.ids.new(), service.ids.new()
    item = KnowledgeItem(
        id=item_id,
        company_id=actor.company_id,
        title=canonical,
        created_by=actor.account_id,
        candidate_revision_id=revision_id,
        created_at=now,
        updated_at=now,
    )
    revision = KnowledgeRevision(
        id=revision_id,
        company_id=actor.company_id,
        item_id=item_id,
        uploaded_by=actor.account_id,
        original_filename=original.original_filename,
        media_type=original.media_type,
        size_bytes=original.size_bytes,
        sha256=original.sha256,
        storage_key=original.storage_key,
        state="processing",
        pipeline_version=service.pipeline.version,
        created_at=now,
    )
    job = IngestionJob(
        id=service.ids.new(),
        company_id=actor.company_id,
        revision_id=revision_id,
        pipeline_version=service.pipeline.version,
        state="queued",
        attempt_count=0,
        run_after=now,
        created_at=now,
    )
    # A failed/ambiguous DB commit leaves an unreferenced object for later reconciliation.
    # Deleting it here could destroy a committed original after a lost commit acknowledgment.
    with service.storage.protect(original.storage_key):
        service.storage.verify(original)
        with service.store.transaction(actor.company_id) as transaction:
            transaction.save_item(item)
            transaction.save_revision(revision)
            transaction.save_job(job)
            if reauthorize is not None:
                current = reauthorize()
                allowed(current, admin=True)
                if (current.company_id, current.account_id, current.login_session_id) != (
                    actor.company_id,
                    actor.account_id,
                    actor.login_session_id,
                ):
                    from taskify_knowledge.domain.errors import AuthenticationRequired

                    raise AuthenticationRequired()
            transaction.commit()
    return ItemView(item, None, revision)
