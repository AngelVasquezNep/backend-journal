"""Internal service-scoped retrieval validates accepted sessions online and never accepts tenant claims."""

import hmac
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BeforeValidator, Field

from taskify_knowledge.adapters.inbound.http.common import StrictDTO, request_id
from taskify_knowledge.adapters.outbound.settings import Settings
from taskify_knowledge.application.ports.identity import SessionRequest, SessionValidator
from taskify_knowledge.application.ports.retrieval import EvidenceKey, VectorSearch
from taskify_knowledge.application.retrieve import retrieve
from taskify_knowledge.application.service import KnowledgeService
from taskify_knowledge.application.validate_sources import validate_sources
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.locators import locator_dict


def parse_uuid(value: object) -> UUID:
    """Parse only string UUIDs at the JSON boundary without broad Pydantic coercion."""
    if not isinstance(value, (str, UUID)):
        raise ValueError("A UUID is required.")
    return UUID(value) if isinstance(value, str) else value


JsonUUID = Annotated[UUID, BeforeValidator(parse_uuid)]


class SearchInput(StrictDTO):
    """The worker supplies an accepted session and bounded question, never company/model/version selectors."""

    login_session_id: JsonUUID
    query: Annotated[str, Field(min_length=1, max_length=4000)]
    request_id: JsonUUID


class CitationInput(StrictDTO):
    """A reference is exactly three UUIDs; locators/labels/URLs cannot become authority."""

    item_id: JsonUUID
    revision_id: JsonUUID
    chunk_id: JsonUUID


class ValidateInput(StrictDTO):
    """History and release limits are selected by receiving policy, with release restricted to workers."""

    login_session_id: JsonUUID
    citations: Annotated[list[CitationInput], Field(max_length=100)]
    purpose: Literal["release", "history"]


def retrieval_router(
    service: KnowledgeService, search: VectorSearch, identity: SessionValidator, settings: Settings
) -> APIRouter:
    """Bind caller-specific worker/API scopes on routes excluded from public ingress."""
    router = APIRouter(prefix="/internal/v1")
    credentials = dict(settings.internal_credentials)

    def authorize(request: Request, worker_only: bool) -> None:
        """Constant-time service authentication precedes all user authority resolution and provider work."""
        supplied = request.headers.get("authorization", "")
        matched = next(
            (
                name
                for name, secret in credentials.items()
                if secret
                and supplied.isascii()
                and hmac.compare_digest(supplied, "Bearer " + secret)
            ),
            None,
        )
        if matched is None:
            raise ApplicationError(
                "authentication_required", "Service authentication is required.", 401
            )
        if worker_only and matched != "CHAT_WORKER_CREDENTIAL":
            raise ApplicationError("forbidden", "This service scope is not permitted.", 403)

    @router.post("/retrieval/search")
    def search_current(body: SearchInput, request: Request) -> dict[str, object]:
        """Search only a currently valid accepting session's company with the active pipeline."""
        authorize(request, True)
        actor = identity.resolve(
            SessionRequest(login_session_id=body.login_session_id, activity="background"),
            request_id(request),
        )
        page = retrieve(service, search, actor, body.query)
        return {
            "pipeline_version": page.pipeline_version,
            "retrieval_config_version": page.retrieval_config_version,
            "candidates": [
                {
                    "chunk_id": str(chunk.key.chunk_id),
                    "item_id": str(chunk.key.item_id),
                    "revision_id": str(chunk.key.revision_id),
                    "title": chunk.title,
                    "text": chunk.text,
                    "locator": locator_dict(chunk.locator),
                    "similarity": chunk.similarity,
                }
                for chunk in page.candidates
            ],
        }

    @router.post("/sources/validate")
    def sources(body: ValidateInput, request: Request) -> dict[str, object]:
        """Resolve each exact triple in one atomic snapshot; never disclose unavailable foreign metadata."""
        authorize(request, body.purpose == "release")
        actor = identity.resolve(
            SessionRequest(login_session_id=body.login_session_id, activity="background"),
            request_id(request),
        )
        keys = tuple(
            EvidenceKey(value.item_id, value.revision_id, value.chunk_id)
            for value in body.citations
        )
        snapshot = validate_sources(service, search, actor, keys, body.purpose)
        return {
            "validated_at": snapshot.validated_at.isoformat(),
            "all_current": all(source.resource_url is not None for source in snapshot.sources),
            "sources": [
                {
                    "item_id": str(source.key.item_id),
                    "revision_id": str(source.key.revision_id),
                    "chunk_id": str(source.key.chunk_id),
                    "availability": "current" if source.resource_url else "unavailable",
                    "label": source.title,
                    "locator": locator_dict(source.locator) if source.locator else None,
                    "resource_url": source.resource_url,
                }
                for source in snapshot.sources
            ],
        }

    return router
