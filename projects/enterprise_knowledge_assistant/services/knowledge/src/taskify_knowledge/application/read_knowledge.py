"""Authorized item/status/original reads keep metadata and bytes inside the current company."""

from uuid import UUID

from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.application.ports.knowledge_store import ItemPage, ItemView
from taskify_knowledge.application.ports.storage import Original
from taskify_knowledge.application.service import KnowledgeService, allowed
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.revision import KnowledgeRevision
from taskify_knowledge.domain.values import Pagination


def listing(service: KnowledgeService, actor: Principal, pagination: Pagination) -> ItemPage:
    """Return only nonremoved company items; users see current ready revisions only."""
    allowed(actor)
    with service.store.transaction(actor.company_id) as transaction:
        return transaction.page(actor, pagination)


def read(service: KnowledgeService, actor: Principal, item_id: UUID) -> ItemView:
    """Read exact owned metadata; unknown, foreign and user-unready items share a 404."""
    allowed(actor)
    with service.store.transaction(actor.company_id) as transaction:
        item = transaction.item(item_id)
        if item is None or item.removed_at is not None:
            raise ApplicationError("not_found", "Resource not found.", 404)
        view = transaction.view(item)
        if actor.role != "admin" and view.availability != "ready":
            raise ApplicationError("not_found", "Resource not found.", 404)
        return view


def revision_status(
    service: KnowledgeService, actor: Principal, item_id: UUID, revision_id: UUID
) -> KnowledgeRevision:
    """Expose processing/status only to same-company admins with an exact item/revision pair."""
    allowed(actor, admin=True)
    with service.store.transaction(actor.company_id) as transaction:
        item, revision = transaction.item(item_id), transaction.revision(revision_id)
        if (
            item is None
            or item.removed_at is not None
            or revision is None
            or revision.item_id != item_id
        ):
            raise ApplicationError("not_found", "Resource not found.", 404)
        return revision


def source(
    service: KnowledgeService, actor: Principal, item_id: UUID, revision_id: UUID
) -> Original:
    """Authorize the exact current original; historical own-company unavailability is 410, foreign is 404."""
    allowed(actor)
    with service.store.transaction(actor.company_id) as transaction:
        item, revision = transaction.item(item_id), transaction.revision(revision_id)
        if item is None or revision is None or revision.item_id != item_id:
            raise ApplicationError("not_found", "Resource not found.", 404)
        if (
            item.removed_at is not None
            or item.active_revision_id != revision_id
            or revision.state != "ready"
        ):
            raise ApplicationError("source_unavailable", "This source changed or was removed.", 410)
        original = Original(
            revision.storage_key,
            revision.original_filename,
            revision.media_type,
            revision.size_bytes,
            revision.sha256,
        )
    service.storage.verify(original)
    return original
