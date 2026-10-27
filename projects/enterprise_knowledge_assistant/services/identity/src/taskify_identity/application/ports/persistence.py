"""Owned transaction ports expose no ORM, database session, or transport types."""

from types import TracebackType
from typing import Protocol, Self
from uuid import UUID


class UnitOfWork(Protocol):
    """One trusted actor transaction; unsuccessful exits roll back all domain changes."""

    def __enter__(self) -> Self:
        """Begin a transaction and return its owned repositories; reject nested entry."""
        ...

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        """Roll back uncommitted work and release resources even after an exception."""
        ...

    def commit(self) -> None:
        """Atomically persist validated changes; storage errors propagate to the adapter."""
        ...

    def rollback(self) -> None:
        """Discard changes without committing actor context or partial records."""
        ...


class UnitOfWorkFactory(Protocol):
    """Construct a transaction from authoritative identity or stored worker ownership."""

    def __call__(self, company_id: UUID, account_id: UUID | None = None) -> UnitOfWork:
        """Return a new scoped unit; user-controlled identity claims are never accepted."""
        ...
