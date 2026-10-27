"""Admin company mutations use exact CAS and immutable replacement originals with old-ready preservation."""

from collections.abc import Callable, Iterable
from dataclasses import replace
from uuid import UUID

from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.application.ports.knowledge_store import ItemView
from taskify_knowledge.application.service import KnowledgeService, allowed
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.ingestion_job import IngestionJob
from taskify_knowledge.domain.revision import KnowledgeRevision
from taskify_knowledge.domain.revision_policy import editable, removed, renamed


def rename(
    service: KnowledgeService, actor: Principal, item_id: UUID, expected: int, title: str
) -> ItemView:
    """Lock and rename the exact current version, preserving processing/current original identities."""
    allowed(actor, admin=True)
    with service.store.transaction(actor.company_id) as transaction:
        item = editable(transaction.item(item_id, lock=True), expected)
        updated = renamed(item, title, service.clock.now())
        transaction.save_item(updated)
        view = transaction.view(updated)
        transaction.commit()
        return view


def replace_original(
    service: KnowledgeService,
    actor: Principal,
    item_id: UUID,
    expected: int,
    filename: str,
    media_type: str,
    content: Iterable[bytes],
    *,
    reauthorize: Callable[[], Principal] | None = None,
) -> ItemView:
    """Stage a validated original, then atomically CAS one candidate/job while retaining the old ready revision."""
    allowed(actor, admin=True)
    with service.store.transaction(actor.company_id) as transaction:
        item = editable(transaction.item(item_id), expected)
        if item.candidate_revision_id:
            candidate = transaction.revision(item.candidate_revision_id)
            if candidate and candidate.state == "processing":
                raise ApplicationError(
                    "replacement_in_progress",
                    "Wait for the current candidate before replacing again.",
                    409,
                )
    original = service.storage.stage(filename, media_type, content)
    with service.storage.protect(original.storage_key):
        service.storage.verify(original)
        with service.store.transaction(actor.company_id) as transaction:
            item = editable(transaction.item(item_id, lock=True), expected)
            if item.candidate_revision_id:
                candidate = transaction.revision(item.candidate_revision_id)
                if candidate and candidate.state == "processing":
                    raise ApplicationError(
                        "replacement_in_progress",
                        "Wait for the current candidate before replacing again.",
                        409,
                    )
            now = service.clock.now()
            revision = KnowledgeRevision(
                id=service.ids.new(),
                company_id=actor.company_id,
                item_id=item.id,
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
                revision_id=revision.id,
                pipeline_version=service.pipeline.version,
                state="queued",
                attempt_count=0,
                run_after=now,
                created_at=now,
            )
            updated = replace(
                item, candidate_revision_id=revision.id, version=item.version + 1, updated_at=now
            )
            transaction.save_revision(revision)
            transaction.save_job(job)
            transaction.save_item(updated)
            view = ItemView(
                updated,
                transaction.revision(item.active_revision_id) if item.active_revision_id else None,
                revision,
            )
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
            return view


def remove(service: KnowledgeService, actor: Principal, item_id: UUID, expected: int) -> None:
    """Immediately exclude an item and cancel pending work under item-before-job lock ordering."""
    allowed(actor, admin=True)
    with service.store.transaction(actor.company_id) as transaction:
        item = editable(transaction.item(item_id, lock=True), expected)
        if item.candidate_revision_id:
            transaction.cancel_jobs(item.candidate_revision_id)
            candidate = transaction.revision(item.candidate_revision_id)
            if candidate is not None and candidate.state == "processing":
                transaction.save_revision(replace(candidate, state="cancelled"))
        if item.active_revision_id:
            active = transaction.revision(item.active_revision_id)
            if active is not None and active.state == "ready":
                transaction.save_revision(replace(active, state="superseded"))
        transaction.save_item(removed(item, service.clock.now()))
        transaction.commit()
