"""Async LangChain structured roles use the exact accepted model, Responses/store=false and no tools/retries."""

import json
import re
from dataclasses import asdict
from typing import Literal
from uuid import UUID

from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    APITimeoutError,
    DefaultAsyncHttpxClient,
    DefaultHttpxClient,
    InternalServerError,
    RateLimitError,
)
from pydantic import BaseModel, ConfigDict, SecretStr

from taskify_chat.adapters.outbound.model_profiles import compatible
from taskify_chat.adapters.outbound.prompts import GENERATE, SCOPE, VERIFY
from taskify_chat.application.ports.answerer import (
    AnswerDraft,
    Claim,
    HistoryMessage,
    ScopeDecision,
)
from taskify_chat.application.ports.knowledge import Evidence
from taskify_chat.application.ports.workflow import AcceptedConfiguration
from taskify_chat.domain.errors import DependencyUnavailable


class TransientProviderError(DependencyUnavailable):
    """Only transient provider failures consume the one shared per-attempt retry budget."""


class ScopeSchema(BaseModel):
    """Strict operation classification; company_information is a candidate for document search."""

    model_config = ConfigDict(extra="forbid", strict=True)
    intent: Literal["company_information", "unrelated", "action_request", "mixed", "ambiguous"]
    query: str | None
    refusal_text: str | None


