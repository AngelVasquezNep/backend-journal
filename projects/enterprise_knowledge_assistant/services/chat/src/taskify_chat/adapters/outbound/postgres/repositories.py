"""Account-scoped owned repositories enforce idempotency, sequences and final SQL lease fencing."""

import base64
import hashlib
import hmac
import json
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import Engine, insert, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from taskify_chat.adapters.outbound.postgres.models import (
    chat_messages,
    chat_turns,
    citations,
    conversations,
)
from taskify_chat.adapters.outbound.postgres.unit_of_work import SqlUnitOfWork
from taskify_chat.application.ports.identity import Principal
from taskify_chat.domain.citation import Citation
from taskify_chat.domain.conversation import Conversation
from taskify_chat.domain.errors import ApplicationError
from taskify_chat.domain.message import ChatMessage
from taskify_chat.domain.turn import ChatTurn


class SqlChatTransaction(SqlUnitOfWork):
    """Only explicitly scoped queries execute on this transaction's resetting runtime pool."""

    def conversation(self, *, lock: bool = False) -> Conversation | None:
        """Serialize even lazy creation with one account advisory lock before reading a row."""
        assert self.session is not None
        if lock:
            self.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:account, 0))"),
                {"account": str(self.account_id)},
            )
        query = select(conversations).where(
            conversations.c.company_id == self.company_id,
            conversations.c.account_id == self.account_id,
        )
        if lock:
            query = query.with_for_update()
        row = self.session.execute(query).mappings().first()
        return Conversation(**row) if row else None

    def save_conversation(self, value: Conversation) -> None:
        """Upsert this owned conversation with immutable identity and monotonic application sequence."""
        assert self.session is not None
        data = asdict(value)
        self.session.execute(
            pg_insert(conversations)
            .values(**data)
            .on_conflict_do_update(
                index_elements=["id"],
                set_={"last_sequence": value.last_sequence, "updated_at": value.updated_at},
            )
        )

    def turn(self, turn_id: UUID) -> ChatTurn | None:
        """Apply RLS and explicit owned predicates to every exact turn lookup."""
        assert self.session is not None
        row = (
            self.session.execute(
                select(chat_turns).where(
                    chat_turns.c.id == turn_id,
                    chat_turns.c.company_id == self.company_id,
                    chat_turns.c.account_id == self.account_id,
                )
            )
            .mappings()
            .first()
        )
        return ChatTurn(**row) if row else None

    def replay(self, client_id: UUID) -> ChatTurn | None:
        """Resolve a same-account idempotency ID without requiring a matching obsolete sequence."""
        assert self.session is not None
        row = (
            self.session.execute(
                select(chat_turns).where(
                    chat_turns.c.client_message_id == client_id,
                    chat_turns.c.company_id == self.company_id,
                    chat_turns.c.account_id == self.account_id,
                )
            )
            .mappings()
            .first()
        )
        return ChatTurn(**row) if row else None

    def active(self) -> ChatTurn | None:
        """Return the database-enforced single active turn for this exact account."""
        assert self.session is not None
        row = (
            self.session.execute(
                select(chat_turns).where(
                    chat_turns.c.company_id == self.company_id,
                    chat_turns.c.account_id == self.account_id,
                    chat_turns.c.state.in_(["queued", "running"]),
                )
            )
            .mappings()
            .first()
        )
        return ChatTurn(**row) if row else None

    def save_turn(self, value: ChatTurn) -> None:
        """Insert immutable accepted context or update only mutable terminal/lease metadata."""
        assert self.session is not None
        data = asdict(value)
        keys = (
            "state",
            "attempt_count",
            "lease_owner",
            "lease_until",
            "lease_version",
            "completed_at",
            "assistant_message_id",
            "error_code",
            "retrieval_config_version",
        )
        self.session.execute(
            pg_insert(chat_turns)
            .values(**data)
            .on_conflict_do_update(index_elements=["id"], set_={key: data[key] for key in keys})
        )

    def message(self, message_id: UUID) -> ChatMessage | None:
        """Read no foreign message even when a fabricated UUID happens to identify one."""
        assert self.session is not None
        row = (
            self.session.execute(
                select(chat_messages).where(
                    chat_messages.c.id == message_id,
                    chat_messages.c.company_id == self.company_id,
                    chat_messages.c.account_id == self.account_id,
                )
            )
            .mappings()
            .first()
        )
        return ChatMessage(**row) if row else None

    def messages(
        self, conversation_id: UUID, *, limit: int = 50, before: int | None = None
    ) -> tuple[ChatMessage, ...]:
        """Page newest-first in SQL then restore chronological display order; tenant filtering precedes paging."""
        assert self.session is not None
        query = select(chat_messages).where(
            chat_messages.c.conversation_id == conversation_id,
            chat_messages.c.company_id == self.company_id,
            chat_messages.c.account_id == self.account_id,
        )
        if before is not None:
            query = query.where(chat_messages.c.sequence < before)
        rows = (
            self.session.execute(query.order_by(chat_messages.c.sequence.desc()).limit(limit))
            .mappings()
            .all()
        )
        return tuple(ChatMessage(**row) for row in reversed(rows))

    def history(self, before: int) -> tuple[ChatMessage, ...]:
        """Load a bounded newest suffix sufficient for the adapter's 6000-token complete-message budget."""
        conversation = self.conversation()
        return self.messages(conversation.id, limit=6001, before=before) if conversation else ()

    def save_message(self, value: ChatMessage) -> None:
        """Insert once; database uniqueness couples a message to its own turn/conversation/owner."""
        assert self.session is not None
        self.session.execute(insert(chat_messages).values(**asdict(value)))

    def citations(self, message_id: UUID) -> tuple[Citation, ...]:
        """Read original citation provenance only within the current private account context."""
        assert self.session is not None
        rows = (
            self.session.execute(
                select(citations)
                .where(
                    citations.c.assistant_message_id == message_id,
                    citations.c.company_id == self.company_id,
                    citations.c.account_id == self.account_id,
                )
                .order_by(citations.c.id)
            )
            .mappings()
            .all()
        )
        return tuple(Citation(**row) for row in rows)

    def save_citation(self, value: Citation) -> None:
        """Persist no remote URL; later source hydration resolves exact immutable IDs online."""
        assert self.session is not None
        self.session.execute(insert(citations).values(**asdict(value)))

    def live_turn(self, value: ChatTurn, now: datetime) -> bool:
        """Lock exact live owner/version and reject expired claims before any single-use source receipt."""
        assert self.session is not None
        row = (
            self.session.execute(
                select(chat_turns)
                .where(
                    chat_turns.c.id == value.id,
                    chat_turns.c.company_id == self.company_id,
                    chat_turns.c.account_id == self.account_id,
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        return bool(
            row
            and row["state"] == "running"
            and row["lease_owner"] == value.lease_owner
            and row["lease_version"] == value.lease_version
            and row["lease_until"] > now
        )


class SqlChatStore:
    """Own private storage and narrow unscoped queue claim functions; no graph checkpoints exist."""

    def __init__(self, engine: Engine, cursor_key: str) -> None:
        """Retain owned pool and domain-separated cursor signing material, excluded from DTOs/logs."""
        self.engine = engine
        self.cursor_key = hashlib.sha256(("chat-history-v1:" + cursor_key).encode()).digest()

    def transaction(self, actor: Principal) -> SqlChatTransaction:
        """Use online principal or stored queue ownership; never request JSON authority."""
        return SqlChatTransaction(self.engine, actor.company_id, actor.account_id)

    def claim(self, worker: UUID, now: datetime) -> ChatTurn | None:
        """Short SKIP LOCKED claim recovers from the first graph node with increasing fencing version."""
        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    text("SELECT * FROM taskify_claim_turn(:worker,:now)"),
                    {"worker": worker, "now": now},
                )
                .mappings()
                .first()
            )
            return ChatTurn(**row) if row else None

    def heartbeat(self, turn: ChatTurn, now: datetime) -> bool:
        """Reject stale/expired worker refreshes and terminal authorization."""
        with self.engine.begin() as connection:
            return bool(
                connection.scalar(
                    text("SELECT taskify_heartbeat_turn(:id,:worker,:version,:now)"),
                    {
                        "id": turn.id,
                        "worker": turn.lease_owner,
                        "version": turn.lease_version,
                        "now": now,
                    },
                )
            )

    def encode_cursor(self, actor: Principal, before: int) -> str:
        """Bind continuation to exact company/account and history query version."""
        payload = json.dumps(
            [str(actor.company_id), str(actor.account_id), before], separators=(",", ":")
        ).encode()
        return (
            base64.urlsafe_b64encode(payload + hmac.digest(self.cursor_key, payload, "sha256"))
            .decode()
            .rstrip("=")
        )

    def decode_cursor(self, actor: Principal, cursor: str) -> int:
        """Validate signed ownership before allowing any history boundary selection."""
        try:
            if not 1 <= len(cursor) <= 512:
                raise ValueError()
            raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
            payload, signature = raw[:-32], raw[-32:]
            if not hmac.compare_digest(signature, hmac.digest(self.cursor_key, payload, "sha256")):
                raise ValueError()
            company, account, before = json.loads(payload)
            if (
                company != str(actor.company_id)
                or account != str(actor.account_id)
                or type(before) is not int
                or before < 1
            ):
                raise ValueError()
            return before
        except (ValueError, TypeError, UnicodeError):
            raise ApplicationError(
                "validation_failed", "Reload the conversation with a valid history cursor.", 422
            ) from None
