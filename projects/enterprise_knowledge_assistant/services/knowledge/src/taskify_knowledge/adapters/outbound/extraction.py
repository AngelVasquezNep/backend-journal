"""Bounded subprocess parser/OCR adapter; private diagnostics and provider credentials stay outside it."""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from taskify_knowledge.application.ports.storage import Original
from taskify_knowledge.domain.block import ExtractedText
from taskify_knowledge.domain.errors import ApplicationError, DependencyUnavailable
from taskify_knowledge.domain.locators import decode_locator
from taskify_knowledge.domain.revision import ERROR_MESSAGES
from taskify_knowledge.domain.values import MEDIA_TYPES, FileMetadata


class LocalExtractor:
    """Extract only local validated originals under a 90-second/512-MiB subprocess budget."""

    def __init__(self, root: Path, languages: str = "eng+spa") -> None:
        """Retain private storage root and explicitly configured installed OCR language packs."""
        if not re.fullmatch(r"[a-z_]+(?:\+[a-z_]+)*", languages) or len(languages) > 64:
            raise ValueError("OCR languages must name installed local Tesseract packs.")
        self.root = root.resolve()
        self.languages = languages

    def validate_runtime(self) -> None:
        """Check required local OCR packs nonbillably before an API/worker accepts processing work."""
        if sys.platform != "linux":
            raise ValueError("Run resource-isolated Knowledge processing in its Linux container.")
        binary = shutil.which("tesseract")
        if binary is None:
            raise DependencyUnavailable()
        response = subprocess.run(
            [binary, "--list-langs"], capture_output=True, text=True, timeout=5, check=False
        )
        if response.returncode or not set(self.languages.split("+")) <= set(
            response.stdout.splitlines()
        ):
            raise DependencyUnavailable()

    def extract(self, original: Original) -> tuple[ExtractedText, ...]:
        """Resolve a server-owned immutable storage key; user-controlled paths/URLs are forbidden."""
        if not re.fullmatch(r"[0-9a-f]{32}", original.storage_key):
            raise ApplicationError("validation_failed", "Invalid private object identity.", 422)
        path = self.root / original.storage_key
        if path.is_symlink() or path.resolve().parent != self.root:
            raise ApplicationError("validation_failed", "Invalid private object identity.", 422)
        return self.extract_path(path, original.media_type)

    def extract_path(self, path: Path, media_type: str | None = None) -> tuple[ExtractedText, ...]:
        """Extract a local adapter/test file with explicit or filename-derived supported format."""
        media = media_type or MEDIA_TYPES.get(path.suffix.lower())
        if media is None:
            raise ApplicationError("unsupported_file_type", "Use PDF, DOCX, TXT, PNG or JPEG.", 415)
        data = self.run(path, media, False)
        try:
            return tuple(
                ExtractedText(
                    ordinal=part["ordinal"],
                    normalized_text=part["normalized_text"],
                    locator=decode_locator(part["locator"]),
                    source_offset_map=tuple(part["source_offset_map"]),
                    extractor_version=part["extractor_version"],
                )
                for part in data["blocks"]
            )
        except (KeyError, ValueError, TypeError):
            raise ApplicationError("corrupt_file", ERROR_MESSAGES["corrupt_file"], 422) from None

    def inspect(self, path: Path, media_type: str) -> None:
        """Validate structural format/encoding safely before durable upload acceptance, without OCR."""
        self.run(path, media_type, True)

    def run(self, path: Path, media_type: str, inspect_only: bool) -> dict[str, Any]:
        """Run a fresh isolated parser with a minimal secret-free environment; kill its process group on timeout."""
        try:
            size = path.stat().st_size
            suffix = next(
                extension for extension, mime in MEDIA_TYPES.items() if mime == media_type
            )
            FileMetadata("original" + suffix, size, media_type)
        except OSError:
            raise DependencyUnavailable() from None
        except ValueError:
            raise ApplicationError(
                "validation_failed", "File size must be 1–20,971,520 bytes.", 422
            ) from None
        request = json.dumps(
            {
                "path": str(path),
                "media_type": media_type,
                "languages": self.languages,
                "inspect_only": inspect_only,
            }
        ).encode()
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "LANG": "C.UTF-8",
            "OMP_THREAD_LIMIT": "1",
            "PYTHONIOENCODING": "utf-8",
        }
        # Bounded file-backed IPC avoids buffering attacker-amplified parser output in API memory.
        with tempfile.TemporaryFile() as channel:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "taskify_knowledge.adapters.outbound.extraction_child",
                ],
                stdin=subprocess.PIPE,
                stdout=channel,
                stderr=subprocess.DEVNULL,
                env=environment,
                start_new_session=True,
            )
            try:
                process.communicate(request, timeout=90)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise ApplicationError(
                    "resource_limit", ERROR_MESSAGES["resource_limit"], 422
                ) from None
            if process.returncode or channel.tell() > 32 * 1024 * 1024:
                raise ApplicationError("resource_limit", ERROR_MESSAGES["resource_limit"], 422)
            channel.seek(0)
            output = channel.read(32 * 1024 * 1024 + 1)
            if len(output) > 32 * 1024 * 1024:
                raise ApplicationError("resource_limit", ERROR_MESSAGES["resource_limit"], 422)
        try:
            data: dict[str, Any] = json.loads(output)
        except (ValueError, TypeError):
            raise ApplicationError("corrupt_file", ERROR_MESSAGES["corrupt_file"], 422) from None
        if code := data.get("error"):
            if code == "storage_unavailable":
                raise DependencyUnavailable()
            safe_code = code if code in ERROR_MESSAGES else "corrupt_file"
            raise ApplicationError(safe_code, ERROR_MESSAGES[safe_code], 422)
        return data
