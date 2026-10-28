"""Owned test factories never seed production databases or expose a public authentication bypass."""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url

from taskify_chat.adapters.outbound.postgres.unit_of_work import owned_engine


@dataclass
class FakeClock:
    """Controllable aware UTC clock; only tests can move it without waiting for real time."""

    instant: datetime

    def now(self) -> datetime:
        """Return the current fixture instant without extending any login session."""
        return self.instant

    def advance(self, seconds: float) -> None:
        """Advance fixture time for exact expiry, lease and rate-window boundaries."""
        self.instant += timedelta(seconds=seconds)


@pytest.fixture
def clock() -> FakeClock:
    """Supply a deterministic UTC clock independent of process/provider time."""
    return FakeClock(datetime(2026, 10, 21, tzinfo=UTC))


@pytest.fixture
def owner_ids() -> tuple[UUID, UUID, UUID, UUID]:
    """Return two companies and distinct accounts for cross-owner security cases."""
    return uuid4(), uuid4(), uuid4(), uuid4()


def private_environment() -> dict[str, str]:
    """Read only local fixture configuration; never print credentials or evaluate shell content."""
    values: dict[str, str] = {}
    local = Path(__file__).resolve().parents[3] / ".env"
    if local.exists():
        for line in local.read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    values.update(os.environ)
    return values


@pytest.fixture(scope="session")
def database_urls() -> tuple[str, str]:
    """Require opt-in real storage; reject any URL outside this service's dedicated test database."""
    if os.environ.get("TASKIFY_RUN_DB_TESTS") != "1":
        pytest.skip("Real PostgreSQL checks require TASKIFY_RUN_DB_TESTS=1.")
    env = private_environment()
    runtime = (
        env.get("TASKIFY_TEST_DATABASE_URL")
        or f"postgresql+psycopg://chat_runtime:{env.get('CHAT_DB_PASSWORD', '')}@127.0.0.1:55432/chat_test"
    )
    migration = (
        env.get("TASKIFY_TEST_MIGRATION_DATABASE_URL")
        or f"postgresql+psycopg://chat_migration:{env.get('CHAT_MIGRATION_PASSWORD', '')}@127.0.0.1:55432/chat_test"
    )
    for value, role in ((runtime, "chat_runtime"), (migration, "chat_migration")):
        url = make_url(value)
        if url.database != "chat_test" or url.username != role:
            pytest.fail(
                "Fixtures may access only the owning service test database with its matching role."
            )
    return runtime, migration


@pytest.fixture
def runtime_engine(database_urls: tuple[str, str]) -> Iterator[Engine]:
    """Exercise the actual non-owner role and resetting pool; always release connections."""
    engine = owned_engine(database_urls[0])
    yield engine
    engine.dispose()


@pytest.fixture
def migration_engine(database_urls: tuple[str, str]) -> Iterator[Engine]:
    """Create only service-owned test fixtures with the separate migration role."""
    engine = create_engine(database_urls[1], echo=False, hide_parameters=True)
    yield engine
    engine.dispose()


@pytest.fixture
def knowledge_double(clock):
    """Contract-valid current evidence double never counts as real OpenAI quality evidence."""
    from taskify_chat.application.ports.knowledge import (
        CitationKey,
        Evidence,
        SearchResult,
        SourceSnapshot,
        SourceStatus,
    )

    class KnowledgeDouble:
        """Mutable fixture retrieval version permits recovery/source-change tests without external APIs."""

        version = "retrieval-fixture-v1"
        current = True
        evidence = Evidence(
            uuid4(),
            uuid4(),
            uuid4(),
            "Leave policy",
            "Company leave policy grants 20 days of annual leave.",
            {"kind": "text", "line_start": 1, "line_end": 1},
            0.9,
        )

        def search(self, login_session_id, query, request_id):
            """Return bounded own fixture evidence tagged with the then-current retrieval version."""
            return SearchResult("pipeline-fixture-v1", self.version, (self.evidence,))

        def validate(self, login_session_id, citations, purpose, request_id):
            """Produce a fresh exact batch whose availability can be changed at the final checkpoint."""
            key = CitationKey(
                self.evidence.item_id, self.evidence.revision_id, self.evidence.chunk_id
            )
            sources = tuple(
                SourceStatus(
                    value,
                    "current" if self.current and value == key else "unavailable",
                    self.evidence.title if self.current and value == key else None,
                    self.evidence.locator if self.current and value == key else None,
                    f"/api/v1/knowledge/{key.item_id}/source?revision_id={key.revision_id}"
                    if self.current and value == key
                    else None,
                )
                for value in citations
            )
            return SourceSnapshot(
                clock.now(), all(value.availability == "current" for value in sources), sources
            )

    return KnowledgeDouble()


