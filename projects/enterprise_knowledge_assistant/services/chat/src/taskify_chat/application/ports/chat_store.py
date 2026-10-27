"""Chat-owned persistence exposes private immutable core values and fenced short transactions."""

from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from taskify_chat.application.ports.identity import Principal
from taskify_chat.domain.citation import Citation
from taskify_chat.domain.conversation import Conversation
from taskify_chat.domain.message import ChatMessage
from taskify_chat.domain.turn import ChatTurn


class ChatTransaction(Protocol):
    """Account-scoped unit of work; no SQL types or foreign service storage enter core."""

    def __enter__(self) -> Self:
        """Enter trusted company/account context with no previous account's pooled settings."""
        ...

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Rollback any uncommitted attempt and release locks/resources."""
        ...

    def commit(self) -> None:
        """Atomically persist all accepted/terminal state or fail closed."""
        ...

    def conversation(self, *, lock: bool = False) -> Conversation | None:
        """Read only this account's conversation; lock serializes creation/sequence/active checks."""
        ...

    def save_conversation(self, value: Conversation) -> None:
        """Insert/update only this account's immutable owned conversation."""
        ...

    def turn(self, turn_id: UUID) -> ChatTurn | None:
        """Return an owned turn, never another account's even in the same company."""
        ...

    def replay(self, client_id: UUID) -> ChatTurn | None:
        """Find own idempotent acceptance before sequence/active-turn validation."""
        ...

    def active(self) -> ChatTurn | None:
        """Return at most one own queued/running turn for reload recovery."""
        ...

    def save_turn(self, value: ChatTurn) -> None:
        """Stage immutable accepted context or a live-fenced terminal transition."""
        ...

    def message(self, message_id: UUID) -> ChatMessage | None:
        """Read an exact own saved question/terminal result."""
        ...

    def messages(
        self, conversation_id: UUID, *, limit: int = 50, before: int | None = None
    ) -> tuple[ChatMessage, ...]:
        """Read a bounded newest page of own messages in chronological order."""
        ...

    def history(self, before: int) -> tuple[ChatMessage, ...]:
        """Load complete own prior messages for the adapter's 6000-token newest-message window."""
        ...

    def save_message(self, value: ChatMessage) -> None:
        """Insert a saved question or one terminal assistant; uniqueness prevents duplicate saves."""
        ...

    def citations(self, message_id: UUID) -> tuple[Citation, ...]:
        """Read only the owning assistant message's original evidence references."""
        ...

    def save_citation(self, value: Citation) -> None:
        """Insert only application-authorized evidence with immutable original provenance."""
        ...

    def live_turn(self, value: ChatTurn, now: datetime) -> bool:
        """Lock and require this exact current live lease before final source validation/commit."""
        ...


class ChatStore(Protocol):
    """Own all chat access; only narrow claims can enumerate pending work across accounts."""

    def transaction(self, actor: Principal) -> ChatTransaction:
        """Set transaction-local company/account from online Identity or stored worker authority."""
        ...

    def claim(self, worker: UUID, now: datetime) -> ChatTurn | None:
        """Claim/reclaim at most three times; expired exhausted turns receive one safe terminal result."""
        ...

    def heartbeat(self, turn: ChatTurn, now: datetime) -> bool:
        """Extend only this current lease; a stale/expired holder cannot resurrect itself."""
        ...

    def encode_cursor(self, actor: Principal, before: int) -> str:
        """Sign an owner/query-scoped history continuation without exposing an authority selector."""
        ...

    def decode_cursor(self, actor: Principal, cursor: str) -> int:
        """Reject malformed/tampered/foreign history cursors with a safe validation error."""
        ...
