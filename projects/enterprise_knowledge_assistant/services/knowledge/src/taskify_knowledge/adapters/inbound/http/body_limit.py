"""Limit the entire upload envelope before multipart spooling; file bytes remain capped at 20 MiB."""

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from taskify_knowledge.adapters.inbound.http.common import safe_error
from taskify_knowledge.domain.errors import ApplicationError

MAX_ENVELOPE_BYTES = 21 * 1024 * 1024


class BodyLimit:
    """Bound chunked and declared multipart request bodies even when bypassing the public ingress."""

    def __init__(self, app: ASGIApp) -> None:
        """Retain the inner ASGI app; no request body or private state is cached."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject oversized declared bodies early and count streamed bytes before parser allocation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        raw = dict(scope.get("headers", [])).get(b"content-length", b"0")
        if len(raw) > 10 or (raw.isdigit() and int(raw) > MAX_ENVELOPE_BYTES):
            response = safe_error(
                Request(scope), "file_too_large", "Each file must be at most 20 MiB.", 413
            )
            await response(scope, receive, send)
            return
        count = 0

        async def limited() -> Message:
            """Count only body messages and reject over-limit streams without retaining their content."""
            nonlocal count
            message = await receive()
            if message["type"] == "http.request":
                count += len(message.get("body", b""))
                if count > MAX_ENVELOPE_BYTES:
                    raise ApplicationError(
                        "file_too_large", "Each file must be at most 20 MiB.", 413
                    )
            return message

        await self.app(scope, limited, send)
