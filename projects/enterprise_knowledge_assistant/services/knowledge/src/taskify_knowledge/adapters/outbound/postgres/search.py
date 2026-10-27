"""Exact pgvector ranking filters tenant/current revision/model space before selecting evidence."""

import math
from uuid import UUID

from sqlalchemy import Engine, text

from taskify_knowledge.adapters.outbound.postgres.unit_of_work import SqlUnitOfWork
from taskify_knowledge.application.ports.retrieval import CurrentSource, EvidenceKey, RetrievedChunk
from taskify_knowledge.domain.errors import DependencyUnavailable
from taskify_knowledge.domain.locators import PdfLocator, decode_locator


class SqlVectorSearch:
    """Owned runtime pool performs no approximate/global ranking or after-ranking tenant filtering."""

    def __init__(self, engine: Engine) -> None:
        """Retain Knowledge-owned storage only; caller authority is a freshly resolved company."""
        self.engine = engine

    def search(
        self, company: UUID, vector: tuple[float, ...], pipeline: str
    ) -> tuple[RetrievedChunk, ...]:
        """Reject incompatible spaces and select at most 20 exact cosine candidates deterministically."""
        if (
            len(vector) != 1536
            or not all(math.isfinite(value) for value in vector)
            or not any(vector)
        ):
            raise DependencyUnavailable()
        with SqlUnitOfWork(self.engine, company) as transaction:
            assert transaction.session is not None
            mismatch = transaction.session.scalar(
                text("""SELECT EXISTS(SELECT 1 FROM knowledge_chunks c
                JOIN knowledge_items i ON i.id=c.item_id AND i.company_id=c.company_id
                JOIN knowledge_revisions r ON r.id=c.revision_id AND r.company_id=c.company_id
                WHERE i.company_id=:company AND i.removed_at IS NULL AND i.active_revision_id=r.id AND r.state='ready'
                  AND (c.pipeline_version<>:pipeline OR c.embedding_model<>'text-embedding-3-small' OR c.dimensions<>1536))"""),
                {"company": company, "pipeline": pipeline},
            )
            if mismatch:
                raise DependencyUnavailable()
            rows = (
                transaction.session.execute(
                    text("""SELECT c.id,c.item_id,c.revision_id,c.text,c.locator,i.title,
                1-(c.embedding <=> CAST(:vector AS vector)) AS similarity
                FROM knowledge_chunks c JOIN knowledge_items i ON i.id=c.item_id AND i.company_id=c.company_id
                JOIN knowledge_revisions r ON r.id=c.revision_id AND r.company_id=c.company_id AND r.item_id=i.id
                WHERE c.company_id=:company AND i.removed_at IS NULL AND i.active_revision_id=r.id AND r.state='ready'
                  AND c.pipeline_version=:pipeline AND c.embedding_model='text-embedding-3-small' AND c.dimensions=1536
                ORDER BY c.embedding <=> CAST(:vector AS vector),c.id LIMIT 20"""),
                    {
                        "company": company,
                        "pipeline": pipeline,
                        "vector": "[" + ",".join(str(value) for value in vector) + "]",
                    },
                )
                .mappings()
                .all()
            )
            return tuple(
                RetrievedChunk(
                    EvidenceKey(row["item_id"], row["revision_id"], row["id"]),
                    row["title"],
                    row["text"],
                    decode_locator(row["locator"]),
                    float(row["similarity"]),
                )
                for row in rows
            )

    def validate(self, company: UUID, keys: tuple[EvidenceKey, ...]) -> tuple[CurrentSource, ...]:
        """One SQL statement provides the batch snapshot; exact triples prevent locator relinking."""
        if not keys:
            return ()
        bindings: dict[str, object] = {"company": company}
        predicates = []
        for index, key in enumerate(keys):
            predicates.append(
                f"(c.item_id=:item{index} AND c.revision_id=:revision{index} AND c.id=:chunk{index})"
            )
            bindings.update(
                {
                    f"item{index}": key.item_id,
                    f"revision{index}": key.revision_id,
                    f"chunk{index}": key.chunk_id,
                }
            )
        with SqlUnitOfWork(self.engine, company) as transaction:
            assert transaction.session is not None
            rows = (
                transaction.session.execute(
                    text(
                        """SELECT c.item_id,c.revision_id,c.id,c.locator,i.title
                FROM knowledge_chunks c JOIN knowledge_items i ON i.id=c.item_id AND i.company_id=c.company_id
                JOIN knowledge_revisions r ON r.id=c.revision_id AND r.company_id=c.company_id AND r.item_id=i.id
                WHERE c.company_id=:company AND i.removed_at IS NULL AND i.active_revision_id=r.id AND r.state='ready' AND ("""
                        + " OR ".join(predicates)
                        + ")"
                    ),
                    bindings,
                )
                .mappings()
                .all()
            )
            current = {
                EvidenceKey(row["item_id"], row["revision_id"], row["id"]): row for row in rows
            }
        result = []
        for key in keys:
            row = current.get(key)
            if row is None:
                result.append(CurrentSource(key, None, None, None))
            else:
                locator = decode_locator(row["locator"])
                path = f"/api/v1/knowledge/{key.item_id}/source?revision_id={key.revision_id}"
                if isinstance(locator, PdfLocator):
                    path += f"#page={locator.page}"
                result.append(CurrentSource(key, row["title"], locator, path))
        return tuple(result)
