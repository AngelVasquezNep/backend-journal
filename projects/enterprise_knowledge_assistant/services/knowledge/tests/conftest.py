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

from taskify_knowledge.adapters.outbound.postgres.unit_of_work import owned_engine


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
    local = next(
        (
            parent / ".env"
            for parent in Path(__file__).resolve().parents
            if (parent / ".env").is_file()
        ),
        Path("/nonexistent/taskify-env"),
    )
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
        or f"postgresql+psycopg://knowledge_runtime:{env.get('KNOWLEDGE_DB_PASSWORD', '')}@127.0.0.1:55432/knowledge_test"
    )
    migration = (
        env.get("TASKIFY_TEST_MIGRATION_DATABASE_URL")
        or f"postgresql+psycopg://knowledge_migration:{env.get('KNOWLEDGE_MIGRATION_PASSWORD', '')}@127.0.0.1:55432/knowledge_test"
    )
    for value, role in ((runtime, "knowledge_runtime"), (migration, "knowledge_migration")):
        url = make_url(value)
        if url.database != "knowledge_test" or url.username != role:
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


@pytest.fixture(scope="session")
def corpus(tmp_path_factory):
    """Generate public two-company parser fixtures locally, without contacting an external provider."""
    import importlib.util

    root = Path(
        os.environ.get("TASKIFY_TEST_PROJECT_ROOT") or str(Path(__file__).resolve().parents[3])
    )
    spec = importlib.util.spec_from_file_location(
        "taskify_corpus_builder", root / "tests/fixtures/build_corpus.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path_factory.mktemp("corpus")
    module.build(target)
    return target


@pytest.fixture
def extractor(tmp_path):
    """Exercise real host extraction with the installed English pack; production images include eng+spa."""
    from taskify_knowledge.adapters.outbound.extraction import LocalExtractor

    if os.sys.platform != "linux":
        pytest.skip(
            "Strict parser isolation requires Linux; run docker compose run --rm --build knowledge-test."
        )
    return LocalExtractor(tmp_path, languages="eng+spa")


@pytest.fixture
def admin_principal(clock: FakeClock):
    """Create a contract-valid trusted fixture principal, never a public authentication bypass."""
    from taskify_knowledge.application.ports.identity import Principal

    return Principal(uuid4(), uuid4(), uuid4(), "admin", False, clock.now() + timedelta(minutes=30))


@pytest.fixture
def knowledge_service(
    database_urls: tuple[str, str],
    migration_engine: Engine,
    clock: FakeClock,
    tmp_path,
    monkeypatch,
):
    """Migrate/seed only knowledge_test and use real parsers plus a separately tagged fixture vector space."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from taskify_knowledge.adapters.outbound.chunking import TokenChunker
    from taskify_knowledge.adapters.outbound.embeddings import DeterministicEmbedder
    from taskify_knowledge.adapters.outbound.extraction import LocalExtractor
    from taskify_knowledge.adapters.outbound.filesystem import FilesystemStorage
    from taskify_knowledge.adapters.outbound.postgres.cursors import CursorCodec
    from taskify_knowledge.adapters.outbound.postgres.repositories import SqlKnowledgeStore
    from taskify_knowledge.adapters.outbound.settings import Settings
    from taskify_knowledge.adapters.outbound.system import RandomIds
    from taskify_knowledge.application.service import KnowledgeService
    from taskify_knowledge.bootstrap import pipeline

    if os.sys.platform != "linux":
        pytest.skip("Use the Linux knowledge-test container for parser-backed storage contracts.")
    root = Path(__file__).resolve().parents[1]
    with monkeypatch.context() as context:
        context.setenv("DATABASE_URL", database_urls[1])
        command.upgrade(Config(str(root / "alembic.ini")), "head")
    with migration_engine.begin() as connection:
        connection.execute(text("TRUNCATE knowledge_items CASCADE"))
        connection.execute(text("TRUNCATE pipeline_configurations CASCADE"))
    engine = owned_engine(database_urls[0])
    selected = pipeline(Settings(database_urls[0], "test", "http://localhost:8080", "stub"), clock)
    store = SqlKnowledgeStore(engine, CursorCodec("fixture-cursor-" + "x" * 32))
    store.register_pipeline(selected)
    parser = LocalExtractor(tmp_path, languages="eng+spa")
    service = KnowledgeService(
        store,
        FilesystemStorage(tmp_path, parser),
        parser,
        TokenChunker(),
        DeterministicEmbedder(),
        selected,
        clock,
        RandomIds(),
        lambda: 0.5,
    )
    yield service
    engine.dispose()


@pytest.fixture
def knowledge_worker(knowledge_service):
    """Process the actual durable queue with real extraction and deterministic fixture vectors."""
    from taskify_knowledge.adapters.inbound.worker import IngestionWorker

    return IngestionWorker(knowledge_service)


@pytest.fixture
def knowledge_client(
    knowledge_service, admin_principal, clock: FakeClock, database_urls: tuple[str, str]
):
    """Wire contract-safe online Identity doubles inside tests only; no seed/auth-bypass route exists."""
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from taskify_knowledge.adapters.outbound.settings import Settings
    from taskify_knowledge.application.ports.identity import SessionRequest
    from taskify_knowledge.bootstrap import create_app
    from taskify_knowledge.domain.errors import ApplicationError, AuthenticationRequired

    principals = {
        "A" * 43: admin_principal,
        "B" * 43: replace(admin_principal, account_id=uuid4(), role="user"),
        "C" * 43: replace(admin_principal, account_id=uuid4(), company_id=uuid4()),
    }

    class IdentityDouble:
        """Accept only predeclared fixture cookies and exact synchronizer material under requested policy."""

        def resolve(self, request: SessionRequest, request_id: UUID):
            """Validate fixture identity/CSRF with the receiving-handler-selected activity contract."""
            principal = (
                principals.get(request.session_token or "")
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
            if principal is None or principal.idle_expires_at <= clock.now():
                raise AuthenticationRequired()
            if request.require_csrf and request.csrf_token != "c" * 64:
                raise ApplicationError("csrf_failed", "Refresh the session and retry.", 403)
            return replace(principal, csrf_valid=True if request.require_csrf else None)

    settings = Settings(
        database_urls[0],
        "test",
        "http://localhost:8080",
        "stub",
        storage_root=str(knowledge_service.storage.root),
        internal_credentials=(
            ("CHAT_API_CREDENTIAL", "fixture-chat-api-" + "x" * 32),
            ("CHAT_WORKER_CREDENTIAL", "fixture-chat-worker-" + "x" * 32),
        ),
    )
    with TestClient(create_app(settings, knowledge_service, IdentityDouble())) as client:
        client.cookies.set("taskify_session", "A" * 43)
        yield client
