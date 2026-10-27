"""Knowledge composition wires local storage/OCR, durable PostgreSQL work and scoped Identity HTTP."""

import random
from importlib.metadata import version
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI
from sqlalchemy import text

from taskify_knowledge.adapters.inbound.http.body_limit import BodyLimit
from taskify_knowledge.adapters.inbound.http.common import install_boundaries, install_health
from taskify_knowledge.adapters.inbound.http.internal_retrieval import retrieval_router
from taskify_knowledge.adapters.inbound.http.knowledge import knowledge_router
from taskify_knowledge.adapters.inbound.http.maintenance import maintenance_router
from taskify_knowledge.adapters.inbound.http.sources import source_router
from taskify_knowledge.adapters.outbound.chunking import TokenChunker
from taskify_knowledge.adapters.outbound.embeddings import DeterministicEmbedder, OpenAIEmbedder
from taskify_knowledge.adapters.outbound.extraction import LocalExtractor
from taskify_knowledge.adapters.outbound.filesystem import FilesystemStorage
from taskify_knowledge.adapters.outbound.http.identity import IdentityHTTP
from taskify_knowledge.adapters.outbound.operational import configure_logging
from taskify_knowledge.adapters.outbound.postgres.cursors import CursorCodec
from taskify_knowledge.adapters.outbound.postgres.repositories import SqlKnowledgeStore
from taskify_knowledge.adapters.outbound.postgres.search import SqlVectorSearch
from taskify_knowledge.adapters.outbound.postgres.unit_of_work import owned_engine
from taskify_knowledge.adapters.outbound.settings import Settings
from taskify_knowledge.adapters.outbound.system import RandomIds, SystemClock
from taskify_knowledge.application.ports.identity import SessionValidator
from taskify_knowledge.application.service import KnowledgeService
from taskify_knowledge.domain.errors import DependencyUnavailable
from taskify_knowledge.domain.pipeline import PipelineConfiguration


def pipeline(settings: Settings, clock: SystemClock) -> PipelineConfiguration:
    """Tag stub/OpenAI vector spaces separately; never mix deterministic vectors with real embeddings."""
    backend = "stub-v1" if settings.ai_mode == "stub" else "openai-v1"
    return PipelineConfiguration(
        version=settings.pipeline_version + "-" + backend,
        normalization_version="nfc-newlines-offsets-v1",
        extractor_versions={
            name: version(name) for name in ("pypdf", "pypdfium2", "python-docx", "Pillow")
        }
        | {"embedding_backend": backend},
        splitter_name="recursive-tiktoken-v1",
        chunk_tokens=800,
        overlap_tokens=100,
        embedding_model="text-embedding-3-small",
        dimensions=1536,
        tokenizer="cl100k_base",
        created_at=clock.now(),
    )


def create_service(settings: Settings | None = None, *, worker: bool = False) -> KnowledgeService:
    """Compose/register owned processing metadata without making an embedding availability call."""
    resolved = settings or Settings.from_env()
    if not resolved.storage_root or not resolved.service_credential:
        raise ValueError("Knowledge requires private storage and service credentials.")
    clock = SystemClock()
    selected = pipeline(resolved, clock)
    store = SqlKnowledgeStore(
        owned_engine(resolved.database_url), CursorCodec(resolved.service_credential)
    )
    extractor = LocalExtractor(Path(resolved.storage_root))
    extractor.validate_runtime()
    embedder = (
        DeterministicEmbedder()
        if resolved.ai_mode == "stub"
        else OpenAIEmbedder(resolved.api_key or "")
    )
    store.register_pipeline(selected)
    return KnowledgeService(
        store,
        FilesystemStorage(Path(resolved.storage_root), extractor),
        extractor,
        TokenChunker(),
        embedder,
        selected,
        clock,
        RandomIds(),
        random.random,
    )


def create_app(
    settings: Settings | None = None,
    service: KnowledgeService | None = None,
    identity: SessionValidator | None = None,
) -> FastAPI:
    """Expose company-scoped APIs with explicit dependencies for real-storage/parser contract tests."""
    resolved = settings or Settings.from_env()
    knowledge = service or create_service(resolved)
    session_validator = identity or IdentityHTTP(
        resolved.identity_url or "",
        resolved.service_credential or "",
        allow_insecure=not resolved.production,
    )
    app = FastAPI(title="Taskify Knowledge", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(BodyLimit)
    install_boundaries(app)
    app.include_router(knowledge_router(knowledge, session_validator, resolved))
    app.include_router(maintenance_router(knowledge, session_validator, resolved))
    app.include_router(source_router(knowledge, session_validator, resolved))
    if isinstance(knowledge.store, SqlKnowledgeStore):
        background_identity = identity or IdentityHTTP(
            resolved.identity_url or "",
            resolved.worker_credential or "",
            worker=True,
            allow_insecure=not resolved.production,
        )
        app.include_router(
            retrieval_router(
                knowledge, SqlVectorSearch(knowledge.store.engine), background_identity, resolved
            )
        )

    def ready() -> None:
        """Check owned queue/storage and local OCR only; readiness never embeds text or calls a model."""
        store = knowledge.store
        if not isinstance(store, SqlKnowledgeStore):
            raise DependencyUnavailable()
        with store.engine.connect() as connection:
            connection.execute(text("SELECT id FROM ingestion_jobs LIMIT 0"))
        if not Path(resolved.storage_root or "").is_dir():
            raise DependencyUnavailable()

        for dependency in (resolved.identity_url,):
            if dependency:
                try:
                    response = httpx.get(
                        dependency.rstrip("/") + "/health/ready",
                        timeout=1.0,
                        follow_redirects=False,
                    )
                    if response.status_code != 200:
                        raise DependencyUnavailable()
                except httpx.HTTPError:
                    raise DependencyUnavailable() from None

    install_health(app, ready)
    return app


def main() -> None:
    """Serve the independent Knowledge API without request-body/provider tracing or access payloads."""
    configure_logging()
    uvicorn.run(
        "taskify_knowledge.bootstrap:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        access_log=False,
    )
