"""Own conversation creation and history reads never accept a client-selected conversation or account."""

from dataclasses import dataclass
from uuid import UUID

from taskify_chat.application.ports.identity import Principal
from taskify_chat.application.service import ChatService, allowed
from taskify_chat.domain.conversation import Conversation
from taskify_chat.domain.errors import ApplicationError
from taskify_chat.domain.message import ChatMessage
from taskify_chat.domain.values import Pagination


@dataclass(frozen=True)
class ConversationView:
    """Public own-conversation metadata includes the active durable turn for reload recovery."""

    conversation: Conversation
    active_turn_id: UUID | None


@dataclass(frozen=True)
class MessagePage:
    """Own history remains stored in full; only server pages and model context are bounded."""

    messages: tuple[ChatMessage, ...]
    next_cursor: str | None
    last_sequence: int


def open_conversation(
    service: ChatService, actor: Principal, *, create: bool = True
) -> ConversationView:
    """Exactly one conversation/account, never visible to another account; lazy creation is atomic."""
    allowed(actor)
    with service.store.transaction(actor) as transaction:
        current = transaction.conversation(lock=create)
        if current is None:
            if not create:
                raise ApplicationError("not_found", "Conversation not found.", 404)
            now = service.clock.now()
            current = Conversation(
                id=service.ids.new(),
                company_id=actor.company_id,
                account_id=actor.account_id,
                last_sequence=0,
                created_at=now,
                updated_at=now,
            )
            transaction.save_conversation(current)
        active = transaction.active()
        transaction.commit()
        return ConversationView(current, active.id if active else None)


def history(service: ChatService, actor: Principal, pagination: Pagination) -> MessagePage:
    """Read a tenant/account-filtered newest page in chronological order with owner-scoped continuation."""
    allowed(actor)
    before = service.store.decode_cursor(actor, pagination.cursor) if pagination.cursor else None
    with service.store.transaction(actor) as transaction:
        conversation = transaction.conversation()
        if conversation is None:
            raise ApplicationError("not_found", "Conversation not found.", 404)
        messages = transaction.messages(conversation.id, limit=pagination.limit + 1, before=before)
        older = len(messages) > pagination.limit
        page = messages[-pagination.limit :]
        cursor = service.store.encode_cursor(actor, page[0].sequence) if older else None
        return MessagePage(page, cursor, conversation.last_sequence)
