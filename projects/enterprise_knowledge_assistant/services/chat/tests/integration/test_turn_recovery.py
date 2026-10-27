"""Whole-turn recovery fences stale workers, pins accepted answer settings and discards ephemeral receipts."""

from uuid import uuid4

from taskify_chat.application.conversations import open_conversation
from taskify_chat.application.process_turn import process
from taskify_chat.application.submit_message import submit


def test_reclaim_is_single_terminal_and_retrieval_version_is_terminal_only(
    chat_service, chat_principal, clock
) -> None:
    """A recovered attempt searches fresh; only its final retrieval version is persisted."""
    service = chat_service
    open_conversation(service, chat_principal)
    accepted = submit(service, chat_principal, uuid4(), "What is the company leave policy?", 0)
    assert accepted.turn.retrieval_config_version is None
    first = service.store.claim(uuid4(), clock.now())
    assert first is not None
    clock.advance(31)
    second = service.store.claim(uuid4(), clock.now())
    assert second is not None and second.lease_version > first.lease_version
    assert not process(service, first)
    service.knowledge.version = "retrieval-current-after-restart"
    assert process(service, second)
    with service.store.transaction(chat_principal) as transaction:
        final = transaction.turn(accepted.turn.id)
        assert final.state == "completed" and final.model == accepted.turn.model
        assert final.retrieval_config_version == "retrieval-current-after-restart"
        assert len(transaction.messages(final.conversation_id, limit=100)) == 2
    assert not process(service, second)


def test_expired_accepting_login_prevents_facts_but_retains_history(
    chat_service, chat_principal, clock
) -> None:
    """Expired sessions produce one safe failure rather than releasing an unverified factual draft."""
    open_conversation(chat_service, chat_principal)
    accepted = submit(chat_service, chat_principal, uuid4(), "What is the company leave policy?", 0)
    clock.advance(1800)
    claim = chat_service.store.claim(uuid4(), clock.now())
    assert claim is not None
    assert process(chat_service, claim)
    with chat_service.store.transaction(chat_principal) as transaction:
        terminal = transaction.turn(accepted.turn.id)
        assert terminal.error_code == "authentication_required"
        result = transaction.message(terminal.assistant_message_id)
        assert result.outcome == "failure" and "20 days" not in result.content
