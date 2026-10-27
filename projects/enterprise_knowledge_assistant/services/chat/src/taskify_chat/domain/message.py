"""Saved ordered messages carry one user question or one assistant terminal outcome."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from taskify_chat.domain.conversation import ownership, utc
from taskify_chat.domain.values import MessageText

Outcome = Literal["answer", "refusal", "insufficient_information", "clarification", "failure"]


@dataclass(frozen=True, kw_only=True)
class ChatMessage:
    """Unique conversation sequence and one assistant terminal result per turn; immutable ownership."""

    id: UUID
    company_id: UUID
    account_id: UUID
    conversation_id: UUID
    turn_id: UUID
    sequence: int
    sender: Literal["user", "assistant"]
    content: str
    outcome: Outcome | None = None
    refusal_text: str | None = None
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate sender/outcome and user bounds; all assistant text is application-authorized."""
        ownership(self.id, self.company_id, self.account_id, self.conversation_id, self.turn_id)
        utc(self.created_at)
        if (
            type(self.sequence) is not int
            or self.sequence < 1
            or not isinstance(self.content, str)
            or not self.content
        ):
            raise ValueError("Invalid message.")
        if self.sender == "user":
            if (
                MessageText(self.content).value != self.content
                or self.outcome is not None
                or self.refusal_text is not None
            ):
                raise ValueError("Invalid user message.")
        elif (
            self.sender != "assistant"
            or self.outcome
            not in ("answer", "refusal", "insufficient_information", "clarification", "failure")
            or len(self.content) > 16000
        ):
            raise ValueError("Invalid assistant terminal outcome.")
