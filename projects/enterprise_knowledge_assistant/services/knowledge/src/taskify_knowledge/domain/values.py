"""Knowledge-owned values and metadata bounds, independent from transport and parsers."""

import unicodedata
from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID

MAX_FILE_BYTES = 20_971_520
MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def identifier(value: UUID | str) -> UUID:
    """Return a valid UUID or raise a safe validation error."""
    try:
        return value if isinstance(value, UUID) else UUID(value)
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError("A valid UUID is required.") from error


def sequence(value: int) -> int:
    """Require 'Valid UUID; positive item version; sequence integer >= 0'; reject coercion."""
    if type(value) is not int or value < 0:
        raise ValueError("Sequence must be a nonnegative integer.")
    return value


def positive_version(value: int) -> int:
    """Require a positive integer version for optimistic concurrency."""
    if type(value) is not int or value < 1:
        raise ValueError("Version must be a positive integer.")
    return value


@dataclass(frozen=True)
class Title:
    """Trim; 1–200 code points; reject control characters."""

    value: str

    def __post_init__(self) -> None:
        """Validate and normalize the title; failures reveal only the corrective bounds."""
        if not isinstance(self.value, str):
            raise ValueError("A title must be text.")
        value = self.value.strip()
        if not 1 <= len(value) <= 200 or any(unicodedata.category(c) == "Cc" for c in self.value):
            raise ValueError("Titles must contain 1–200 characters and no controls.")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class FileMetadata:
    """Validate names/sizes/types; matching extension/content is verified by the file adapter.

    1–255 characters, no separators/control characters; 1–20,971,520 bytes inclusive;
    allowlisted MIME and matching extension/content are mandatory before acceptance.
    """

    filename: str
    size_bytes: int
    media_type: str

    def __post_init__(self) -> None:
        """Reject invalid file metadata; metadata alone cannot authorize content publication."""
        if not isinstance(self.filename, str) or not 1 <= len(self.filename) <= 255:
            raise ValueError("Filenames must contain 1–255 characters.")
        if any(c in "/\\" or unicodedata.category(c) == "Cc" for c in self.filename):
            raise ValueError("Filenames cannot contain path separators or controls.")
        if type(self.size_bytes) is not int or not 1 <= self.size_bytes <= MAX_FILE_BYTES:
            raise ValueError("File size must be 1–20,971,520 bytes.")
        if MEDIA_TYPES.get(PurePosixPath(self.filename).suffix.lower()) != self.media_type:
            raise ValueError("File extension and media type must match a supported format.")


@dataclass(frozen=True)
class Pagination:
    """`limit` 1–100, default 50; opaque bounded cursor <= 512 characters, scoped to query/owner."""

    limit: int = 50
    cursor: str | None = None

    def __post_init__(self) -> None:
        """Check transport-independent bounds; repositories enforce opaque cursor ownership."""
        if type(self.limit) is not int or not 1 <= self.limit <= 100:
            raise ValueError("Limit must be an integer from 1 to 100.")
        if self.cursor is not None and (
            not isinstance(self.cursor, str) or not 1 <= len(self.cursor) <= 512
        ):
            raise ValueError("Cursor must contain 1–512 characters.")
