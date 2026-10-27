"""Knowledge-only private immutable originals: stream, inspect, verify and reconcile owned keys."""

import fcntl
import hashlib
import os
import re
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from taskify_knowledge.adapters.outbound.extraction import LocalExtractor
from taskify_knowledge.application.ports.storage import Original
from taskify_knowledge.domain.errors import ApplicationError, DependencyUnavailable
from taskify_knowledge.domain.values import MAX_FILE_BYTES, MEDIA_TYPES, FileMetadata


class FilesystemStorage:
    """Expose no public path/URL; only Knowledge API/worker processes mount this private root."""

    def __init__(self, root: Path, inspector: LocalExtractor) -> None:
        """Create a private service-owned root and retain bounded structural validation."""
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.inspector = inspector
        self.locks = self.root / ".locks"
        self.locks.mkdir(mode=0o700, exist_ok=True)

    @contextmanager
    def protect(self, storage_key: str, *, blocking: bool = True) -> Iterator[bool]:
        """Use bounded permanent lock shards shared by API and worker on the same private volume."""
        self.path_for(storage_key)
        descriptor = os.open(
            self.locks / str(int(storage_key, 16) % 64), os.O_RDWR | os.O_CREAT, 0o600
        )
        with os.fdopen(descriptor, "rb") as guard:
            try:
                fcntl.flock(guard.fileno(), fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
            except BlockingIOError:
                yield False
                return
            try:
                yield True
            finally:
                fcntl.flock(guard.fileno(), fcntl.LOCK_UN)

    def stale_objects(self, before: datetime, limit: int = 1000) -> tuple[str, ...]:
        """Scan bounded regular originals/staging; callers must acquire a nonblocking per-key guard."""
        result = []
        with os.scandir(self.root) as entries:
            for entry in entries:
                if not re.fullmatch(r"[0-9a-f]{32}", entry.name) or not entry.is_file(
                    follow_symlinks=False
                ):
                    continue
                stat = entry.stat(follow_symlinks=False)
                if stat.st_mtime < before.timestamp():
                    result.append(entry.name)
                    if len(result) >= limit:
                        break
        return tuple(result)

    def path_for(self, key: str) -> Path:
        """Resolve only generated immutable keys; never follow symlinks or caller-supplied subpaths."""
        if not re.fullmatch(r"[0-9a-f]{32}", key):
            raise ApplicationError("not_found", "Resource not found.", 404)
        path = self.root / key
        if path.is_symlink() or path.resolve().parent != self.root:
            raise ApplicationError("not_found", "Resource not found.", 404)
        return path

    def stage(self, filename: str, media_type: str, chunks: Iterable[bytes]) -> Original:
        """Validate metadata and stream at most 20 MiB, then inspect format before database acceptance."""
        if (
            Path(filename).suffix.lower() not in MEDIA_TYPES
            or media_type not in MEDIA_TYPES.values()
        ):
            raise ApplicationError("unsupported_file_type", "Use PDF, DOCX, TXT, PNG or JPEG.", 415)
        try:
            FileMetadata(filename, 1, media_type)
        except ValueError:
            raise ApplicationError(
                "validation_failed", "Check filename and matching supported media type.", 422
            ) from None
        key = uuid4().hex
        target = self.path_for(key)
        digest = hashlib.sha256()
        size = 0
        created = False
        with self.protect(key):
            try:
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                created = True
                with os.fdopen(descriptor, "wb") as stream:
                    for chunk in chunks:
                        if not isinstance(chunk, bytes):
                            raise ValueError("Upload streams must contain bytes.")
                        size += len(chunk)
                        if size > MAX_FILE_BYTES:
                            raise ApplicationError(
                                "file_too_large", "Each file must be at most 20 MiB.", 413
                            )
                        stream.write(chunk)
                        digest.update(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                if size < 1:
                    raise ApplicationError(
                        "validation_failed", "Files must contain at least one byte.", 422
                    )
                self.inspector.inspect(target, media_type)
                target.chmod(0o400)
                return Original(key, filename, media_type, size, digest.hexdigest())
            except BaseException:
                if created:
                    target.unlink(missing_ok=True)
                raise

    def verify(self, original: Original) -> None:
        """Require immutable stored size/hash before extraction and again before ready publication."""
        target = self.path_for(original.storage_key)
        try:
            digest = hashlib.sha256()
            size = 0
            with target.open("rb") as stream:
                while chunk := stream.read(65536):
                    size += len(chunk)
                    if size > original.size_bytes:
                        raise ApplicationError(
                            "original_changed", "The original could not be verified.", 422
                        )
                    digest.update(chunk)
            if size != original.size_bytes or digest.hexdigest() != original.sha256:
                raise ApplicationError(
                    "original_changed", "The original could not be verified. Upload it again.", 422
                )
        except OSError:
            raise DependencyUnavailable() from None

    def remove(self, storage_key: str) -> None:
        """Remove only an owned unreferenced object; deletion never changes database availability."""
        self.path_for(storage_key).unlink(missing_ok=True)
