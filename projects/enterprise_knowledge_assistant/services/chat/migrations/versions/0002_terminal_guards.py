"""Strengthen saved message/terminal-state invariants independently from worker application checks."""

from alembic import op

revision = "0002_terminal_guards"
down_revision = "0001_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Require exact user/assistant pointers, immutable saved text and complete lease/terminal metadata."""
    op.execute("""
    ALTER TABLE chat_messages ADD CONSTRAINT assistant_terminal_nonnull
      CHECK(sender='user' OR outcome IS NOT NULL);
    ALTER TABLE chat_turns ADD CONSTRAINT exact_pending_terminal_fields
      CHECK((state IN ('queued','running') AND assistant_message_id IS NULL AND completed_at IS NULL)
        OR (state IN ('completed','failed') AND assistant_message_id IS NOT NULL AND completed_at IS NOT NULL));
    ALTER TABLE chat_turns ADD CONSTRAINT exact_lease_fields
      CHECK((state='running' AND lease_owner IS NOT NULL AND lease_until IS NOT NULL AND attempt_count>=1)
        OR (state<>'running' AND lease_owner IS NULL AND lease_until IS NULL));
    ALTER TABLE chat_turns ADD CONSTRAINT nonempty_retrieval_version
      CHECK(retrieval_config_version IS NULL OR char_length(retrieval_config_version) BETWEEN 1 AND 400);
    CREATE FUNCTION taskify_saved_message_immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,public AS $$
    BEGIN RAISE EXCEPTION 'Saved message and citation content is immutable'; END $$;
    CREATE TRIGGER immutable_message BEFORE UPDATE ON chat_messages FOR EACH ROW EXECUTE FUNCTION taskify_saved_message_immutable();
    CREATE TRIGGER immutable_citation BEFORE UPDATE ON citations FOR EACH ROW EXECUTE FUNCTION taskify_saved_message_immutable();
    CREATE FUNCTION taskify_exact_turn_messages() RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    DECLARE current_turn public.chat_turns; user_sequence bigint;
    BEGIN
      SELECT * INTO current_turn FROM public.chat_turns WHERE id=NEW.id;
      SELECT sequence INTO user_sequence FROM public.chat_messages WHERE id=current_turn.user_message_id AND sender='user';
      IF user_sequence IS NULL THEN RAISE EXCEPTION 'A turn must reference its user question'; END IF;
      IF current_turn.state IN ('completed','failed') AND NOT EXISTS(SELECT 1 FROM public.chat_messages
        WHERE id=current_turn.assistant_message_id AND sender='assistant' AND sequence=user_sequence+1
          AND ((current_turn.state='failed' AND outcome='failure') OR (current_turn.state='completed' AND outcome<>'failure')))
      THEN RAISE EXCEPTION 'A terminal turn must reference its next assistant outcome'; END IF;
      RETURN NEW;
    END $$;
    CREATE CONSTRAINT TRIGGER exact_turn_messages AFTER INSERT OR UPDATE ON chat_turns DEFERRABLE INITIALLY DEFERRED
      FOR EACH ROW EXECUTE FUNCTION taskify_exact_turn_messages();
    """)


def downgrade() -> None:
    """Preserve saved-history integrity through reviewed forward migrations only."""
    raise RuntimeError("Use a reviewed forward migration for saved-history constraints.")
