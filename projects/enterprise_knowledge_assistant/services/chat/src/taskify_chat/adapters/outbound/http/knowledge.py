"""Strict Knowledge HTTP consumer never turns outages into empty evidence or trusts supplied source URLs."""

import math
from datetime import datetime, timedelta
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx
import tiktoken
from pydantic import BaseModel, ConfigDict, ValidationError

from taskify_chat.application.ports.knowledge import (
    CitationKey,
    Evidence,
    SearchResult,
    SourceSnapshot,
    SourceStatus,
)
from taskify_chat.domain.errors import AuthenticationRequired, DependencyUnavailable
from taskify_chat.domain.locators import decode_locator, locator_dict


class DTO(BaseModel):
    """Require exact primitive types while tolerating compatible additive provider response fields."""

    model_config = ConfigDict(strict=True, extra="ignore", allow_inf_nan=False)


class EvidenceDTO(DTO):
    """Validate identifiers and primitives before semantic token/source checks."""

    chunk_id: UUID
    item_id: UUID
    revision_id: UUID
    title: str
    text: str
    locator: dict[str, Any]
    similarity: float


class SearchDTO(DTO):
    """Every successful search includes both nonempty active configuration versions."""

    pipeline_version: str
    retrieval_config_version: str
    candidates: list[EvidenceDTO]


class SourceDTO(DTO):
    """An unavailable reference has no private label, locator or resource link."""

    item_id: UUID
    revision_id: UUID
    chunk_id: UUID
    availability: Literal["current", "unavailable"]
    label: str | None
    locator: dict[str, Any] | None
    resource_url: str | None


class SnapshotDTO(DTO):
    """Source release depends on one exact complete fresh response, never a cached receipt."""

    validated_at: datetime
    all_current: bool
    sources: list[SourceDTO]


