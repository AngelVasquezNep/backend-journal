"""Application-owned final source checks use one fresh atomic batch snapshot per request."""

from typing import Literal

from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.application.ports.retrieval import EvidenceKey, SourceBatch, VectorSearch
from taskify_knowledge.application.service import KnowledgeService, allowed
from taskify_knowledge.domain.errors import ApplicationError


def validate_sources(
    service: KnowledgeService,
    search: VectorSearch,
    actor: Principal,
    keys: tuple[EvidenceKey, ...],
    purpose: Literal["release", "history"],
) -> SourceBatch:
    """Require unique bounded triples; unavailable/foreign evidence has no distinguishing private metadata."""
    allowed(actor)
    if (
        purpose not in ("release", "history")
        or len(keys) > (8 if purpose == "release" else 100)
        or len(set(keys)) != len(keys)
    ):
        raise ApplicationError(
            "validation_failed", "Supply bounded unique exact citation references.", 422
        )
    return SourceBatch(service.clock.now(), search.validate(actor.company_id, keys))
