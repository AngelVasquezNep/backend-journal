"""Owned time and identity-generation ports for deterministic application behavior."""

from datetime import datetime
from typing import Protocol
from uuid import UUID


class Clock(Protocol):
    """Supply an aware UTC instant; the application never reads process time directly."""

    def now(self) -> datetime:
        """Return current UTC time without changing application state."""
        ...


class IdGenerator(Protocol):
    """Supply UUIDs without coupling core entities to a specific generator."""

    def new(self) -> UUID:
        """Return a new identifier; the storage layer still enforces uniqueness."""
        ...
