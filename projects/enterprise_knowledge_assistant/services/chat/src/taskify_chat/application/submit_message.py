"""Durable message acceptance resolves network replay before sequence/active-turn checks."""

from dataclasses import dataclass, replace
from uuid import UUID

from taskify_chat.application.ports.identity import Principal
from taskify_chat.application.service import ChatService, allowed
from taskify_chat.domain.errors import ApplicationError
from taskify_chat.domain.message import ChatMessage
from taskify_chat.domain.turn import ChatTurn
from taskify_chat.domain.values import MessageText, sequence


@dataclass(frozen=True)
class TurnView:
    """A pending turn has only its committed user message; terminal results are never streamed drafts."""

    turn: ChatTurn
    user_message: ChatMessage
    assistant_message: ChatMessage | None


def submit(
    service: ChatService, actor: Principal, client_id: UUID, content: str, expected_sequence: int
) -> TurnView:
    """Atomically save a question and queued turn with accepted model/graph/prompt/profile settings."""
    allowed(actor)
    try:
        canonical = MessageText(content).value
        sequence(expected_sequence)
        if not isinstance(client_id, UUID):
            raise ValueError()
    except ValueError:
        raise ApplicationError(
            "validation_failed",
            "Use a UUID, 1–4000 character question and nonnegative sequence.",
            422,
        ) from None
    with service.store.transaction(actor) as transaction:
        conversation = transaction.conversation(lock=True)
        if conversation is None:
            raise ApplicationError("not_found", "Open your conversation first.", 404)
        prior = transaction.replay(client_id)
        if prior is not None:
            question = transaction.message(prior.user_message_id)
            if question is None or question.content != canonical:
                raise ApplicationError(
                    "idempotency_conflict",
                    "This message ID was already used for different content.",
                    409,
                )
            return TurnView(
                prior,
                question,
                transaction.message(prior.assistant_message_id)
                if prior.assistant_message_id
                else None,
            )
        if transaction.active() is not None:
            raise ApplicationError(
                "turn_in_progress",
                "Wait for the current answer before sending another question.",
                409,
            )
        if expected_sequence != conversation.last_sequence:
            raise ApplicationError(
                "conversation_changed", "Reload the current conversation before sending.", 409
            )
        now = service.clock.now()
        turn_id, message_id = service.ids.new(), service.ids.new()
        configuration = service.configuration
        turn = ChatTurn(
            id=turn_id,
            company_id=actor.company_id,
            account_id=actor.account_id,
            conversation_id=conversation.id,
            client_message_id=client_id,
            user_message_id=message_id,
            accepted_login_session_id=actor.login_session_id,
            state="queued",
            created_at=now,
            ai_mode=configuration.ai_mode,
            model=configuration.model,
            graph_version=configuration.graph_version,
            prompt_version=configuration.prompt_version,
            model_config_version=configuration.model_config_version,
        )
        message = ChatMessage(
            id=message_id,
            company_id=actor.company_id,
            account_id=actor.account_id,
            conversation_id=conversation.id,
            turn_id=turn_id,
            sequence=conversation.last_sequence + 1,
            sender="user",
            content=canonical,
            created_at=now,
        )
        transaction.save_turn(turn)
        transaction.save_message(message)
        transaction.save_conversation(
            replace(conversation, last_sequence=message.sequence, updated_at=now)
        )
        transaction.commit()
        return TurnView(turn, message, None)


def read_turn(service: ChatService, actor: Principal, turn_id: UUID) -> TurnView:
    """Read only the authenticated account's committed processing or terminal result."""
    allowed(actor)
    with service.store.transaction(actor) as transaction:
        turn = transaction.turn(turn_id)
        if turn is None:
            raise ApplicationError("not_found", "Turn not found.", 404)
        user = transaction.message(turn.user_message_id)
        if user is None:
            raise ApplicationError(
                "dependency_unavailable", "The conversation could not be loaded.", 503
            )
        return TurnView(
            turn,
            user,
            transaction.message(turn.assistant_message_id) if turn.assistant_message_id else None,
        )
