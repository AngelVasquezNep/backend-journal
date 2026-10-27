"""Chat composition uses only owned persistence and authenticated Identity/Knowledge HTTP contracts."""

import time

import httpx
import uvicorn
from fastapi import FastAPI
from sqlalchemy import text

from taskify_chat.adapters.inbound.http.chat import chat_router
from taskify_chat.adapters.inbound.http.common import install_boundaries, install_health
from taskify_chat.adapters.outbound.http.identity import IdentityHTTP
from taskify_chat.adapters.outbound.http.knowledge import KnowledgeHTTP
from taskify_chat.adapters.outbound.langchain_openai import OpenAIAnswerer, StubAnswerer
from taskify_chat.adapters.outbound.langgraph_workflow import LangGraphWorkflow
from taskify_chat.adapters.outbound.model_profiles import compatible
from taskify_chat.adapters.outbound.operational import configure_logging
from taskify_chat.adapters.outbound.postgres.repositories import SqlChatStore
from taskify_chat.adapters.outbound.postgres.unit_of_work import owned_engine
from taskify_chat.adapters.outbound.settings import Settings
from taskify_chat.adapters.outbound.system import RandomIds, SystemClock
from taskify_chat.application.ports.answerer import Answerer
from taskify_chat.application.ports.identity import SessionValidator
from taskify_chat.application.ports.workflow import AcceptedConfiguration
from taskify_chat.application.service import ChatService
from taskify_chat.domain.errors import DependencyUnavailable


def create_service(settings: Settings | None = None, *, worker: bool = False) -> ChatService:
    """Compose locally validated exact-model roles without making a paid availability probe."""
    resolved = settings or Settings.from_env()
    accepted = AcceptedConfiguration(
        resolved.ai_mode, resolved.model or "", "graph-v1", "prompt-v1", "responses-v1"
    )
    compatible(accepted)
    identity = IdentityHTTP(
        resolved.identity_url or "",
        resolved.worker_credential or "",
        worker=True,
        allow_insecure=not resolved.production,
    )
    knowledge = KnowledgeHTTP(
        resolved.knowledge_url or "",
        (resolved.worker_credential if worker else resolved.service_credential) or "",
        allow_insecure=not resolved.production,
    )

    def answerer(configuration: AcceptedConfiguration) -> Answerer:
        """Recover the accepted mode/model/profile; never substitute the current environment's model."""
        if configuration.ai_mode == "stub":
            if resolved.production:
                raise DependencyUnavailable()
            return StubAnswerer()
        return OpenAIAnswerer(configuration, resolved.api_key or "")

    return ChatService(
        SqlChatStore(owned_engine(resolved.database_url), resolved.service_credential or ""),
        identity,
        knowledge,
        LangGraphWorkflow(knowledge, answerer),
        SystemClock(),
        RandomIds(),
        AcceptedConfiguration(
            resolved.ai_mode, resolved.model or "", "graph-v1", "prompt-v1", "responses-v1"
        ),
        time.monotonic,
    )


def create_app(
    settings: Settings | None = None,
    service: ChatService | None = None,
    identity: SessionValidator | None = None,
) -> FastAPI:
    """Expose the private saved chat; all browser authority is resolved online using API credentials."""
    resolved = settings or Settings.from_env()
    chat = service or create_service(resolved)
    public_identity = identity or IdentityHTTP(
        resolved.identity_url or "",
        resolved.service_credential or "",
        allow_insecure=not resolved.production,
    )
    app = FastAPI(title="Taskify Chat", docs_url=None, redoc_url=None, openapi_url=None)
    install_boundaries(app)
    app.include_router(chat_router(chat, public_identity, resolved))

    def ready() -> None:
        """Check owned schema/queue and validated local model configuration, never a paid provider call."""
        if not isinstance(chat.store, SqlChatStore):
            raise DependencyUnavailable()
        with chat.store.engine.connect() as connection:
            connection.execute(text("SELECT id FROM chat_turns LIMIT 0"))

        for dependency in (resolved.identity_url, resolved.knowledge_url):
            if dependency:
                try:
                    response = httpx.get(
                        dependency.rstrip("/") + "/health/ready",
                        timeout=1.0,
                        follow_redirects=False,
                    )
                    if response.status_code != 200:
                        raise DependencyUnavailable()
                except httpx.HTTPError:
                    raise DependencyUnavailable() from None

    install_health(app, ready)
    return app


def main() -> None:
    """Start a private API with no request body/provider/access tracing or public operator capability."""
    configure_logging()
    uvicorn.run(
        "taskify_chat.bootstrap:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        access_log=False,
    )
