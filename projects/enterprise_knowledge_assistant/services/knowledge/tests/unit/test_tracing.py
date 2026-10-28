"""Tracing configuration rejects silent disablement and requires redacted exports."""

import pytest

from taskify_knowledge.adapters.outbound.settings import validate_tracing


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
