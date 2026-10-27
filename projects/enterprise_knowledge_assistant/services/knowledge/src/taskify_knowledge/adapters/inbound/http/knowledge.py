"""Public Knowledge routes authenticate before parsing multipart content and never trust actor headers."""

from collections.abc import Iterator
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from taskify_knowledge.adapters.inbound.http.common import origin_guard, request_id
from taskify_knowledge.adapters.outbound.settings import Settings
from taskify_knowledge.application.ports.identity import Principal, SessionRequest, SessionValidator
from taskify_knowledge.application.ports.knowledge_store import ItemView
from taskify_knowledge.application.read_knowledge import listing, read, revision_status
from taskify_knowledge.application.service import KnowledgeService, allowed
from taskify_knowledge.application.upload import upload
from taskify_knowledge.domain.errors import ApplicationError, AuthenticationRequired
from taskify_knowledge.domain.revision import ERROR_MESSAGES, KnowledgeRevision
from taskify_knowledge.domain.values import MEDIA_TYPES, Pagination


def revision_body(revision: KnowledgeRevision | None) -> dict[str, object] | None:
    """Serialize exact public revision fields without company, private key/hash or parser diagnostics."""
    if revision is None:
        return None
    return {
        "id": str(revision.id),
        "item_id": str(revision.item_id),
        "original_filename": revision.original_filename,
        "media_type": revision.media_type,
        "size_bytes": revision.size_bytes,
        "state": revision.state,
        "error_code": revision.error_code,
        "error_message": ERROR_MESSAGES.get(revision.error_code) if revision.error_code else None,
        "created_at": revision.created_at.isoformat(),
        "ready_at": revision.ready_at.isoformat() if revision.ready_at else None,
    }


def item_body(view: ItemView) -> dict[str, object]:
    """Serialize current/candidate availability; original bytes and ownership stay on their service."""
    item = view.item
    return {
        "id": str(item.id),
        "title": item.title,
        "version": item.version,
        "availability": view.availability,
        "current_revision": revision_body(view.current_revision),
        "candidate_revision": revision_body(view.candidate_revision),
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def actor(
    request: Request,
    settings: Settings,
    identity: SessionValidator,
    *,
    mutation: bool = False,
    poll: bool = False,
) -> Principal:
    """Select fixed handler activity and resolve cookie authority online with no positive cache."""
    if mutation:
        origin_guard(request, settings.public_origin)
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise AuthenticationRequired()
    csrf = request.headers.get("x-csrf-token")
    if mutation and not csrf:
        raise ApplicationError("csrf_failed", "Refresh the session and retry.", 403)
    try:
        selection = SessionRequest(
            session_token=token,
            csrf_token=csrf,
            require_csrf=mutation,
            require_password_changed=True,
            activity="poll" if poll else "user_activity",
        )
    except ValueError:
        raise AuthenticationRequired() from None
    return identity.resolve(selection, request_id(request))


def query_fields(request: Request, permitted: set[str]) -> None:
    """Reject undeclared/duplicate query fields rather than treating a company selector as authority."""
    if any(
        key not in permitted or len(request.query_params.getlist(key)) != 1
        for key in request.query_params
    ):
        raise ApplicationError("invalid_request", "Check the documented query fields.", 400)


def pages(request: Request) -> Pagination:
    """Parse only bounded integer page sizes and bounded owner-scoped opaque cursors."""
    query_fields(request, {"limit", "cursor"})
    raw = request.query_params.get("limit", "50")
    try:
        if not raw.isascii() or not raw.isdigit() or len(raw) > 3:
            raise ValueError("Invalid limit.")
        return Pagination(int(raw), request.query_params.get("cursor"))
    except ValueError:
        raise ApplicationError(
            "validation_failed", "Use limit 1–100 and a valid bounded page cursor.", 422
        ) from None


def file_chunks(file: UploadFile) -> Iterator[bytes]:
    """Yield bounded upload blocks; the storage adapter enforces the total 20-MiB counter."""
    while chunk := file.file.read(65536):
        yield chunk


def knowledge_router(
    service: KnowledgeService, identity: SessionValidator, settings: Settings
) -> APIRouter:
    """Expose authenticated company reads and admin upload/status under the committed public paths."""
    router = APIRouter(prefix="/api/v1/knowledge")

    @router.get("")
    def list_items(request: Request) -> dict[str, object]:
        """List visible current-company items after online user-triggered authentication."""
        principal = actor(request, settings, identity)
        page = listing(service, principal, pages(request))
        return {
            "items": [item_body(value) for value in page.items],
            "next_cursor": page.next_cursor,
        }

    @router.post("", status_code=202)
    async def upload_item(request: Request) -> JSONResponse:
        """Authenticate admin/Origin/CSRF before multipart parsing and bounded private staging."""
        principal = await run_in_threadpool(actor, request, settings, identity, mutation=True)
        allowed(principal, admin=True)
        async with request.form(max_files=2, max_fields=8, max_part_size=1024) as form:
            if set(form) != {"title", "file"} or any(len(form.getlist(key)) != 1 for key in form):
                raise ApplicationError(
                    "invalid_request", "Supply exactly one title and one file.", 400
                )
            title, file = form["title"], form["file"]
            if not isinstance(title, str) or not isinstance(file, UploadFile) or not file.filename:
                raise ApplicationError(
                    "validation_failed", "Supply a title and a named supported file.", 422
                )
            from pathlib import Path

            media = file.content_type or MEDIA_TYPES.get(Path(file.filename).suffix.lower(), "")
            if media == "application/octet-stream":
                media = MEDIA_TYPES.get(Path(file.filename).suffix.lower(), "")
            view = await run_in_threadpool(
                upload,
                service,
                principal,
                title,
                file.filename,
                media,
                file_chunks(file),
                reauthorize=lambda: actor(request, settings, identity, mutation=True),
            )
        return JSONResponse(
            item_body(view), status_code=202, headers={"ETag": f'"{view.item.version}"'}
        )

    @router.get("/{item_id}")
    def get_item(item_id: UUID, request: Request) -> JSONResponse:
        """Read an exact owned item; conservative metadata polling never extends idle login time."""
        query_fields(request, set())
        view = read(service, actor(request, settings, identity, poll=True), item_id)
        return JSONResponse(item_body(view), headers={"ETag": f'"{view.item.version}"'})

    @router.get("/{item_id}/revisions/{revision_id}")
    def get_revision(
        item_id: UUID, revision_id: UUID, request: Request
    ) -> dict[str, object] | None:
        """Poll only the owning company's admin processing status without idle refresh."""
        query_fields(request, set())
        return revision_body(
            revision_status(
                service, actor(request, settings, identity, poll=True), item_id, revision_id
            )
        )

    return router
