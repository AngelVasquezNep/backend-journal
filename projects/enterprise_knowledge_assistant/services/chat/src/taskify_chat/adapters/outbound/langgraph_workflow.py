"""Acyclic transient LangGraph orchestrates bounded roles; application code alone authorizes and saves results."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from typing import TypedDict, TypeVar

import tiktoken
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from taskify_chat.adapters.outbound.langchain_openai import TransientProviderError
from taskify_chat.adapters.outbound.model_profiles import compatible
from taskify_chat.application.ports.answerer import (
    AnswerDraft,
    Answerer,
    HistoryMessage,
    ScopeDecision,
)
from taskify_chat.application.ports.knowledge import Evidence, KnowledgeGateway
from taskify_chat.application.ports.workflow import AcceptedConfiguration, ActorContext, Candidate
from taskify_chat.domain.answer_policy import supported_membership
from taskify_chat.domain.errors import ApplicationError

T = TypeVar("T")


def bounded_history(history: tuple[HistoryMessage, ...]) -> tuple[tuple[HistoryMessage, ...], bool]:
    """Select newest complete prior messages in order at <=6000 cl100k tokens, excluding current question."""
    encoding = tiktoken.get_encoding("cl100k_base")
    selected = []
    total = 0
    for message in reversed(history):
        count = len(encoding.encode(message.content, disallowed_special=()))
        if total + count > 6000:
            break
        total += count
        selected.append(message)
    return tuple(reversed(selected)), len(selected) != len(history)


class RetryBudget:
    """At most one transient provider retry across all roles, sharing the outer attempt deadline."""

    def __init__(self) -> None:
        """Create a fresh one-use retry budget on every whole-turn attempt."""
        self.remaining = 1

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Retry only explicitly transient provider errors; no graph back edges or multiplied SDK retries."""
        try:
            return await operation()
        except TransientProviderError:
            if self.remaining == 0:
                raise
            self.remaining -= 1
            await asyncio.sleep(0.1)
            return await operation()


@dataclass
class Audit:
    """Only this attempt's successful retrieval version survives a later safe failure candidate."""

    retrieval_version: str | None = None


@dataclass(frozen=True)
class Context:
    """Immutable per-attempt actor/answerer references remain outside model-writable graph state."""

    actor: ActorContext
    answerer: Answerer
    retry: RetryBudget
    audit: Audit


class State(TypedDict, total=False):
    """Ephemeral graph data contains no credentials, source authorization receipt or persistence handles."""

    question: str
    history: tuple[HistoryMessage, ...]
    omitted: bool
    scope: ScopeDecision
    evidence: tuple[Evidence, ...]
    draft: AnswerDraft