@pytest.fixture
def chat_principal(clock):
    """Return a trusted fixture owner, with no public bypass/seed endpoint."""
    from taskify_chat.application.ports.identity import Principal

    return Principal(uuid4(), uuid4(), uuid4(), "user", False, clock.now() + timedelta(minutes=30))


@pytest.fixture
def identity_double(chat_principal, clock):
    """Validate only declared tokens/session IDs and enforce exact inactivity and CSRF in tests."""
    from dataclasses import replace

    from taskify_chat.domain.errors import ApplicationError, AuthenticationRequired

    principals = {
        "A" * 43: chat_principal,
        "B" * 43: replace(chat_principal, login_session_id=uuid4(), account_id=uuid4()),
        "C" * 43: replace(
            chat_principal, login_session_id=uuid4(), account_id=uuid4(), company_id=uuid4()
        ),
    }

    class IdentityDouble:
        """Receiving handlers select activity; no browser input can forge trusted company authority."""

        def resolve(self, request, request_id):
            """Return a live principal only for exact known selectors and requested synchronizer material."""
            principal = (
                principals.get(request.session_token)
                if request.session_token
                else next(
                    (
                        value
                        for value in principals.values()
                        if value.login_session_id == request.login_session_id
                    ),
                    None,
                )
            )
            if principal is None or clock.now() >= principal.idle_expires_at:
                raise AuthenticationRequired()
            if request.require_csrf and request.csrf_token != "c" * 64:
                raise ApplicationError("csrf_failed", "Refresh and retry.", 403)
            return replace(principal, csrf_valid=True if request.require_csrf else None)

    return IdentityDouble()


@pytest.fixture
def chat_service(
    database_urls, migration_engine, clock, knowledge_double, identity_double, monkeypatch
):
    """Run actual owned migrations/RLS/leases with a deterministic graph model and online-contract doubles."""
    import time

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from taskify_chat.adapters.outbound.langchain_openai import StubAnswerer
    from taskify_chat.adapters.outbound.langgraph_workflow import LangGraphWorkflow
    from taskify_chat.adapters.outbound.postgres.repositories import SqlChatStore
    from taskify_chat.adapters.outbound.system import RandomIds
    from taskify_chat.application.ports.workflow import AcceptedConfiguration
    from taskify_chat.application.service import ChatService

    root = Path(__file__).resolve().parents[1]
    with monkeypatch.context() as context:
        context.setenv("DATABASE_URL", database_urls[1])
        command.upgrade(Config(str(root / "alembic.ini")), "head")
    with migration_engine.begin() as connection:
        connection.execute(text("TRUNCATE conversations CASCADE"))
    engine = owned_engine(database_urls[0])
    yield ChatService(
        SqlChatStore(engine, "fixture-cursor-key-" + "x" * 32),
        identity_double,
        knowledge_double,
        LangGraphWorkflow(knowledge_double, lambda configuration: StubAnswerer()),
        clock,
        RandomIds(),
        AcceptedConfiguration("stub", "stub-fixture-v1", "graph-v1", "prompt-v2", "responses-v1"),
        time.monotonic,
    )
    engine.dispose()


@pytest.fixture
def chat_client(chat_service, identity_double, database_urls):
    """Wire exact public routes to owned real storage and explicitly injected fixture session policy."""
    from fastapi.testclient import TestClient

    from taskify_chat.adapters.outbound.settings import Settings
    from taskify_chat.bootstrap import create_app

    with TestClient(
        create_app(
            Settings(
                database_urls[0], "test", "http://localhost:8080", "stub", model="stub-fixture-v1"
            ),
            chat_service,
            identity_double,
        )
    ) as client:
        client.cookies.set("taskify_session", "A" * 43)
        yield client


@pytest.fixture
def chat_worker(chat_service):
    """Process actual SQL claims/heartbeats/final terminal transactions through the real graph."""
    from taskify_chat.adapters.inbound.worker import AnswerWorker

    return AnswerWorker(chat_service)
