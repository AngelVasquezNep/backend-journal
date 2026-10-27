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

from taskify_identity.adapters.outbound.postgres.unit_of_work import owned_engine


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
        or f"postgresql+psycopg://identity_runtime:{env.get('IDENTITY_DB_PASSWORD', '')}@127.0.0.1:55432/identity_test"
    )
    migration = (
        env.get("TASKIFY_TEST_MIGRATION_DATABASE_URL")
        or f"postgresql+psycopg://identity_migration:{env.get('IDENTITY_MIGRATION_PASSWORD', '')}@127.0.0.1:55432/identity_test"
    )
    for value, role in ((runtime, "identity_runtime"), (migration, "identity_migration")):
        url = make_url(value)
        if url.database != "identity_test" or url.username != role:
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
def identity_service(
    database_urls: tuple[str, str], migration_engine: Engine, clock: FakeClock, monkeypatch
):
    """Migrate and seed only identity_test through the operator application use case."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from taskify_identity.adapters.outbound.postgres.repositories import SqlIdentityStore
    from taskify_identity.adapters.outbound.security.passwords import ArgonPasswords
    from taskify_identity.adapters.outbound.security.tokens import SecureTokens
    from taskify_identity.adapters.outbound.system import RandomIds
    from taskify_identity.application.authenticate import IdentityService
    from taskify_identity.application.provision_admin import provision_admin

    root = Path(__file__).resolve().parents[1]
    with monkeypatch.context() as context:
        context.setenv("DATABASE_URL", database_urls[1])
        command.upgrade(Config(str(root / "alembic.ini")), "head")
    with migration_engine.begin() as connection:
        connection.execute(text("TRUNCATE companies CASCADE"))
        connection.execute(text("TRUNCATE login_attempt_windows"))
    engine = owned_engine(database_urls[0])
    service = IdentityService(
        SqlIdentityStore(engine),
        ArgonPasswords(),
        SecureTokens("test-key-" + "x" * 32),
        clock,
        RandomIds(),
    )
    provision_admin(
        service.store,
        service.passwords,
        clock,
        service.ids,
        company_name="Company A",
        company_id=None,
        display_name="Admin",
        email="admin@example.test",
        password="Initial-password-123",
    )
    yield service
    engine.dispose()


@pytest.fixture
def identity_client(identity_service, database_urls: tuple[str, str]):
    """Expose only real owned application routes with deterministic clock and private fixture settings."""
    from fastapi.testclient import TestClient

    from taskify_identity.adapters.outbound.settings import Settings
    from taskify_identity.bootstrap import create_app

    keys = (
        "KNOWLEDGE_API_CREDENTIAL",
        "KNOWLEDGE_WORKER_CREDENTIAL",
        "CHAT_API_CREDENTIAL",
        "CHAT_WORKER_CREDENTIAL",
    )
    values = ("knowledge-api-", "knowledge-worker-", "chat-api-", "chat-worker-")
    settings = Settings(
        database_urls[0],
        "test",
        "http://localhost:8080",
        "none",
        session_hmac_key="test-key-" + "x" * 32,
        internal_credentials=tuple(
            (key, prefix + "x" * 32) for key, prefix in zip(keys, values, strict=True)
        ),
    )
    with TestClient(create_app(settings, identity_service)) as client:
        yield client
