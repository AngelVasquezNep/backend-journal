"""Publication races preserve current title/version and removal cancels a leased candidate atomically."""

from taskify_knowledge.application.maintain_knowledge import remove, rename
from taskify_knowledge.application.read_knowledge import read
from taskify_knowledge.application.upload import upload


def test_rename_during_processing_survives_publication(
    knowledge_service, knowledge_worker, admin_principal
) -> None:
    """A title edit during processing is retained by locked publication with a further version increment."""
    created = upload(
        knowledge_service,
        admin_principal,
        "Before",
        "policy.txt",
        "text/plain",
        iter([b"Company policy text."]),
    )
    renamed = rename(
        knowledge_service, admin_principal, created.item.id, created.item.version, "After"
    )
    assert knowledge_worker.run_once()
    published = read(knowledge_service, admin_principal, created.item.id)
    assert published.item.title == "After" and published.item.version == renamed.item.version + 1


def test_remove_before_publication_cancels_current_lease(
    knowledge_service, knowledge_worker, admin_principal
) -> None:
    """Removing a candidate cancels its job and prevents the old lease from publishing any content."""
    created = upload(
        knowledge_service,
        admin_principal,
        "Policy",
        "policy.txt",
        "text/plain",
        iter([b"Company policy text."]),
    )
    claim = knowledge_worker.claim()
    assert claim is not None
    remove(knowledge_service, admin_principal, created.item.id, created.item.version)
    assert not knowledge_worker.process(claim)
    with knowledge_service.store.transaction(admin_principal.company_id) as transaction:
        removed = transaction.item(created.item.id)
        revision = transaction.revision(created.candidate_revision.id)
        assert removed.removed_at is not None and removed.candidate_revision_id is None
        assert revision.state == "cancelled"
