"""Create Knowledge-owned revisions, exact vectors, forced tenant policies and fenced durable jobs.

All identifiers are UUIDs; timestamps are UTC.
Text lengths count Unicode code points, not bytes, unless explicitly stated.
"""

from alembic import op

revision = "0001_knowledge"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply immutable ownership constraints and narrowly granted worker functions."""
    op.execute("""
    CREATE TABLE pipeline_configurations (
      version text PRIMARY KEY, normalization_version text NOT NULL, extractor_versions jsonb NOT NULL,
      splitter_name text NOT NULL, chunk_tokens integer NOT NULL CHECK (chunk_tokens=800),
      overlap_tokens integer NOT NULL CHECK (overlap_tokens=100), embedding_model text NOT NULL CHECK (embedding_model='text-embedding-3-small'),
      dimensions integer NOT NULL CHECK (dimensions=1536), tokenizer text NOT NULL CHECK (tokenizer='cl100k_base'), created_at timestamptz NOT NULL
    );
    CREATE TABLE knowledge_items (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200 AND title=btrim(title) AND title !~ '[[:cntrl:]]'),
      created_by uuid NOT NULL, active_revision_id uuid, candidate_revision_id uuid,
      version integer NOT NULL CHECK (version>0), created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL, removed_at timestamptz,
      UNIQUE(company_id,id), CHECK(removed_at IS NULL OR (active_revision_id IS NULL AND candidate_revision_id IS NULL))
    );
    CREATE INDEX knowledge_items_company ON knowledge_items(company_id,created_at,id);
    CREATE TABLE knowledge_revisions (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, item_id uuid NOT NULL, uploaded_by uuid NOT NULL,
      original_filename text NOT NULL CHECK (char_length(original_filename) BETWEEN 1 AND 255 AND original_filename !~ '[/\\\\[:cntrl:]]'),
      media_type text NOT NULL CHECK (media_type IN ('application/pdf','application/vnd.openxmlformats-officedocument.wordprocessingml.document','text/plain','image/png','image/jpeg')),
      size_bytes integer NOT NULL CHECK (size_bytes BETWEEN 1 AND 20971520), sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'), storage_key text NOT NULL UNIQUE CHECK (storage_key ~ '^[0-9a-f]{32}$'),
      state text NOT NULL CHECK (state IN ('processing','ready','failed','superseded','cancelled')),
      pipeline_version text NOT NULL REFERENCES pipeline_configurations(version), error_code text, created_at timestamptz NOT NULL, ready_at timestamptz,
      UNIQUE(company_id,id), UNIQUE(company_id,item_id,id),
      FOREIGN KEY(company_id,item_id) REFERENCES knowledge_items(company_id,id) DEFERRABLE INITIALLY DEFERRED
    );
    CREATE UNIQUE INDEX one_processing_revision ON knowledge_revisions(item_id) WHERE state='processing';
    ALTER TABLE knowledge_items ADD CONSTRAINT active_revision_owner FOREIGN KEY(company_id,id,active_revision_id) REFERENCES knowledge_revisions(company_id,item_id,id) DEFERRABLE INITIALLY DEFERRED;
    ALTER TABLE knowledge_items ADD CONSTRAINT candidate_revision_owner FOREIGN KEY(company_id,id,candidate_revision_id) REFERENCES knowledge_revisions(company_id,item_id,id) DEFERRABLE INITIALLY DEFERRED;
    CREATE TABLE extracted_blocks (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, revision_id uuid NOT NULL,
      ordinal integer NOT NULL CHECK(ordinal>=0), normalized_text text NOT NULL CHECK(char_length(normalized_text)>0),
      locator jsonb NOT NULL, source_offset_map jsonb NOT NULL, extractor_version text NOT NULL,
      UNIQUE(company_id,revision_id,id), UNIQUE(revision_id,ordinal),
      FOREIGN KEY(company_id,revision_id) REFERENCES knowledge_revisions(company_id,id) DEFERRABLE INITIALLY DEFERRED
    );
    CREATE TABLE knowledge_chunks (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, item_id uuid NOT NULL, revision_id uuid NOT NULL, block_id uuid NOT NULL,
      ordinal integer NOT NULL CHECK(ordinal>=0), text text NOT NULL CHECK(char_length(text)>0), token_count integer NOT NULL CHECK(token_count BETWEEN 1 AND 800),
      locator jsonb NOT NULL, text_sha256 text NOT NULL CHECK(text_sha256 ~ '^[0-9a-f]{64}$'),
      pipeline_version text NOT NULL REFERENCES pipeline_configurations(version), embedding_model text NOT NULL CHECK(embedding_model='text-embedding-3-small'),
      dimensions integer NOT NULL CHECK(dimensions=1536), embedding vector(1536) NOT NULL,
      UNIQUE(revision_id,pipeline_version,ordinal),
      FOREIGN KEY(company_id,item_id,revision_id) REFERENCES knowledge_revisions(company_id,item_id,id) DEFERRABLE INITIALLY DEFERRED,
      FOREIGN KEY(company_id,revision_id,block_id) REFERENCES extracted_blocks(company_id,revision_id,id) DEFERRABLE INITIALLY DEFERRED
    );
    CREATE INDEX knowledge_chunks_company_revision ON knowledge_chunks(company_id,revision_id);
    CREATE TABLE ingestion_jobs (
      id uuid PRIMARY KEY, company_id uuid NOT NULL, revision_id uuid NOT NULL,
      pipeline_version text NOT NULL REFERENCES pipeline_configurations(version), state text NOT NULL CHECK(state IN ('queued','running','succeeded','failed','cancelled')),
      attempt_count integer NOT NULL CHECK(attempt_count BETWEEN 0 AND 4), run_after timestamptz NOT NULL,
      lease_owner uuid, lease_until timestamptz, lease_version integer NOT NULL CHECK(lease_version>=0), heartbeat_at timestamptz, last_error_code text, created_at timestamptz NOT NULL,
      UNIQUE(revision_id,pipeline_version), FOREIGN KEY(company_id,revision_id) REFERENCES knowledge_revisions(company_id,id) DEFERRABLE INITIALLY DEFERRED,
      CHECK(state<>'running' OR (lease_owner IS NOT NULL AND lease_until IS NOT NULL))
    );
    CREATE INDEX ingestion_claims ON ingestion_jobs(state,run_after,lease_until);
    """)
    for table in (
        "knowledge_items",
        "knowledge_revisions",
        "extracted_blocks",
        "knowledge_chunks",
        "ingestion_jobs",
    ):
        op.execute(
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY; ALTER TABLE {table} FORCE ROW LEVEL SECURITY; CREATE POLICY tenant_scope ON {table} USING(current_user='knowledge_migration' OR company_id::text=current_setting('taskify.company_id',true));"
        )
    op.execute("""
    CREATE FUNCTION taskify_immutable_pipeline() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    BEGIN RAISE EXCEPTION 'Pipeline versions are immutable'; END; $$;
    CREATE TRIGGER immutable_pipeline BEFORE UPDATE OR DELETE ON pipeline_configurations FOR EACH ROW EXECUTE FUNCTION taskify_immutable_pipeline();
    CREATE FUNCTION taskify_immutable_original() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    BEGIN
      IF ROW(NEW.company_id,NEW.item_id,NEW.uploaded_by,NEW.original_filename,NEW.media_type,NEW.size_bytes,NEW.sha256,NEW.storage_key,NEW.pipeline_version,NEW.created_at)
         IS DISTINCT FROM ROW(OLD.company_id,OLD.item_id,OLD.uploaded_by,OLD.original_filename,OLD.media_type,OLD.size_bytes,OLD.sha256,OLD.storage_key,OLD.pipeline_version,OLD.created_at)
      THEN RAISE EXCEPTION 'Original identity is immutable'; END IF;
      IF NEW.state<>OLD.state AND NOT ((OLD.state='processing' AND NEW.state IN ('ready','failed','cancelled')) OR (OLD.state='ready' AND NEW.state='superseded'))
      THEN RAISE EXCEPTION 'Invalid revision transition'; END IF;
      RETURN NEW;
    END; $$;
    CREATE TRIGGER immutable_original BEFORE UPDATE ON knowledge_revisions FOR EACH ROW EXECUTE FUNCTION taskify_immutable_original();
    CREATE FUNCTION taskify_current_ready() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    DECLARE current_id uuid;
    BEGIN
      SELECT active_revision_id INTO current_id FROM public.knowledge_items WHERE id=NEW.id;
      IF current_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.knowledge_revisions WHERE id=current_id AND item_id=NEW.id AND company_id=NEW.company_id AND state='ready')
      THEN RAISE EXCEPTION 'Current pointer requires a ready revision'; END IF;
      RETURN NEW;
    END; $$;
    CREATE CONSTRAINT TRIGGER current_ready AFTER INSERT OR UPDATE ON knowledge_items DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION taskify_current_ready();

    CREATE FUNCTION taskify_claim_ingestion(p_worker uuid,p_now timestamptz) RETURNS SETOF ingestion_jobs
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    BEGIN
      WITH exhausted AS (UPDATE public.ingestion_jobs SET state='failed',last_error_code='processing_unavailable'
        WHERE state='running' AND lease_until<=p_now AND attempt_count>=4 RETURNING revision_id,company_id)
      UPDATE public.knowledge_revisions r SET state='failed',error_code='processing_unavailable'
        FROM exhausted e WHERE r.id=e.revision_id AND r.company_id=e.company_id AND r.state='processing';
      RETURN QUERY WITH candidate AS (
        SELECT id FROM public.ingestion_jobs WHERE attempt_count<4 AND
          ((state='queued' AND run_after<=p_now) OR (state='running' AND lease_until<=p_now))
        ORDER BY created_at,id FOR UPDATE SKIP LOCKED LIMIT 1
      ) UPDATE public.ingestion_jobs j SET state='running',attempt_count=j.attempt_count+1,
        lease_owner=p_worker,lease_until=p_now+interval '120 seconds',lease_version=j.lease_version+1,heartbeat_at=p_now
        FROM candidate c WHERE j.id=c.id RETURNING j.*;
    END; $$;
    CREATE FUNCTION taskify_heartbeat_ingestion(p_id uuid,p_owner uuid,p_version integer,p_now timestamptz) RETURNS boolean
      LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    BEGIN
      UPDATE public.ingestion_jobs SET lease_until=p_now+interval '120 seconds',heartbeat_at=p_now
        WHERE id=p_id AND lease_owner=p_owner AND lease_version=p_version AND state='running' AND lease_until>p_now;
      RETURN FOUND;
    END; $$;
    GRANT EXECUTE ON FUNCTION taskify_claim_ingestion(uuid,timestamptz),taskify_heartbeat_ingestion(uuid,uuid,integer,timestamptz) TO knowledge_runtime;
    """)


def downgrade() -> None:
    """Remove only Knowledge-owned schema and queue helpers; no other service data is affected."""
    op.execute("""
    DROP FUNCTION taskify_claim_ingestion(uuid,timestamptz),taskify_heartbeat_ingestion(uuid,uuid,integer,timestamptz);
    ALTER TABLE knowledge_items DROP CONSTRAINT active_revision_owner, DROP CONSTRAINT candidate_revision_owner;
    DROP TABLE ingestion_jobs,knowledge_chunks,extracted_blocks,knowledge_revisions,knowledge_items,pipeline_configurations;
    DROP FUNCTION taskify_immutable_pipeline(),taskify_immutable_original(),taskify_current_ready();
    """)
