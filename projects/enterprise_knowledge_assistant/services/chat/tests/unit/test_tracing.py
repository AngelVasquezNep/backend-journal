"""Tracing configuration rejects silent disablement and requires redacted exports."""

import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.tracers.langchain import wait_for_all_tracers
from langsmith import Client, tracing_context

from taskify_chat.adapters.outbound.langchain_openai import (
    AnswerSchema,
    ClaimSchema,
    OpenAIAnswerer,
    ScopeSchema,
    VerifySchema,
)
from taskify_chat.adapters.outbound.langgraph_workflow import LangGraphWorkflow
from taskify_chat.adapters.outbound.settings import validate_tracing
from taskify_chat.application.ports.workflow import AcceptedConfiguration, ActorContext


def enabled_environment() -> dict[str, str]:
    """Supply a complete local tracing fixture without any real provider credentials."""
    return {
        "LANGSMITH_TRACING": "true",
        "LANGCHAIN_TRACING_V2": "true",
        "LANGSMITH_API_KEY": "fixture-langsmith-secret",
        "LANGSMITH_PROJECT": "taskify-test",
        "LANGSMITH_ENDPOINT": "https://api.smith.langchain.com",
        "LANGSMITH_HIDE_INPUTS": "true",
        "LANGSMITH_HIDE_OUTPUTS": "true",
    }


def test_tracing_is_optional_and_valid_configuration_is_accepted() -> None:
    """Disabled tracing needs no credentials; enabled tracing accepts regional endpoints."""
    validate_tracing({})
    environment = enabled_environment()
    environment["LANGSMITH_ENDPOINT"] = "https://eu.api.smith.langchain.com"
    validate_tracing(environment)


@pytest.mark.parametrize(
    "key,value",
    [
        ("LANGSMITH_TRACING", "True"),
        ("LANGCHAIN_TRACING_V2", "false"),
        ("LANGSMITH_TRACING_V2", "false"),
        ("LANGSMITH_API_KEY", ""),
        ("LANGSMITH_PROJECT", " "),
        ("LANGSMITH_ENDPOINT", "http://api.smith.langchain.com"),
        ("LANGSMITH_ENDPOINT", "https://user:secret@example.test"),
        ("LANGSMITH_HIDE_INPUTS", "false"),
        ("LANGSMITH_HIDE_OUTPUTS", ""),
    ],
)
def test_invalid_tracing_fails_before_accepting_work(key: str, value: str) -> None:
    """Reject conflicting flags, missing credentials, unsafe destinations and visible payloads."""
    environment = enabled_environment()
    environment[key] = value
    with pytest.raises(ValueError) as failure:
        validate_tracing(environment)
    assert "fixture-langsmith-secret" not in str(failure.value)


def test_legacy_flag_cannot_enable_tracing_behind_the_canonical_switch() -> None:
    """A disabled canonical flag cannot coexist with an enabled legacy SDK flag."""
    with pytest.raises(ValueError, match="must match"):
        validate_tracing({"LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "true"})


@pytest.mark.parametrize("enabled", [True, False])
def test_graph_and_model_roles_share_one_redacted_trace(
    monkeypatch, knowledge_double, enabled
) -> None:
    """Exercise actual callback inheritance and SDK export without OpenAI or LangSmith requests."""
    exported = []

    def capture(self, method, path, *, request_kwargs=None, **kwargs):
        """Capture serialized trace bodies after the configured privacy processing."""
        if request_kwargs and request_kwargs.get("data"):
            exported.append(json.loads(request_kwargs["data"]))

    monkeypatch.setattr(Client, "request_with_retries", capture)
    client = Client(
        api_url="https://traces.example.test",
        api_key="fixture-tracing-key",
        auto_batch_tracing=False,
        hide_inputs=True,
        hide_outputs=True,
    )
    answerer = object.__new__(OpenAIAnswerer)
    answerer.model = SimpleNamespace(root_async_client=None, root_client=None)
    answerer.scope_role = RunnableLambda(
        lambda _: ScopeSchema(
            intent="company_information", query="private-company-question", refusal_text=None
        )
    )
    answerer.generate_role = RunnableLambda(
        lambda _: AnswerSchema(
            outcome="answer",
            claims=[
                ClaimSchema(
                    text="private-company-answer",
                    evidence_ids=[str(knowledge_double.evidence.chunk_id)],
                    conflicting=False,
                )
            ],
            message=None,
        )
    )
    answerer.verify_role = RunnableLambda(lambda _: VerifySchema(supported=True))
    workflow = LangGraphWorkflow(knowledge_double, lambda _: answerer)
    with tracing_context(enabled=enabled, client=client, project_name="taskify-test"):
        result = workflow.run(
            "private-company-question",
            (),
            ActorContext(uuid4(), uuid4(), uuid4(), uuid4()),
            AcceptedConfiguration("stub", "fixture-local", "graph-v1", "prompt-v1", "responses-v1"),
            time.monotonic() + 20,
        )
    wait_for_all_tracers()
    client.flush()
    assert result.draft.outcome == "answer"
    if enabled:
        runs = {run["name"]: run for run in exported if "name" in run}
        root = runs["taskify.chat.answer"]
        for role in ("scope", "generate", "verify"):
            run = runs["taskify.chat." + role]
            assert run["trace_id"] == root["trace_id"] and run.get("parent_run_id")
        assert all(not run.get("inputs") and not run.get("outputs") for run in exported)
        assert "private-company-question" not in json.dumps(exported)
        assert "private-company-answer" not in json.dumps(exported)
    else:
        assert exported == []
