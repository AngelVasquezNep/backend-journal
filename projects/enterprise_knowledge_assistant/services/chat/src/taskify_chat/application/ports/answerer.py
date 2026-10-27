"""Application-owned model roles exchange plain immutable values, never provider types."""

from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID

from taskify_chat.application.ports.knowledge import Evidence


@dataclass(frozen=True)
class HistoryMessage:
    """One prior authorized complete message for topic resolution, never factual evidence."""

    sender: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class ScopeDecision:
    """Classified company-information scope and optional bounded standalone question."""

    intent: Literal["company_information", "unrelated", "action_request", "mixed", "ambiguous"]
    query: str | None = None
    refusal_text: str | None = None


@dataclass(frozen=True)
class Claim:
    """A proposed factual statement must cite supplied authorized chunk identifiers."""

    text: str
    evidence_ids: tuple[UUID, ...]
    conflicting: bool = False


@dataclass(frozen=True)
class AnswerDraft:
    """Uncommitted structured output; a model cannot grant release permission."""

    outcome: Literal["answer", "insufficient_information", "clarification", "refusal", "failure"]
    claims: tuple[Claim, ...] = ()
    message: str | None = None
    refusal_text: str | None = None


class Answerer(Protocol):
    """Three bounded model roles share the accepted configuration and one attempt retry budget."""

    async def scope(self, question: str, history: tuple[HistoryMessage, ...]) -> ScopeDecision:
        """Resolve the current question's company scope and in-window references."""
        ...

    async def generate(self, query: str, evidence: tuple[Evidence, ...]) -> AnswerDraft:
        """Produce only claims entailed by supplied evidence; provider failures remain explicit."""
        ...

    async def verify(self, query: str, draft: AnswerDraft, evidence: tuple[Evidence, ...]) -> bool:
        """Return whether each claim is grounded; do not fabricate sources or regenerate."""
        ...

    async def close(self) -> None:
        """Release per-attempt provider resources after success, failure or deadline cancellation."""
        ...
