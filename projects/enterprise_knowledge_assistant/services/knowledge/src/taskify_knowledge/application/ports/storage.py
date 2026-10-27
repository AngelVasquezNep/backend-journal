"""Private immutable object storage port carries server-owned keys, never public URLs or paths."""

from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Original:
    """Validated original identity; the adapter keeps its private filesystem location internal."""

    storage_key: str
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str


class ObjectStorage(Protocol):
    """Stage only validated complete originals before the owning database acceptance transaction."""

    def stage(self, filename: str, media_type: str, chunks: Iterable[bytes]) -> Original:
        """Stream with byte/format validation; reject unsafe content without exposing partial objects."""
        ...

    def verify(self, original: Original) -> None:
        """Require the original's stored size and SHA-256 identity before processing/publication."""
        ...

    def remove(self, storage_key: str) -> None:
        """Delete only an owned unreferenced key during reconciliation, never restore availability."""
        ...

    def protect(self, storage_key: str, *, blocking: bool = True) -> AbstractContextManager[bool]:
        """Serialize acceptance/reference checking against cleanup for this owned immutable key."""
        ...

    def stale_objects(self, before: datetime, limit: int = 1000) -> tuple[str, ...]:
        """List a bounded batch of regular objects older than the orphan grace period."""
        ...
