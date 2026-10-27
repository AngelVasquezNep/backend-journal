"""Host acceptance client uses only contracted public flows and private memory-only first-party sessions."""

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx


class PublicFlowError(RuntimeError):
    """Expose a redacted operation/status failure without credentials, documents or request bodies."""


def private_json(path: Path) -> dict:
    """Read credentials/evidence only from an owner-private file; never evaluate shell or print its contents."""
    if path.stat().st_mode & 0o077:
        raise PublicFlowError("Private configuration must have permissions 0600.")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise PublicFlowError("Private configuration must be an object.")
    return value


def save_private(path: Path, value: dict, *, exclusive: bool = False) -> None:
    """Write private fixture/evaluation output with restricted permissions and explicit overwrite policy."""
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


class PublicClient:
    """Own one acceptance actor's cookie jar and memory-only synchronizer; never share it between accounts."""

    def __init__(self, origin: str) -> None:
        """Require a configured origin, TLS outside loopback, and bounded nonredirecting requests."""
        parsed = urlparse(origin)
        if (
            parsed.scheme not in ("https", "http")
            or not parsed.hostname
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or (
                parsed.scheme == "http"
                and parsed.hostname not in ("localhost", "127.0.0.1", "::1")
            )
        ):
            raise PublicFlowError(
                "Use a first-party HTTPS origin or explicit loopback development origin."
            )
        self.origin = origin
        self.client = httpx.Client(base_url=origin, follow_redirects=False, timeout=15)
        self.csrf = None

    def request(
        self, method: str, path: str, *, expected: tuple[int, ...] = (200,), **kwargs
    ):
        """Send a contracted same-origin request with safe status-only errors and no secret logging."""
        if not path.startswith("/api/v1/") or path.startswith("//"):
            raise PublicFlowError(
                "Only relative first-party public API paths are permitted."
            )
        headers = dict(kwargs.pop("headers", {}))
        if method not in ("GET", "HEAD"):
            headers["Origin"] = self.origin
            if self.csrf:
                headers["X-CSRF-Token"] = self.csrf
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code not in expected:
            raise PublicFlowError(
                f"Public operation failed with HTTP {response.status_code}."
            )
        return response

    def login(self, email: str, password: str, replacement: str | None = None) -> dict:
        """Complete first-party login and an optional required initial-password change through public HTTP."""
        session = self.request(
            "POST", "/api/v1/auth/login", json={"email": email, "password": password}
        ).json()
        self.csrf = session["csrf_token"]
        if session["account"]["must_change_password"]:
            if replacement is None:
                raise PublicFlowError(
                    "A private replacement password is required for the first login."
                )
            session = self.request(
                "PUT",
                "/api/v1/auth/password",
                json={"current_password": password, "new_password": replacement},
            ).json()
            self.csrf = session["csrf_token"]
        return session["account"]

    def upload(
        self, title: str, path: Path, *, allow_failed: bool = False
    ) -> tuple[dict, float]:
        """Time acceptance through visible readiness, including extraction/OCR/embedding/queue work."""
        import mimetypes

        started = time.monotonic()
        media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        with path.open("rb") as stream:
            accepted = self.request(
                "POST",
                "/api/v1/knowledge",
                expected=(202,),
                data={"title": title},
                files={"file": (path.name, stream, media)},
            ).json()
        deadline = started + 180
        while time.monotonic() < deadline:
            item = self.request("GET", "/api/v1/knowledge/" + accepted["id"]).json()
            if item["availability"] == "ready":
                return item, time.monotonic() - started
            candidate = item.get("candidate_revision")
            if candidate and candidate["state"] == "failed":
                if allow_failed:
                    return item, time.monotonic() - started
                raise PublicFlowError("A representative document failed processing.")
            time.sleep(0.5)
        raise PublicFlowError(
            "Representative ingestion exceeded the observation deadline."
        )

    def conversation(self) -> dict:
        """Open/reuse only this account's one saved private conversation."""
        return self.request("PUT", "/api/v1/chat", json={}).json()

    def question(
        self, content: str, *, expected_sequence: int | None = None, barrier=None
    ) -> tuple[dict, float]:
        """Measure submit-to-terminal-display-equivalent time including queue and one-second polls."""
        sequence = (
            self.conversation()["last_sequence"]
            if expected_sequence is None
            else expected_sequence
        )
        if barrier:
            barrier.wait(timeout=30)
        started = time.monotonic()
        turn = self.request(
            "POST",
            "/api/v1/chat/messages",
            expected=(200, 202),
            json={
                "client_message_id": str(uuid4()),
                "content": content,
                "expected_last_sequence": sequence,
            },
        ).json()
        if not re.fullmatch(r"/api/v1/chat/turns/[0-9a-f-]{36}", turn["poll_url"]):
            raise PublicFlowError("Invalid server turn route.")
        while turn["state"] in ("queued", "running"):
            if time.monotonic() - started > 90:
                raise PublicFlowError("Answer observation exceeded its deadline.")
            time.sleep(1)
            turn = self.request("GET", turn["poll_url"]).json()
        if turn["assistant_message"] is None:
            raise PublicFlowError("Terminal turn has no committed result.")
        return turn, time.monotonic() - started

    def verify_source(self, citation: dict, originals: dict) -> None:
        """Read exact current source bytes through public auth and compare the provisioned original digest."""
        path = citation.get("resource_url")
        if (
            citation.get("availability") != "current"
            or not isinstance(path, str)
            or not re.fullmatch(
                r"/api/v1/knowledge/[0-9a-f-]{36}/source\?revision_id=[0-9a-f-]{36}(?:#page=[1-9][0-9]*)?",
                path,
            )
        ):
            raise PublicFlowError("A factual citation is unavailable or malformed.")
        item = originals.get(citation["item_id"])
        if not item or citation["revision_id"] != item["revision_id"]:
            raise PublicFlowError(
                "A citation belongs to an unknown or foreign original."
            )
        response = self.request("GET", path.split("#", 1)[0])
        if hashlib.sha256(response.content).hexdigest() != item["sha256"]:
            raise PublicFlowError("The cited original identity changed.")

    def close(self) -> None:
        """Discard cookies/CSRF and release the host-owned HTTP pool without writing browser storage."""
        self.csrf = None
        self.client.close()