class ClaimSchema(BaseModel):
    """Model IDs are untrusted strings until validated against supplied server evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)
    text: str
    evidence_ids: list[str]
    conflicting: bool


class AnswerSchema(BaseModel):
    """Generation can only propose an answer, insufficiency or company-topic clarification."""

    model_config = ConfigDict(extra="forbid", strict=True)
    outcome: Literal["answer", "insufficient_information", "clarification"]
    claims: list[ClaimSchema]
    message: str | None


class VerifySchema(BaseModel):
    """One final grounding boolean cannot authorize release or request regeneration."""

    model_config = ConfigDict(extra="forbid", strict=True)
    supported: bool


class OpenAIAnswerer:
    """Three roles share the same explicit accepted model/profile with no fallback or external state."""

    def __init__(self, configuration: AcceptedConfiguration, key: str) -> None:
        """Construct locally without a paid availability probe; omit temperature/reasoning/token assumptions."""
        compatible(configuration)
        if configuration.ai_mode != "openai" or not key:
            raise DependencyUnavailable()
        self.model = ChatOpenAI(
            model=configuration.model,
            api_key=SecretStr(key),
            base_url="https://api.openai.com/v1",
            use_responses_api=True,
            max_retries=0,
            timeout=60.0,
            # LangChain caches default pools; each attempt closes only its own clients.
            http_client=DefaultHttpxClient(timeout=60.0),
            http_async_client=DefaultAsyncHttpxClient(timeout=60.0),
            cache=False,
            store=False,
        )
        self.scope_role = self.model.with_structured_output(
            ScopeSchema, method="json_schema", strict=True
        )
        self.generate_role = self.model.with_structured_output(
            AnswerSchema, method="json_schema", strict=True
        )
        self.verify_role = self.model.with_structured_output(
            VerifySchema, method="json_schema", strict=True
        )

    async def scope(self, question: str, history: tuple[HistoryMessage, ...]) -> ScopeDecision:
        """Resolve company scope from a quoted bounded history, never promote prior statements to facts."""
        try:
            output = await self.scope_role.ainvoke(
                [
                    ("system", SCOPE),
                    (
                        "human",
                        json.dumps(
                            {
                                "question": question,
                                "history": [asdict(message) for message in history],
                            },
                            ensure_ascii=False,
                        ),
                    ),
                ],
                config={"run_name": "taskify.chat.scope"},
            )
            if (
                not isinstance(output, ScopeSchema)
                or (output.query is not None and not 1 <= len(output.query.strip()) <= 4000)
                or (output.refusal_text is not None and len(output.refusal_text) > 1000)
            ):
                raise ValueError()
            return ScopeDecision(output.intent, output.query, output.refusal_text)
        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError):
            raise TransientProviderError() from None
        except Exception:
            raise DependencyUnavailable() from None

    async def generate(self, query: str, evidence: tuple[Evidence, ...]) -> AnswerDraft:
        """Return structured claims only; provider safety refusal/incomplete/schema errors fail explicitly."""
        try:
            output = await self.generate_role.ainvoke(
                [
                    ("system", GENERATE),
                    (
                        "human",
                        json.dumps(
                            {"question": query, "evidence": [asdict(entry) for entry in evidence]},
                            default=str,
                            ensure_ascii=False,
                        ),
                    ),
                ],
                config={"run_name": "taskify.chat.generate"},
            )
            if not isinstance(output, AnswerSchema) or len(output.claims) > 12:
                raise ValueError()
            claims = tuple(
                Claim(value.text, tuple(UUID(key) for key in value.evidence_ids), value.conflicting)
                for value in output.claims
            )
            return AnswerDraft(output.outcome, claims, output.message)
        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError):
            raise TransientProviderError() from None
        except Exception:
            raise DependencyUnavailable() from None

    async def verify(self, query: str, draft: AnswerDraft, evidence: tuple[Evidence, ...]) -> bool:
        """Check grounding using the accepted model and supplied evidence, with no regeneration/tools."""
        try:
            output = await self.verify_role.ainvoke(
                [
                    ("system", VERIFY),
                    (
                        "human",
                        json.dumps(
                            {
                                "question": query,
                                "draft": asdict(draft),
                                "evidence": [asdict(entry) for entry in evidence],
                            },
                            default=str,
                            ensure_ascii=False,
                        ),
                    ),
                ],
                config={"run_name": "taskify.chat.verify"},
            )
            if not isinstance(output, VerifySchema):
                raise ValueError()
            return output.supported
        except (APIConnectionError, APITimeoutError, InternalServerError, RateLimitError):
            raise TransientProviderError() from None
        except Exception:
            raise DependencyUnavailable() from None

    async def close(self) -> None:
        """Close both owned SDK pools before the per-attempt event loop exits, retaining no provider state."""
        if self.model.root_async_client is not None:
            await self.model.root_async_client.close()
        if self.model.root_client is not None:
            self.model.root_client.close()


class StubAnswerer:
    """Conservative deterministic fixture role; provides no live quality/refusal evaluation evidence."""

    async def scope(self, question: str, history: tuple[HistoryMessage, ...]) -> ScopeDecision:
        """Route fixture information topics to search; never infer document coverage from keywords."""
        lowered = question.casefold()
        prohibited = re.compile(
            r"\b(?:send|delete|create|write|draft|generate|execute|email)\b"
            r"|ignore (?:all|instructions)|reveal (?:the )?(?:system|protected)"
        )
        # This intentionally small fixture parser is not a production safety classifier.
        parts = re.split(r"\s+and\s+", question, flags=re.IGNORECASE)
        information = [part for part in parts if not prohibited.search(part.casefold())]
        action = bool(prohibited.search(lowered))
        if action and not information:
            return ScopeDecision("action_request")
        query = " and ".join(information) if action else question
        reference = bool(
            re.search(r"\b(?:that|those|it)\b|what about|exceptions", query.casefold())
        )
        if reference and not re.search(r"policy\s+\d+", query.casefold()):
            topic = next(
                (message.content for message in reversed(history) if message.sender == "user"),
                None,
            )
            if topic is None:
                return ScopeDecision("ambiguous")
            query = topic + " " + query
        return ScopeDecision(
            "mixed" if action else "company_information",
            query if len(query) <= 4000 else None,
            "I cannot create code, prompts or other drafts, or perform actions."
            if action
            else None,
        )

    async def generate(self, query: str, evidence: tuple[Evidence, ...]) -> AnswerDraft:
        """Quote only fixture source sentences with matching topic terms; never execute document instructions."""
        terms = set(re.findall(r"\w+", query.casefold())) - {
            "what",
            "is",
            "the",
            "company",
            "policy",
            "a",
            "of",
            "and",
            "to",
        }
        claims = []
        for entry in evidence:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", entry.text):
                lower = sentence.casefold()
                if terms & set(re.findall(r"\w+", lower)) and not any(
                    word in lower
                    for word in (
                        "ignore all",
                        "ignore instructions",
                        "reveal the system prompt",
                        "send ",
                        "delete ",
                        "http:",
                        "https:",
                    )
                ):
                    claims.append(Claim(sentence.strip(), (entry.chunk_id,)))
                    break
            if len(claims) >= 3:
                break
        return (
            AnswerDraft("answer", tuple(claims))
            if claims
            else AnswerDraft(
                "insufficient_information",
                message="The ready company information does not answer this question.",
            )
        )

    async def verify(self, query: str, draft: AnswerDraft, evidence: tuple[Evidence, ...]) -> bool:
        """Require literal fixture grounding; production verification uses the accepted OpenAI role."""
        supplied = {entry.chunk_id: entry.text for entry in evidence}
        return all(
            all(claim.text in supplied.get(key, "") for key in claim.evidence_ids)
            for claim in draft.claims
        )

    async def close(self) -> None:
        """Finish a deterministic attempt without network resources or retained private state."""
