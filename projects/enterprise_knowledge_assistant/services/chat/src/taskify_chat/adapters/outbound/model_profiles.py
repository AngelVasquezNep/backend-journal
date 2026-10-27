"""Explicit Responses profile omits unsupported optional parameters instead of guessing from model aliases."""

from taskify_chat.application.ports.workflow import AcceptedConfiguration
from taskify_chat.domain.errors import ApplicationError

GRAPH_VERSION = "graph-v1"
MODEL_CONFIG_VERSION = "responses-v1"


def compatible(configuration: AcceptedConfiguration) -> None:
    """Retain supported accepted versions on recovery; never silently replace a queued model/profile."""
    if (
        configuration.graph_version != GRAPH_VERSION
        or configuration.prompt_version != "prompt-v1"
        or configuration.model_config_version != MODEL_CONFIG_VERSION
        or configuration.ai_mode not in ("stub", "openai")
        or not configuration.model
        or len(configuration.model) > 200
        or any(char.isspace() or ord(char) < 32 for char in configuration.model)
    ):
        raise ApplicationError(
            "configuration_unavailable", "The accepted answer configuration is unavailable.", 503
        )
    if configuration.ai_mode == "openai" and (
        configuration.model.startswith(("gpt-3", "gpt-4-")) or configuration.model == "gpt-4"
    ):
        raise ApplicationError(
            "configuration_unavailable",
            "The accepted model is incompatible with native structured Responses.",
            503,
        )
