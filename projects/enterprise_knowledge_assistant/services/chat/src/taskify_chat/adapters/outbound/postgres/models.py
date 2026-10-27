"""Service-owned SQLAlchemy tables mirror explicit migrations; core values never import ORM types."""

from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, Integer, MetaData, Table, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()


def columns(names: str, kind: Any) -> list[Column[Any]]:
    """Build simple owned column declarations without generating migration constraints implicitly."""
    return [Column(name, kind) for name in names.split()]


conversations = Table(
    "conversations",
    metadata,
    *columns("id company_id account_id", Uuid),
    Column("last_sequence", BigInteger),
    *columns("created_at updated_at", DateTime(timezone=True)),
)
chat_turns = Table(
    "chat_turns",
    metadata,
    *columns(
        "id company_id account_id conversation_id client_message_id user_message_id assistant_message_id accepted_login_session_id lease_owner",
        Uuid,
    ),
    *columns(
        "state error_code ai_mode model graph_version prompt_version model_config_version retrieval_config_version",
        Text,
    ),
    Column("attempt_count", Integer),
    Column("lease_version", BigInteger),
    *columns("lease_until created_at completed_at", DateTime(timezone=True)),
)
chat_messages = Table(
    "chat_messages",
    metadata,
    *columns("id company_id account_id conversation_id turn_id", Uuid),
    Column("sequence", BigInteger),
    *columns("sender content outcome refusal_text", Text),
    Column("created_at", DateTime(timezone=True)),
)
citations = Table(
    "citations",
    metadata,
    *columns("id company_id account_id assistant_message_id item_id revision_id chunk_id", Uuid),
    Column("locator", JSONB),
    Column("title_at_answer", Text),
    Column("validated_at", DateTime(timezone=True)),
)
