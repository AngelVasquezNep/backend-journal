"""Owned shared invariants for immutable knowledge metadata and UTC provenance."""

import re
from datetime import datetime, timedelta
from uuid import UUID


def ids(*values: UUID) -> None:
    """Require actual UUID values after receiving-boundary parsing, without string coercion."""
    if any(not isinstance(value, UUID) for value in values):
        raise ValueError("Knowledge identifiers must be UUIDs.")


def utc(*values: datetime | None) -> None:
    """Require aware UTC timestamps; optional lifecycle times remain None until applicable."""
    if any(
        value is not None and (value.tzinfo is None or value.utcoffset() != timedelta(0))
        for value in values
    ):
        raise ValueError("Knowledge timestamps must be UTC.")


def digest(value: str) -> None:
    """Require a lowercase SHA-256 hex identity; never include private bytes in errors."""
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Invalid content digest.")
