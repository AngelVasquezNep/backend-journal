"""Enforce ready/current invariants even when a revision changes without a paired item update."""

from alembic import op

revision = "0004_current_revision_guard"
down_revision = "0003_retire_originals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Use a deferred revision-side guard so atomic supersede/pointer switches remain valid."""
    op.execute("""
    CREATE FUNCTION taskify_revision_current_guard() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    BEGIN
      IF EXISTS(SELECT 1 FROM public.knowledge_items i JOIN public.knowledge_revisions r
        ON i.active_revision_id=r.id AND i.company_id=r.company_id WHERE r.id=NEW.id AND (r.state<>'ready' OR i.removed_at IS NOT NULL))
      THEN RAISE EXCEPTION 'An active revision must remain ready and available'; END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER revision_current_guard AFTER UPDATE ON knowledge_revisions DEFERRABLE INITIALLY DEFERRED
      FOR EACH ROW EXECUTE FUNCTION taskify_revision_current_guard();
    """)


def downgrade() -> None:
    """Remove only the revision-side validation trigger, preserving originals and existing rows."""
    op.execute(
        "DROP TRIGGER revision_current_guard ON knowledge_revisions; DROP FUNCTION taskify_revision_current_guard();"
    )
