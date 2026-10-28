"""Embedding failures retain safe operational diagnostics without exposing provider payloads."""

import json
import logging

import httpx
import pytest
from langsmith import Client, tracing_context
from openai import AuthenticationError

from taskify_knowledge.adapters.outbound.embeddings import OpenAIEmbedder
from taskify_knowledge.domain.errors import DependencyUnavailable


@pytest.mark.parametrize("http_failure", [True, False])
def test_provider_failure_logs_only_type_and_status(monkeypatch, caplog, http_failure) -> None:
    """Distinguish rejected keys from transport failures without logging keys or uploaded text."""
    private = "private-provider-key-and-document"
    error = (
        AuthenticationError(
            private,
            response=httpx.Response(401, request=httpx.Request("POST", "https://example.test")),
            body={"message": private},
        )
        if http_failure
        else RuntimeError(private)
    )

    class Client:
        """Fail locally without contacting a provider or loading tokenizer data."""

        def embed_documents(self, texts):
            """Simulate a provider or transport exception containing private diagnostic data."""
            raise error

    embedder = object.__new__(OpenAIEmbedder)
    monkeypatch.setattr(embedder, "client", Client(), raising=False)
    with caplog.at_level(logging.WARNING, logger="taskify.ingestion"):
        with pytest.raises(DependencyUnavailable) as failure:
            embedder.send([private])

    assert failure.value.status == 503
    assert private not in str(failure.value)
    assert caplog.messages == [
        "embedding_unavailable error_type=AuthenticationError status=401"
        if http_failure
        else "embedding_unavailable error_type=RuntimeError status=None"
    ]


@pytest.mark.parametrize("enabled", [True, False])
def test_embedding_traces_are_optional_and_hide_payloads(monkeypatch, enabled) -> None:
    """Capture actual SDK exports without network traffic; disabled tracing sends nothing."""
    exported = []

    def capture(self, method, path, *, request_kwargs=None, **kwargs):
        """Observe serialized trace bodies after LangSmith applies input/output hiding."""
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

    class Embeddings:
        """Return a valid synthetic vector without sending company text to any provider."""

        def embed_documents(self, texts):
            """Supply the same dimensions as the production embedding contract."""
            return [[1.0] * 1536]

    embedder = object.__new__(OpenAIEmbedder)
    monkeypatch.setattr(embedder, "client", Embeddings(), raising=False)
    with tracing_context(enabled=enabled, client=client, project_name="taskify-test"):
        assert len(embedder.send(["private-document-text"])[0]) == 1536
    client.flush()
    if enabled:
        assert any(
            run.get("name") == "taskify.knowledge.embed" and run.get("run_type") == "embedding"
            for run in exported
        )
        assert all(not run.get("inputs") and not run.get("outputs") for run in exported)
        assert "private-document-text" not in json.dumps(exported)
    else:
        assert exported == []
