"""Chat values distinguish login-session IDs from persistent conversation ownership."""

from dataclasses import dataclass
from uuid import UUID


def identifier(value: UUID | str) -> UUID:
    """Return a valid UUID; reject malformed identifiers without disclosing the value."""
    try:
        return value if isinstance(value, UUID) else UUID(value)
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("A valid UUID is required.") from error


def sequence(value: int) -> int:
    """Require 'Valid UUID; positive item version; sequence integer >= 0'; exclude booleans."""
    if type(value) is not int or value < 0:
        raise ValueError("Sequence must be a nonnegative integer.")
    return value


def positive_version(value: int) -> int:
    """Return a positive version, excluding booleans and coerced string values."""
    if type(value) is not int or value < 1:
        raise ValueError("Version must be a positive integer.")
    return value


@dataclass(frozen=True)
class MessageText:
    """Trim; 1–4000 code points; prior messages never become company evidence."""

    value: str

    def __post_init__(self) -> None:
        """Validate the trimmed question without shortening its Unicode content."""
        if not isinstance(self.value, str) or not 1 <= len(self.value.strip()) <= 4000:
            raise ValueError("Messages must contain 1–4000 characters after trimming.")
        object.__setattr__(self, "value", self.value.strip())


@dataclass(frozen=True)
class Pagination:
    """`limit` 1–100, default 50; opaque bounded cursor <= 512 characters, scoped to query/owner."""

    limit: int = 50
    cursor: str | None = None

    def __post_init__(self) -> None:
        """Check bounds; the owning repository must authenticate the cursor's query/owner scope."""
        if type(self.limit) is not int or not 1 <= self.limit <= 100:
            raise ValueError("Limit must be an integer from 1 to 100.")
        if self.cursor is not None and (
            not isinstance(self.cursor, str) or not 1 <= len(self.cursor) <= 512
        ):
            raise ValueError("Cursor must contain 1–512 characters.")
