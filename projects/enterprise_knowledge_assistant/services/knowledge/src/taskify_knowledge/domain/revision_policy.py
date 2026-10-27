"""Pure item mutation rules preserve immutable originals and prevent lost admin updates/publication after removal."""

from dataclasses import replace
from datetime import datetime

from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.item import KnowledgeItem
from taskify_knowledge.domain.values import Title, positive_version


def editable(item: KnowledgeItem | None, expected: int) -> KnowledgeItem:
    """Require a live owned item and exact positive version before any edit can be committed."""
    if item is None or item.removed_at is not None:
        raise ApplicationError("not_found", "Resource not found.", 404)
    try:
        positive_version(expected)
    except ValueError:
        raise ApplicationError(
            "validation_failed", "Use the quoted current item version.", 422
        ) from None
    if item.version != expected:
        raise ApplicationError(
            "version_conflict", "This item changed. Reload it before editing.", 409
        )
    return item


def renamed(item: KnowledgeItem, title: str, now: datetime) -> KnowledgeItem:
    """Change only canonical title/version; a processing candidate and valid old original remain intact."""
    try:
        canonical = Title(title).value
    except ValueError:
        raise ApplicationError(
            "validation_failed", "Titles must contain 1–200 characters and no controls.", 422
        ) from None
    return replace(item, title=canonical, version=item.version + 1, updated_at=now)


def removed(item: KnowledgeItem, now: datetime) -> KnowledgeItem:
    """Clear visibility pointers immediately; a removed item's pending candidate becomes cancelled.

    Revision states: processing → ready or failed; an active ready revision becomes superseded.
    Removal additionally permits processing → cancelled and forbids later publication.
    """
    return replace(
        item,
        active_revision_id=None,
        candidate_revision_id=None,
        removed_at=now,
        version=item.version + 1,
        updated_at=now,
    )
