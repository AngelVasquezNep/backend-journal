"""Final atomic source snapshot is the release checkpoint; expired/reclaimed attempts cannot reuse it."""

from uuid import uuid4

from taskify_chat.application.conversations import open_conversation
from taskify_chat.application.process_turn import process
from taskify_chat.application.submit_message import submit


def accepted(service, principal):
    """Create one owned durable question for checkpoint/race fixtures, never a public seed route."""
    open_conversation(service, principal)
    return submit(service, principal, uuid4(), "Company leave policy?", 0)


def test_source_removed_before_final_snapshot_blocks_entire_draft(
    chat_service, chat_principal, knowledge_double, chat_worker
) -> None:
    """A source changing after retrieval but before validation produces a safe retryable failure."""
    turn = accepted(chat_service, chat_principal)
    knowledge_double.current = False
    assert chat_worker.run_once()
    with chat_service.store.transaction(chat_principal) as transaction:
        result = transaction.turn(turn.turn.id)
        assert result.error_code == "information_changed" and result.state == "failed"
        assert not transaction.citations(result.assistant_message_id)
        assert "20 days" not in transaction.message(result.assistant_message_id).content


def test_source_changed_after_snapshot_permits_validated_answer_and_disables_future_links(
    chat_service, chat_principal, knowledge_double, chat_worker
) -> None:
    """Changes after the consistency checkpoint do not retroactively reject a verified saved answer."""
    turn = accepted(chat_service, chat_principal)
    validate = knowledge_double.validate

    def after_snapshot(*args):
        """Simulate removal immediately after Knowledge's atomic successful source snapshot."""
        receipt = validate(*args)
        knowledge_double.current = False
        return receipt

    knowledge_double.validate = after_snapshot
    assert chat_worker.run_once()
    with chat_service.store.transaction(chat_principal) as transaction:
        result = transaction.turn(turn.turn.id)
        assert result.state == "completed"
        assert transaction.message(result.assistant_message_id).outcome == "answer"
        references = transaction.citations(result.assistant_message_id)
        assert references[0].revision_id == knowledge_double.evidence.revision_id


def test_expired_lease_after_snapshot_must_revalidate_on_reclaim(
    chat_service, chat_principal, knowledge_double, clock
) -> None:
    """An obsolete receipt cannot authorize a recovered attempt or a second terminal save."""
    turn = accepted(chat_service, chat_principal)
    first = chat_service.store.claim(uuid4(), clock.now())
    validate = knowledge_double.validate
    calls = []

    def expire_once(*args):
        """Expire this holder only after obtaining a fresh first receipt, then invalidate sources."""
        calls.append(1)
        receipt = validate(*args)
        if len(calls) == 1:
            clock.advance(31)
            knowledge_double.current = False
        return receipt

    knowledge_double.validate = expire_once
    assert not process(chat_service, first)
    recovered = chat_service.store.claim(uuid4(), clock.now())
    assert recovered.lease_version > first.lease_version
    assert process(chat_service, recovered)
    assert len(calls) == 2
    with chat_service.store.transaction(chat_principal) as transaction:
        assert transaction.turn(turn.turn.id).error_code == "information_changed"
        assert len(transaction.messages(turn.turn.conversation_id)) == 2
