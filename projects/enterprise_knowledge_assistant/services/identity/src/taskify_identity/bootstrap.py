"""Identity composition root wires owned adapters; no provider or other service database is used."""

import uvicorn
from fastapi import FastAPI
from sqlalchemy import text

from taskify_identity.adapters.inbound.http.auth import auth_router
from taskify_identity.adapters.inbound.http.common import install_boundaries, install_health
from taskify_identity.adapters.inbound.http.internal_sessions import internal_router
from taskify_identity.adapters.inbound.http.users import users_router
from taskify_identity.adapters.outbound.operational import configure_logging
from taskify_identity.adapters.outbound.postgres.repositories import SqlIdentityStore
from taskify_identity.adapters.outbound.postgres.unit_of_work import owned_engine
from taskify_identity.adapters.outbound.security.passwords import ArgonPasswords
from taskify_identity.adapters.outbound.security.tokens import SecureTokens
from taskify_identity.adapters.outbound.settings import Settings
from taskify_identity.adapters.outbound.system import RandomIds, SystemClock
from taskify_identity.application.authenticate import IdentityService
from taskify_identity.domain.errors import DependencyUnavailable


def create_service(settings: Settings) -> IdentityService:
    """Compose runtime-role storage, Argon2id, opaque tokens and UTC/UUID ports without queries."""
    if settings.session_hmac_key is None:
        raise ValueError("Identity requires a session/email HMAC key.")
    return IdentityService(
        SqlIdentityStore(owned_engine(settings.database_url)),
        ArgonPasswords(),
        SecureTokens(settings.session_hmac_key),
        SystemClock(),
        RandomIds(),
    )


def create_app(settings: Settings | None = None, service: IdentityService | None = None) -> FastAPI:
    """Create the first-party service, accepting explicit owned dependencies for real-storage tests."""
    resolved = settings or Settings.from_env()
    identity = service or create_service(resolved)
    app = FastAPI(title="Taskify Identity", docs_url=None, redoc_url=None, openapi_url=None)
    install_boundaries(app)
    app.include_router(auth_router(identity, resolved))
    app.include_router(users_router(identity, resolved))
    app.include_router(internal_router(identity, resolved))

    def ready() -> None:
        """Check the actual owned runtime pool/schema, without making an external/provider call."""
        store = identity.store
        if not isinstance(store, SqlIdentityStore):
            raise DependencyUnavailable()
        with store.engine.connect() as connection:
            connection.execute(text("SELECT id FROM companies LIMIT 0"))

    install_health(app, ready)
    app.state.identity_service = identity
    return app


def main() -> None:
    """Start the independent service with private diagnostics and no request-body/access tracing."""
    configure_logging()
    uvicorn.run(
        "taskify_identity.bootstrap:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        access_log=False,
    )
