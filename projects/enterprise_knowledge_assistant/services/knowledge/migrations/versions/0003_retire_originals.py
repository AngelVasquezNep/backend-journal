"""Expose bounded obsolete original identities solely for the owning worker's conservative cleanup."""

from alembic import op

revision = "0003_retire_originals"
down_revision = "0002_storage_reconcile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Limit enumeration to unavailable revisions with no current pointer and no executable job."""
    op.execute("""
    CREATE TABLE retired_originals (
      revision_id uuid PRIMARY KEY,company_id uuid NOT NULL,storage_key text NOT NULL UNIQUE,purged_at timestamptz NOT NULL,
      FOREIGN KEY(company_id,revision_id) REFERENCES knowledge_revisions(company_id,id)
    );
    ALTER TABLE retired_originals ENABLE ROW LEVEL SECURITY;
    ALTER TABLE retired_originals FORCE ROW LEVEL SECURITY;
    CREATE POLICY tenant_scope ON retired_originals USING(current_user='knowledge_migration' OR company_id::text=current_setting('taskify.company_id',true));
    CREATE FUNCTION taskify_retirable_originals(before_instant timestamptz)
      RETURNS TABLE(company_id uuid,revision_id uuid,storage_key text)
      LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,public AS $$
      SELECT r.company_id,r.id,r.storage_key FROM public.knowledge_revisions r
      JOIN public.knowledge_items i ON i.id=r.item_id AND i.company_id=r.company_id
      WHERE r.created_at<before_instant AND i.active_revision_id IS DISTINCT FROM r.id
        AND (r.state IN ('superseded','failed','cancelled') OR i.removed_at<before_instant)
        AND NOT EXISTS(SELECT 1 FROM public.ingestion_jobs j WHERE j.revision_id=r.id AND j.state IN ('queued','running'))
        AND NOT EXISTS(SELECT 1 FROM public.retired_originals retired WHERE retired.revision_id=r.id)
      ORDER BY r.created_at,r.id LIMIT 100
    $$;
    REVOKE ALL ON FUNCTION taskify_retirable_originals(timestamptz) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION taskify_retirable_originals(timestamptz) TO knowledge_runtime;
    """)


def downgrade() -> None:
    """Remove the cleanup enumerator while preserving all original metadata."""
    op.execute(
        "DROP FUNCTION taskify_retirable_originals(timestamptz); DROP TABLE retired_originals;"
    )
