"""Grant a narrowly scoped reference-existence function for conservative private orphan cleanup."""

from alembic import op

revision = "0002_storage_reconcile"
down_revision = "0001_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Expose only whether one opaque key has a revision reference; never return tenant records."""
    op.execute("""
    CREATE FUNCTION taskify_original_referenced(object_key text) RETURNS boolean
      LANGUAGE sql STABLE SECURITY DEFINER SET search_path=public,pg_temp AS $$
      SELECT EXISTS(SELECT 1 FROM knowledge_revisions WHERE storage_key=object_key)
    $$;
    REVOKE ALL ON FUNCTION taskify_original_referenced(text) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION taskify_original_referenced(text) TO knowledge_runtime;
    """)


def downgrade() -> None:
    """Remove only this service-owned reference lookup; original rows/bytes remain untouched."""
    op.execute("DROP FUNCTION taskify_original_referenced(text)")
