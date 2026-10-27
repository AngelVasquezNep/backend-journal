"""Admin title/replacement/removal HTTP requires Origin, CSRF and an exact quoted current item version."""

import re
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BeforeValidator, Field
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from taskify_knowledge.adapters.inbound.http.common import StrictDTO, json_guard
from taskify_knowledge.adapters.inbound.http.knowledge import (
    actor,
    file_chunks,
    item_body,
    query_fields,
)
from taskify_knowledge.adapters.outbound.settings import Settings
from taskify_knowledge.application.maintain_knowledge import remove, rename, replace_original
from taskify_knowledge.application.ports.identity import SessionValidator
from taskify_knowledge.application.service import KnowledgeService, allowed
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.values import MEDIA_TYPES, Title


def canonical_title(value: object) -> object:
    """Check the title's post-trim length before DTO limits while retaining raw control-character rejection."""
    return Title(value).value if isinstance(value, str) else value


class RenameInput(StrictDTO):
    """A title edit accepts only a bounded title; version and ownership cannot be body overrides."""

    title: Annotated[str, BeforeValidator(canonical_title), Field(min_length=1, max_length=200)]


def expected_version(request: Request) -> int:
    """Require one quoted positive decimal If-Match, rejecting wildcard/list/weak/unquoted forms."""
    values = request.headers.getlist("if-match")
    if len(values) != 1 or not re.fullmatch(r'"[1-9][0-9]{0,18}"', values[0]):
        raise ApplicationError(
            "validation_failed", "Supply the quoted current item ETag in If-Match.", 422
        )
    return int(values[0][1:-1])


def maintenance_router(
    service: KnowledgeService, identity: SessionValidator, settings: Settings
) -> APIRouter:
    """Expose explicit admin mutations; normal user resource screens remain read-only."""
    router = APIRouter(prefix="/api/v1/knowledge")

    @router.patch("/{item_id}")
    def patch_title(item_id: UUID, body: RenameInput, request: Request) -> JSONResponse:
        """Rename with locked CAS and return the new positive version/ETag without losing candidates."""
        query_fields(request, set())
        principal = actor(request, settings, identity, mutation=True)
        json_guard(request)
        view = rename(service, principal, item_id, expected_version(request), body.title)
        return JSONResponse(item_body(view), headers={"ETag": f'"{view.item.version}"'})

    @router.post("/{item_id}/revisions", status_code=202)
    async def replacement(item_id: UUID, request: Request) -> JSONResponse:
        """Authorize before multipart parsing, then stage and atomically accept one replacement candidate."""
        query_fields(request, set())
        principal = await run_in_threadpool(actor, request, settings, identity, mutation=True)
        allowed(principal, admin=True)
        expected = expected_version(request)
        async with request.form(max_files=2, max_fields=2, max_part_size=1024) as form:
            if set(form) != {"file"} or len(form.getlist("file")) != 1:
                raise ApplicationError(
                    "invalid_request", "Supply exactly one replacement file.", 400
                )
            file = form["file"]
            if not isinstance(file, UploadFile) or not file.filename:
                raise ApplicationError("validation_failed", "Supply a named supported file.", 422)
            media = file.content_type or MEDIA_TYPES.get(Path(file.filename).suffix.lower(), "")
            if media == "application/octet-stream":
                media = MEDIA_TYPES.get(Path(file.filename).suffix.lower(), "")
            view = await run_in_threadpool(
                replace_original,
                service,
                principal,
                item_id,
                expected,
                file.filename,
                media,
                file_chunks(file),
                reauthorize=lambda: actor(request, settings, identity, mutation=True),
            )
        return JSONResponse(
            item_body(view), status_code=202, headers={"ETag": f'"{view.item.version}"'}
        )

    @router.delete("/{item_id}", status_code=204)
    def delete(item_id: UUID, request: Request) -> Response:
        """Immediately remove current visibility and cancel a pending candidate under exact CAS."""
        query_fields(request, set())
        principal = actor(request, settings, identity, mutation=True)
        remove(service, principal, item_id, expected_version(request))
        return Response(status_code=204)

    return router
