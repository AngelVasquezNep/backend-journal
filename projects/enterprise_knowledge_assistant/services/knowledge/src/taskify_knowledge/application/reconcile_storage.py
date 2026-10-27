"""Conservative bounded orphan cleanup never changes database availability or deletes referenced originals."""

from datetime import timedelta

from taskify_knowledge.application.service import KnowledgeService


def reconcile(service: KnowledgeService) -> int:
    """Remove complete originals older than 24 hours only under the same guard used by acceptance.

    Ambiguous commits remain safe: every retained revision is a reference, including
    failed/superseded revisions. Any unavailable database aborts cleanup before deletion.
    Staging locks protect active streams; obsolete metadata remains for historical source identity.
    """
    removed = 0
    for key in service.storage.stale_objects(service.clock.now() - timedelta(hours=24)):
        with service.storage.protect(key, blocking=False) as protected:
            if protected and not service.store.references_original(key):
                service.storage.remove(key)
                removed += 1
    for company_id, revision_id, key in service.store.retirable_originals(
        service.clock.now() - timedelta(hours=24)
    ):
        with service.storage.protect(key, blocking=False) as protected:
            if not protected:
                continue
            with service.store.transaction(company_id) as transaction:
                if transaction.retire_revision(revision_id, key):
                    service.storage.remove(key)
                    transaction.commit()
                    removed += 1
    return removed
