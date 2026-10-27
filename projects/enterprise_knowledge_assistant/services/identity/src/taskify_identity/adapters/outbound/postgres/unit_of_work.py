"""Owned PostgreSQL transactions set trusted actor context locally and reset pooled state."""

from types import TracebackType
from typing import Self
from uuid import UUID

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session
from sqlalchemy.pool import ConnectionPoolEntry, PoolResetState


def reset_connection(
    connection: DBAPIConnection, record: ConnectionPoolEntry, state: PoolResetState
) -> None:
    """Clear session settings and temporary objects before a connection may serve another actor."""
    if state.terminate_only:
        return
    connection.rollback()
    cursor = connection.cursor()
    try:
        cursor.execute("RESET ALL")
        cursor.execute("DISCARD TEMP")
    finally:
        cursor.close()
    connection.commit()


def owned_engine(url: str) -> Engine:
    """Build a pool that rolls back and resets connections; this function performs no query."""
    engine = create_engine(url, pool_pre_ping=True, pool_reset_on_return=None, hide_parameters=True)
    event.listen(engine, "reset", reset_connection)
    return engine


class SqlUnitOfWork:
    """Own one short ORM transaction with context from a validated principal or stored job."""

    def __init__(self, engine: Engine, company_id: UUID, account_id: UUID | None = None) -> None:
        """Store trusted IDs; no connection is opened before entering the transaction."""
        if not isinstance(company_id, UUID) or (
            account_id is not None and not isinstance(account_id, UUID)
        ):
            raise ValueError("Trusted transaction identifiers must be UUIDs.")
        self.engine = engine
        self.company_id = company_id
        self.account_id = account_id
        self.session: Session | None = None

    def __enter__(self) -> Self:
        """Begin a scoped transaction; fail closed if context cannot be installed."""
        if self.session is not None:
            raise RuntimeError("A unit of work cannot be reentered.")
        session = Session(self.engine, expire_on_commit=False)
        try:
            session.execute(text("SET LOCAL lock_timeout = '3s'"))
            session.execute(text("SET LOCAL statement_timeout = '5s'"))
            session.execute(
                text(
                    "SELECT set_config('taskify.company_id', :company, true), set_config('taskify.account_id', :account, true)"
                ),
                {
                    "company": str(self.company_id),
                    "account": str(self.account_id) if self.account_id else "",
                },
            )
        except BaseException:
            session.close()
            raise
        self.session = session
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Rollback uncommitted writes and close; context never outlives the transaction."""
        if self.session is not None:
            self.session.rollback()
            self.session.close()
            self.session = None

    def commit(self) -> None:
        """Commit the scoped transaction; callers must exit before issuing more operations."""
        if self.session is None:
            raise RuntimeError("A unit of work must be entered first.")
        self.session.commit()

    def rollback(self) -> None:
        """Rollback scoped work; subsequent work requires a new unit of work."""
        if self.session is not None:
            self.session.rollback()
