"""Bounded transient turn workflow; authorization and terminal persistence remain outside it."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from taskify_chat.application.ports.answerer import AnswerDraft, HistoryMessage
from taskify_chat.application.ports.knowledge import Evidence


@dataclass(frozen=True)
class ActorContext:
    """Immutable stored ownership and accepting session; model updates cannot alter authority."""

    company_id: UUID
    account_id: UUID
    login_session_id: UUID
    request_id: UUID


@dataclass(frozen=True)
class AcceptedConfiguration:
    """Accepted answer settings remain fixed across retries, rollouts and recovered attempts."""

    ai_mode: str
    model: str
    graph_version: str
    prompt_version: str
    model_config_version: str


@dataclass(frozen=True)
class Candidate:
    """Uncommitted outcome and terminal-attempt retrieval audit data; no release receipt."""

    draft: AnswerDraft
    retrieval_config_version: str | None = None
    evidence: tuple[Evidence, ...] = ()
    error_code: str | None = None


class TurnWorkflow(Protocol):
    """Run fresh state once; no checkpointer, tools, persistent graph memory or database writes."""

    def run(
        self,
        question: str,
        history: tuple[HistoryMessage, ...],
        actor: ActorContext,
        configuration: AcceptedConfiguration,
        deadline: float,
    ) -> Candidate:
        """Return a candidate within 12 steps/60 seconds, or an explicit safe operational failure."""
        ...
