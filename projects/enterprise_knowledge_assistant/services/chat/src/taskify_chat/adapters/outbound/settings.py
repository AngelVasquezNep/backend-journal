"""Bootstrap-only configuration; validation never makes a paid provider request."""

import os
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping, Self
from urllib.parse import urlparse

from sqlalchemy.engine import make_url


def required(environment: Mapping[str, str], key: str) -> str:
    """Read a required setting without echoing secret contents on failure."""
    value = environment.get(key, "")
    if not value or value == "CHANGE_ME":
        raise ValueError(f"{key} must be configured.")
    return value


def validate_tracing(environment: Mapping[str, str]) -> None:
    """Validate opt-in tracing locally; keep private inputs and outputs out of exported runs."""
    enabled = environment.get("LANGSMITH_TRACING", "false")
    if enabled not in ("true", "false"):
        raise ValueError("LANGSMITH_TRACING must be true or false.")
    for key in ("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING_V2"):
        if key in environment and environment[key] != enabled:
            raise ValueError(f"{key} must match LANGSMITH_TRACING.")
    if enabled == "false":
        return
    required(environment, "LANGSMITH_API_KEY")
    if not environment.get("LANGSMITH_PROJECT", "taskify-local").strip():
        raise ValueError("LANGSMITH_PROJECT must not be blank.")
    endpoint = urlparse(environment.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"))
    if (
        endpoint.scheme != "https"
        or not endpoint.hostname
        or endpoint.username
        or endpoint.password
    ):
        raise ValueError("LANGSMITH_ENDPOINT must be an HTTPS API endpoint without credentials.")
    for key in ("LANGSMITH_HIDE_INPUTS", "LANGSMITH_HIDE_OUTPUTS"):
        if environment.get(key) != "true":
            raise ValueError(f"{key}=true is required when tracing is enabled.")


@dataclass(frozen=True)
class Settings:
    """Immutable service-owned settings; credentials are excluded from representations."""

    database_url: str = field(repr=False)
    taskify_env: str
    public_origin: str
    ai_mode: str
    model: str | None = None
    api_key: str | None = field(default=None, repr=False)
    identity_url: str | None = None
    knowledge_url: str | None = None
    service_credential: str | None = field(default=None, repr=False)
    worker_credential: str | None = field(default=None, repr=False)
    session_hmac_key: str | None = field(default=None, repr=False)
    internal_credentials: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    storage_root: str | None = None
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    pipeline_version: str = "pipeline-v1"

    @property
    def production(self) -> bool:
        """Select secure cookies and encrypted service traffic outside development/test."""
        return self.taskify_env == "production"

    @property
    def cookie_name(self) -> str:
        """Select the production __Host cookie or explicit loopback development name."""
        return "__Host-taskify_session" if self.production else "taskify_session"

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None) -> Self:
        """Validate owned settings before composing adapters; never infer a chat-model alias."""
        env = os.environ if environment is None else environment
        mode = env.get("TASKIFY_ENV", "development")
        if mode not in ("development", "test", "production"):
            raise ValueError("TASKIFY_ENV must be development, test or production.")
        database = required(env, "DATABASE_URL")
        url = make_url(database)
        if (
            url.drivername != "postgresql+psycopg"
            or url.username != "chat_runtime"
            or url.database not in ("chat", "chat_test")
        ):
            raise ValueError("DATABASE_URL must use the owned non-owner runtime role/database.")
        origin = required(env, "PUBLIC_ORIGIN")
        public = urlparse(origin)
        if (
            public.scheme not in ("http", "https")
            or not public.hostname
            or public.path
            or public.query
            or public.fragment
            or public.username
            or public.password
        ):
            raise ValueError("PUBLIC_ORIGIN must be an exact origin without a path.")
        if public.scheme != "https" and not (
            mode in ("development", "test") and public.hostname in ("localhost", "127.0.0.1", "::1")
        ):
            raise ValueError("HTTPS is required outside loopback development.")
        ai_mode = env.get("AI_MODE", "stub")
        if ai_mode not in ("stub", "openai") or (mode == "production" and ai_mode != "openai"):
            raise ValueError("AI_MODE must be openai in production; stub is development/test only.")
        validate_tracing(env)
        values: dict[str, Any] = {}
        values["identity_url"] = required(env, "IDENTITY_URL")
        values["knowledge_url"] = required(env, "KNOWLEDGE_URL")
        values["service_credential"] = required(env, "SERVICE_CREDENTIAL")
        values["worker_credential"] = required(env, "WORKER_CREDENTIAL")
        if mode == "production" and any(
            urlparse(values[key]).scheme != "https" for key in ("identity_url", "knowledge_url")
        ):
            raise ValueError("Production service traffic requires HTTPS.")
        if ai_mode == "openai":
            model = required(env, "OPEN_AI_MODEL")
            if len(model) > 200 or any(
                c.isspace() or unicodedata.category(c) == "Cc" for c in model
            ):
                raise ValueError(
                    "OPEN_AI_MODEL must be a nonempty whitespace/control-free ID of at most 200 characters."
                )
            values["model"] = model
            values["api_key"] = required(env, "OPENAI_API_KEY")
        else:
            values["model"] = "stub-fixture-v1"
        return cls(
            database_url=database, taskify_env=mode, public_origin=origin, ai_mode=ai_mode, **values
        )
