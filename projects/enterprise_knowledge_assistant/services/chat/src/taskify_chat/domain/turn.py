"""Durable turn snapshots pin answer settings while retrieval metadata belongs only to a terminal attempt."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from taskify_chat.domain.conversation import ownership, utc


@dataclass(frozen=True, kw_only=True)
class ChatTurn:
    """Unique conversation/client ID, one active turn, at most three claims and lease-fenced completion."""

    id: UUID
    company_id: UUID
    account_id: UUID
    conversation_id: UUID
    client_message_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID | None = None
    accepted_login_session_id: UUID
    state: Literal["queued", "running", "completed", "failed"]
    attempt_count: int = 0
    lease_owner: UUID | None = None
    lease_until: datetime | None = None
    lease_version: int = 0
    created_at: datetime
    completed_at: datetime | None = None
    error_code: str | None = None
    ai_mode: str
    model: str
    graph_version: str
    prompt_version: str
    model_config_version: str
    retrieval_config_version: str | None = None

    def __post_init__(self) -> None:
        """Validate identity, bounded recovery and immutable configuration payload shape."""
        ownership(
            self.id,
            self.company_id,
            self.account_id,
            self.conversation_id,
            self.client_message_id,
            self.user_message_id,
            self.accepted_login_session_id,
        )
        for value in (self.assistant_message_id, self.lease_owner):
            if value is not None:
                ownership(value)
        utc(self.lease_until, self.created_at, self.completed_at)
        if (
            self.state not in ("queued", "running", "completed", "failed")
            or type(self.attempt_count) is not int
            or not 0 <= self.attempt_count <= 3
            or type(self.lease_version) is not int
            or self.lease_version < 0
        ):
            raise ValueError("Invalid turn state.")
        if self.ai_mode not in ("stub", "openai") or any(
            not isinstance(value, str)
            or not value
            or len(value) > 200
            or any(char.isspace() or ord(char) < 32 for char in value)
            for value in (
                self.model,
                self.graph_version,
                self.prompt_version,
                self.model_config_version,
            )
        ):
            raise ValueError("Invalid accepted answer configuration.")
        if self.state == "running":
            if self.lease_owner is None or self.lease_until is None or self.attempt_count < 1:
                raise ValueError("Running turns require a live claim payload.")
        elif self.lease_owner is not None or self.lease_until is not None:
            raise ValueError("Only running turns retain lease ownership.")
        if self.state in ("queued", "running") and (
            self.assistant_message_id is not None or self.completed_at is not None
        ):
            raise ValueError("Pending turns cannot contain terminal message fields.")
        if self.state in ("queued", "running") and self.retrieval_config_version is not None:
            raise ValueError("Pending turns have no retrieval configuration receipt.")
        if (self.state in ("completed", "failed")) != (
            self.completed_at is not None and self.assistant_message_id is not None
        ):
            raise ValueError("Terminal turns require exactly one saved assistant result.")
