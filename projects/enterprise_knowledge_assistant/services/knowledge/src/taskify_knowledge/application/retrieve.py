"""Fresh trusted-session evidence retrieval uses the current active Knowledge vector space."""

from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.application.ports.retrieval import SearchPage, VectorSearch
from taskify_knowledge.application.service import KnowledgeService, allowed
from taskify_knowledge.domain.errors import ApplicationError, DependencyUnavailable

RETRIEVAL_VERSION = "exact-cosine-top20-v1"


def retrieve(
    service: KnowledgeService, search: VectorSearch, actor: Principal, query: str
) -> SearchPage:
    """Validate standalone query and return active configuration metadata even for no evidence."""
    allowed(actor)
    if not isinstance(query, str) or not 1 <= len(query.strip()) <= 4000:
        raise ApplicationError("validation_failed", "Queries must contain 1–4000 characters.", 422)
    vectors = service.embedder.embed((query.strip(),))
    if len(vectors) != 1:
        raise DependencyUnavailable()
    return SearchPage(
        service.pipeline.version,
        service.pipeline.version + ":" + RETRIEVAL_VERSION,
        search.search(actor.company_id, vectors[0], service.pipeline.version),
    )
