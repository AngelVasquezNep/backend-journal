"""Knowledge application dependencies are owned ports, not framework/ORM/provider objects."""

from collections.abc import Callable
from dataclasses import dataclass

from taskify_knowledge.application.ports.clock import Clock, IdGenerator
from taskify_knowledge.application.ports.extraction import Chunker, Embedder, TextExtractor
from taskify_knowledge.application.ports.identity import Principal
from taskify_knowledge.application.ports.knowledge_store import KnowledgeStore
from taskify_knowledge.application.ports.storage import ObjectStorage
from taskify_knowledge.domain.errors import ApplicationError
from taskify_knowledge.domain.pipeline import PipelineConfiguration


@dataclass
class KnowledgeService:
    """Compose application ports without reading environment, transport or database state directly."""

    store: KnowledgeStore
    storage: ObjectStorage
    extractor: TextExtractor
    chunker: Chunker
    embedder: Embedder
    pipeline: PipelineConfiguration
    clock: Clock
    ids: IdGenerator
    retry_jitter: Callable[[], float]


def allowed(actor: Principal, *, admin: bool = False) -> None:
    """Require a changed password and, for mutations, the authenticated admin role."""
    if actor.must_change_password:
        raise ApplicationError(
            "password_change_required", "Change your initial password first.", 403
        )
    if admin and actor.role != "admin":
        raise ApplicationError("forbidden", "Only company admins can perform this action.", 403)