class KnowledgeHTTP:
    """Use a caller-scoped private service credential with bounded, nonredirecting HTTP and no caches."""

    def __init__(
        self,
        url: str,
        credential: str,
        *,
        allow_insecure: bool = False,
        client: httpx.Client | None = None,
    ) -> None:
        """Reject credential-bearing/malformed destinations before retaining the owned HTTP pool."""
        parsed = urlparse(url)
        if (
            not parsed.hostname
            or parsed.path not in ("", "/")
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (parsed.scheme != "https" and not (allow_insecure and parsed.scheme == "http"))
            or not credential
            or any(char.isspace() for char in credential)
        ):
            raise ValueError(
                "Knowledge requires a scoped credential and private TLS-capable origin."
            )
        self.url = url.rstrip("/")
        self.credential = credential
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(3.0, connect=1.0), follow_redirects=False
        )
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def post(self, path: str, payload: dict[str, object], request_id: UUID) -> bytes:
        """Distinguish invalid accepting login from dependency/schema/service-scope failure."""
        try:
            response = self.client.post(
                self.url + path,
                json=payload,
                headers={
                    "Authorization": "Bearer " + self.credential,
                    "X-Request-ID": str(request_id),
                },
            )
        except httpx.HTTPError:
            raise DependencyUnavailable() from None
        if response.status_code == 401:
            raise AuthenticationRequired()
        if response.status_code != 200 or len(response.content) > 2 * 1024 * 1024:
            raise DependencyUnavailable()
        return response.content

    def search(self, login_session_id: UUID, query: str, request_id: UUID) -> SearchResult:
        """Revalidate up to 20 current chunks and deduplicate to eight for bounded generation/release."""
        if not 1 <= len(query.strip()) <= 4000:
            raise ValueError("Standalone queries must contain 1–4000 characters.")
        raw = self.post(
            "/internal/v1/retrieval/search",
            {
                "login_session_id": str(login_session_id),
                "query": query,
                "request_id": str(request_id),
            },
            request_id,
        )
        try:
            dto = SearchDTO.model_validate_json(raw)
            if (
                any(
                    not value or len(value) > 300
                    for value in (dto.pipeline_version, dto.retrieval_config_version)
                )
                or len(dto.candidates) > 20
            ):
                raise ValueError()
            unique: dict[UUID, Evidence] = {}
            for entry in dto.candidates:
                if (
                    not entry.title.strip()
                    or len(entry.title) > 200
                    or not entry.text.strip()
                    or len(self.encoding.encode(entry.text, disallowed_special=())) > 800
                    or not math.isfinite(entry.similarity)
                    or not -1.00001 <= entry.similarity <= 1.00001
                ):
                    raise ValueError()
                evidence = Evidence(
                    entry.chunk_id,
                    entry.item_id,
                    entry.revision_id,
                    entry.title,
                    entry.text,
                    locator_dict(decode_locator(entry.locator)),
                    entry.similarity,
                )
                if entry.chunk_id in unique and unique[entry.chunk_id] != evidence:
                    raise ValueError()
                unique[entry.chunk_id] = evidence
            return SearchResult(
                dto.pipeline_version, dto.retrieval_config_version, tuple(unique.values())[:8]
            )
        except (ValidationError, TypeError, ValueError):
            raise DependencyUnavailable() from None

    def validate(
        self,
        login_session_id: UUID,
        citations: tuple[CitationKey, ...],
        purpose: Literal["release", "history"],
        request_id: UUID,
    ) -> SourceSnapshot:
        """Require an exact one-to-one batch and server-built current source paths matching requested triples."""
        if (
            purpose not in ("release", "history")
            or len(citations) > (8 if purpose == "release" else 100)
            or len(set(citations)) != len(citations)
        ):
            raise ValueError("Invalid citation validation batch.")
        raw = self.post(
            "/internal/v1/sources/validate",
            {
                "login_session_id": str(login_session_id),
                "purpose": purpose,
                "citations": [
                    {
                        "item_id": str(key.item_id),
                        "revision_id": str(key.revision_id),
                        "chunk_id": str(key.chunk_id),
                    }
                    for key in citations
                ],
            },
            request_id,
        )
        try:
            dto = SnapshotDTO.model_validate_json(raw)
            if (
                dto.validated_at.tzinfo is None
                or dto.validated_at.utcoffset() != timedelta(0)
                or len(dto.sources) != len(citations)
            ):
                raise ValueError()
            sources = []
            seen = set()
            for entry in dto.sources:
                key = CitationKey(entry.item_id, entry.revision_id, entry.chunk_id)
                if key not in citations or key in seen:
                    raise ValueError()
                seen.add(key)
                locator = None
                if entry.availability == "current":
                    if (
                        not entry.label
                        or len(entry.label) > 200
                        or entry.locator is None
                        or entry.resource_url is None
                    ):
                        raise ValueError()
                    locator = locator_dict(decode_locator(entry.locator))
                    parsed = urlparse(entry.resource_url)
                    if (
                        parsed.scheme
                        or parsed.netloc
                        or parsed.path != f"/api/v1/knowledge/{key.item_id}/source"
                        or parse_qs(parsed.query) != {"revision_id": [str(key.revision_id)]}
                    ):
                        raise ValueError()
                    if parsed.fragment and (
                        locator.get("kind") != "pdf" or parsed.fragment != f"page={locator['page']}"
                    ):
                        raise ValueError()
                elif (
                    entry.label is not None
                    or entry.locator is not None
                    or entry.resource_url is not None
                ):
                    raise ValueError()
                sources.append(
                    SourceStatus(key, entry.availability, entry.label, locator, entry.resource_url)
                )
            if dto.all_current != all(entry.availability == "current" for entry in sources):
                raise ValueError()
            return SourceSnapshot(dto.validated_at, dto.all_current, tuple(sources))
        except (ValidationError, TypeError, ValueError, AttributeError):
            raise DependencyUnavailable() from None
