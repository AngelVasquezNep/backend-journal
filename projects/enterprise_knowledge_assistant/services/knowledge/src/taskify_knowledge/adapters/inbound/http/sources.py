"""Originals stream only after online login/company/exact-current-revision authorization."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from taskify_knowledge.adapters.inbound.http.knowledge import actor, query_fields
from taskify_knowledge.adapters.outbound.filesystem import FilesystemStorage
from taskify_knowledge.adapters.outbound.settings import Settings
from taskify_knowledge.application.ports.identity import SessionValidator
from taskify_knowledge.application.read_knowledge import source
from taskify_knowledge.application.service import KnowledgeService
from taskify_knowledge.domain.errors import DependencyUnavailable


def source_router(
    service: KnowledgeService, identity: SessionValidator, settings: Settings
) -> APIRouter:
    """Expose no permanent public URL or storage key; every source open revalidates availability."""
    router = APIRouter(prefix="/api/v1/knowledge")

    @router.get("/{item_id}/source")
    def get_source(
        item_id: UUID,
        revision_id: UUID,
        request: Request,
        download: Literal["true", "false"] = "false",
    ) -> FileResponse:
        """Serve only verified current bytes; active content is downloaded with nosniff and sandbox policy."""
        query_fields(request, {"revision_id", "download"})
        original = source(service, actor(request, settings, identity), item_id, revision_id)
        storage = service.storage
        if not isinstance(storage, FilesystemStorage):
            raise DependencyUnavailable()
        inline = (
            original.media_type in ("application/pdf", "image/png", "image/jpeg")
            and download == "false"
        )
        return FileResponse(
            storage.path_for(original.storage_key),
            media_type=original.media_type,
            filename=original.original_filename,
            content_disposition_type="inline" if inline else "attachment",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'self'",
            },
        )

    return router
