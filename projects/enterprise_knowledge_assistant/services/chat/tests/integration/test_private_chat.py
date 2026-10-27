"""Private saved-chat ownership and atomic acceptance hold under real PostgreSQL concurrency."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from taskify_chat.application.conversations import history, open_conversation
from taskify_chat.application.submit_message import submit
from taskify_chat.domain.errors import ApplicationError
from taskify_chat.domain.values import Pagination


def test_concurrent_open_and_identical_acceptance_are_atomic(chat_service, chat_principal) -> None:
    """Concurrent initial opens/replays create exactly one conversation and one user/turn pair."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        opened = list(
            executor.map(lambda _: open_conversation(chat_service, chat_principal), range(2))
        )
    assert opened[0].conversation.id == opened[1].conversation.id
    client_id = uuid4()
    with ThreadPoolExecutor(max_workers=2) as executor:
        turns = list(
            executor.map(
                lambda _: submit(chat_service, chat_principal, client_id, "Leave policy?", 0),
                range(2),
            )
        )
    assert turns[0].turn.id == turns[1].turn.id
    assert len(history(chat_service, chat_principal, Pagination()).messages) == 1


def test_forced_rls_and_cursor_scope_exclude_same_company_accounts(
    chat_service, chat_principal
) -> None:
    """Changing an account selector/cursor cannot read another same-company private conversation."""
    own = open_conversation(chat_service, chat_principal)
    other = replace(chat_principal, account_id=uuid4(), login_session_id=uuid4())
    open_conversation(chat_service, other)
    with chat_service.store.transaction(other) as transaction:
        assert (
            transaction.session.execute(
                text("SELECT id FROM conversations WHERE id=:id"), {"id": own.conversation.id}
            ).first()
            is None
        )
    cursor = chat_service.store.encode_cursor(chat_principal, 2)
    with pytest.raises(ApplicationError):
        chat_service.store.decode_cursor(other, cursor)
    with chat_service.store.engine.connect() as connection:
        assert connection.execute(text("SELECT id FROM conversations")).first() is None


def test_three_abandoned_claims_produce_one_terminal_failure(
    chat_service, chat_principal, clock
) -> None:
    """Recovery never claims a fourth paid attempt and atomically appends one safe assistant result."""
    open_conversation(chat_service, chat_principal)
    accepted = submit(chat_service, chat_principal, uuid4(), "Leave policy?", 0)
    for attempt in range(1, 4):
        claim = chat_service.store.claim(uuid4(), clock.now())
        assert claim is not None and claim.attempt_count == attempt
        clock.advance(31)
    assert chat_service.store.claim(uuid4(), clock.now()) is None
    with chat_service.store.transaction(chat_principal) as transaction:
        final = transaction.turn(accepted.turn.id)
        assert final.state == "failed" and final.retrieval_config_version is None
        assert len(transaction.messages(final.conversation_id)) == 2
    assert chat_service.store.claim(uuid4(), clock.now()) is None


def test_accepted_configuration_and_owner_cannot_change(chat_service, chat_principal) -> None:
    """Database triggers reject changing accepted models or owner context even from service SQL."""
    open_conversation(chat_service, chat_principal)
    accepted = submit(chat_service, chat_principal, uuid4(), "Leave policy?", 0)
    with pytest.raises(DBAPIError):
        with chat_service.store.transaction(chat_principal) as transaction:
            transaction.session.execute(
                text("UPDATE chat_turns SET model='different-model' WHERE id=:id"),
                {"id": accepted.turn.id},
            )
            transaction.commit()
