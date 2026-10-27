"""OPEN_AI_MODEL configuration is explicit, bounded, model-independent and nonbillable."""

import pytest

from taskify_chat.adapters.outbound.settings import Settings


def environment() -> dict[str, str]:
    """Create local configuration containing no real credentials or provider model default."""
    return {
        "DATABASE_URL": "postgresql+psycopg://chat_runtime:test@localhost/chat_test",
        "PUBLIC_ORIGIN": "http://localhost:8080",
        "IDENTITY_URL": "http://identity:8000",
        "KNOWLEDGE_URL": "http://knowledge:8000",
        "SERVICE_CREDENTIAL": "api-test-credential",
        "WORKER_CREDENTIAL": "worker-test-credential",
        "OPENAI_API_KEY": "fixture-not-a-real-key",
        "AI_MODE": "openai",
    }


@pytest.mark.parametrize(
    "model", ["", " ", "has space", "has\nnewline", "has\x00control", "x" * 201]
)
def test_invalid_models_fail_local_configuration(model: str) -> None:
    """Reject empty, whitespace/control-bearing and oversized IDs without calling a provider."""
    env = environment()
    env["OPEN_AI_MODEL"] = model
    with pytest.raises(ValueError):
        Settings.from_env(env)


def test_model_is_required_and_legacy_alias_is_not_used() -> None:
    """Do not infer a chat model from a legacy alias or the embedding configuration."""
    env = environment()
    env["OPENAI_MODEL"] = "a-legacy-alias"
    with pytest.raises(ValueError):
        Settings.from_env(env)
    env["OPEN_AI_MODEL"] = "x" * 200
    assert Settings.from_env(env).model == "x" * 200


def test_stub_is_local_only_and_preserves_embedding_space() -> None:
    """Allow deterministic fixtures locally; production rejects stub mode and requires HTTPS."""
    env = environment()
    env["AI_MODE"] = "stub"
    local = Settings.from_env(env)
    assert local.model == "stub-fixture-v1"
    assert local.embedding_dimensions == 1536
    env["TASKIFY_ENV"] = "production"
    env["PUBLIC_ORIGIN"] = "https://taskify.example"
    with pytest.raises(ValueError):
        Settings.from_env(env)


def test_all_structured_roles_use_exact_accepted_model_and_no_tools(monkeypatch) -> None:
    """Construction is nonbillable and propagates the accepted model to Responses with SDK retries disabled."""
    from taskify_chat.adapters.outbound.langchain_openai import OpenAIAnswerer
    from taskify_chat.application.ports.workflow import AcceptedConfiguration

    captured = {}
    schemas = []

    class Model:
        """Observe local constructor/profile configuration without sending a provider request."""

        def __init__(self, **kwargs):
            """Capture parameter names/model flags, excluding the fixture key from assertions/output."""
            captured.update({key: value for key, value in kwargs.items() if key != "api_key"})

        def with_structured_output(self, schema, **kwargs):
            """Require native JSON schema rather than tool binding or automatic fallback."""
            schemas.append((schema.__name__, kwargs))
            return self

    monkeypatch.setattr("taskify_chat.adapters.outbound.langchain_openai.ChatOpenAI", Model)
    OpenAIAnswerer(
        AcceptedConfiguration(
            "openai", "accepted-model-snapshot", "graph-v1", "prompt-v1", "responses-v1"
        ),
        "fixture-not-a-provider-key",
    )
    assert captured["model"] == "accepted-model-snapshot"
    assert (
        captured["use_responses_api"] is True
        and captured["store"] is False
        and captured["max_retries"] == 0
    )
    assert not {"tools", "temperature", "reasoning_effort", "previous_response_id"} & set(captured)
    assert len(schemas) == 3 and all(
        kwargs == {"method": "json_schema", "strict": True} for _, kwargs in schemas
    )


def test_incompatible_models_fail_before_langchain_can_fall_back_to_tools() -> None:
    """Reject LangChain's known automatic function-calling fallback locally before role construction."""
    from taskify_chat.adapters.outbound.model_profiles import compatible
    from taskify_chat.application.ports.workflow import AcceptedConfiguration
    from taskify_chat.domain.errors import ApplicationError

    for model in ("gpt-3.5-turbo", "gpt-4", "gpt-4-0613"):
        with pytest.raises(ApplicationError):
            compatible(
                AcceptedConfiguration("openai", model, "graph-v1", "prompt-v1", "responses-v1")
            )