class LangGraphWorkflow:
    """Scope → retrieve → generate → verify has no back edges/tools/checkpoints/store/cache or writes."""

    def __init__(
        self, knowledge: KnowledgeGateway, answerers: Callable[[AcceptedConfiguration], Answerer]
    ) -> None:
        """Compile a stateless bounded graph; every invocation gets fresh immutable context and retry budget."""
        self.knowledge = knowledge
        self.answerers = answerers
        builder = StateGraph(State, context_schema=Context)
        builder.add_node("scope", self.scope)
        builder.add_node("retrieve", self.retrieve)
        builder.add_node("generate", self.generate)
        builder.add_node("verify", self.verify)
        builder.add_edge(START, "scope")
        builder.add_conditional_edges(
            "scope",
            lambda state: (
                "retrieve"
                if state["scope"].intent in ("company_information", "mixed")
                and state["scope"].query
                else END
            ),
            ["retrieve", END],
        )
        builder.add_conditional_edges(
            "retrieve",
            lambda state: "generate" if state.get("evidence") else END,
            ["generate", END],
        )
        builder.add_conditional_edges(
            "generate",
            lambda state: "verify" if state["draft"].outcome == "answer" else END,
            ["verify", END],
        )
        builder.add_edge("verify", END)
        self.graph = builder.compile(checkpointer=None, store=None, cache=None)

    async def scope(self, state: State, runtime: Runtime[Context]) -> dict[str, object]:
        """Resolve scope using only the retained topic window; never answer facts from prior messages."""
        context = runtime.context
        decision = await context.retry.call(
            lambda: context.answerer.scope(state["question"], state["history"])
        )
        if decision.intent in ("unrelated", "action_request"):
            draft = AnswerDraft(
                "refusal",
                message="I can answer, explain or summarize information in your company documents. I cannot create code, prompts or other drafts, or perform actions.",
            )
        elif decision.intent == "ambiguous" or not decision.query:
            draft = AnswerDraft(
                "clarification",
                message="What would you like to know? Please specify the subject or document you mean.",
            )
        elif not 1 <= len(decision.query.strip()) <= 4000:
            raise ApplicationError(
                "verification_failed", "The standalone company question was invalid.", 503
            )
        else:
            draft = AnswerDraft(
                "insufficient_information",
                message="I couldn’t find enough information in the available company documents to answer that.",
                refusal_text="I cannot create code, prompts or other drafts, or perform actions."
                if decision.intent == "mixed"
                else None,
            )
        return {"scope": decision, "draft": draft}

    async def retrieve(self, state: State, runtime: Runtime[Context]) -> dict[str, object]:
        """Search current authorized evidence afresh; record version even for a successful empty result."""
        context = runtime.context
        query = state["scope"].query
        assert query is not None
        result = await asyncio.to_thread(
            self.knowledge.search, context.actor.login_session_id, query, context.actor.request_id
        )
        context.audit.retrieval_version = result.retrieval_config_version
        if not result.pipeline_version or not result.retrieval_config_version:
            raise ApplicationError(
                "dependency_unavailable", "Current retrieval configuration is unavailable.", 503
            )
        unique = {entry.chunk_id: entry for entry in result.candidates}
        return {"evidence": tuple(unique.values())[:8]}

    async def generate(self, state: State, runtime: Runtime[Context]) -> dict[str, object]:
        """Treat evidence as untrusted text and reject unknown evidence, free-form facts and invalid outcomes."""
        context = runtime.context
        query = state["scope"].query
        assert query is not None
        draft = await context.retry.call(
            lambda: context.answerer.generate(query, state["evidence"])
        )
        if draft.outcome == "answer":
            if not supported_membership(
                draft.claims, frozenset(entry.chunk_id for entry in state["evidence"])
            ) or any(claim.conflicting and len(claim.evidence_ids) < 2 for claim in draft.claims):
                raise ApplicationError(
                    "verification_failed", "The proposed answer could not be verified.", 503
                )
            # Model message/refusal fields cannot introduce uncited additional facts.
            draft = replace(
                draft,
                message=None,
                refusal_text="I cannot create code, prompts or other drafts, or perform actions."
                if state["scope"].intent == "mixed"
                else None,
            )
        elif draft.outcome in ("insufficient_information", "clarification") and not draft.claims:
            draft = AnswerDraft(
                draft.outcome,
                message="I couldn’t find enough information in the available company documents to answer that."
                if draft.outcome == "insufficient_information"
                else "Please specify the subject or document you mean.",
                refusal_text="I cannot create code, prompts or other drafts, or perform actions."
                if state["scope"].intent == "mixed"
                else None,
            )
        else:
            raise ApplicationError(
                "verification_failed", "The proposed answer could not be verified.", 503
            )
        return {"draft": draft}

    async def verify(self, state: State, runtime: Runtime[Context]) -> dict[str, object]:
        """One grounding role can only accept/reject the candidate; it cannot regenerate or grant release."""
        context = runtime.context
        if not await context.retry.call(
            lambda: context.answerer.verify(
                state["scope"].query or state["question"], state["draft"], state["evidence"]
            )
        ):
            raise ApplicationError(
                "verification_failed", "The answer could not be grounded in company evidence.", 503
            )
        return {}

    def run(
        self,
        question: str,
        history: tuple[HistoryMessage, ...],
        actor: ActorContext,
        configuration: AcceptedConfiguration,
        deadline: float,
    ) -> Candidate:
        """Run at most 12 graph steps within the remaining shared 60-second whole-attempt deadline."""
        compatible(configuration)
        selected, omitted = bounded_history(history)
        audit = Audit()
        context = Context(actor, self.answerers(configuration), RetryBudget(), audit)

        async def attempt() -> Candidate:
            """Cancel awaited provider nodes on deadline and discard all uncommitted graph state."""
            try:
                async with asyncio.timeout(max(0.0, deadline - time.monotonic())):
                    output = await self.graph.ainvoke(
                        State(question=question, history=selected, omitted=omitted),
                        {
                            "recursion_limit": 12,
                            "run_name": "taskify.chat.answer",
                            "tags": ["taskify", "chat"],
                        },
                        context=context,
                    )
                return Candidate(
                    output["draft"], audit.retrieval_version, output.get("evidence", ())
                )
            except TimeoutError:
                return Candidate(
                    AnswerDraft("failure", message="Answer processing timed out. Please retry."),
                    audit.retrieval_version,
                    error_code="attempt_timeout",
                )
            except ApplicationError as error:
                code = (
                    error.code
                    if error.code
                    in ("authentication_required", "verification_failed", "dependency_unavailable")
                    else "dependency_unavailable"
                )

                return Candidate(
                    AnswerDraft(
                        "failure", message="The answer could not be completed. Please retry."
                    ),
                    audit.retrieval_version,
                    error_code=code,
                )
            except Exception:
                return Candidate(
                    AnswerDraft(
                        "failure", message="The answer could not be completed. Please retry."
                    ),
                    audit.retrieval_version,
                    error_code="dependency_unavailable",
                )

            finally:
                with suppress(Exception):
                    async with asyncio.timeout(1):
                        await context.answerer.close()

        return asyncio.run(attempt())
