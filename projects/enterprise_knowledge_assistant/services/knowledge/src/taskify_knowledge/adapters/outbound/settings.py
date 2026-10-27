"""Bootstrap-only configuration; validation never makes a paid provider request."""

import os
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
            or url.username != "knowledge_runtime"
            or url.database not in ("knowledge", "knowledge_test")
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
        for key in ("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING"):
            if env.get(key, "false").lower() not in ("false", "0", ""):
                raise ValueError("Third-party content tracing must remain disabled.")
        values: dict[str, Any] = {}
        values["identity_url"] = required(env, "IDENTITY_URL")
        values["service_credential"] = required(env, "SERVICE_CREDENTIAL")
        values["worker_credential"] = required(env, "WORKER_CREDENTIAL")
        values["storage_root"] = required(env, "KNOWLEDGE_STORAGE_ROOT")
        values["pipeline_version"] = required(env, "PIPELINE_VERSION")
        values["internal_credentials"] = tuple(
            (key, required(env, key)) for key in ("CHAT_API_CREDENTIAL", "CHAT_WORKER_CREDENTIAL")
        )
        if (
            env.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small") != "text-embedding-3-small"
            or env.get("EMBEDDING_DIMENSIONS", "1536") != "1536"
        ):
            raise ValueError(
                "The initial embedding pipeline requires text-embedding-3-small and 1536 dimensions."
            )
        if mode == "production" and urlparse(values["identity_url"]).scheme != "https":
            raise ValueError("Production service traffic requires HTTPS.")
        if ai_mode == "openai":
            values["api_key"] = required(env, "OPENAI_API_KEY")
        return cls(
            database_url=database, taskify_env=mode, public_origin=origin, ai_mode=ai_mode, **values
        )
