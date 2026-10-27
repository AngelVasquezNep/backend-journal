"""Validate deferred worker transitions in their narrowly scoped owner context after unscoped claims return."""

from alembic import op

revision = "0003_deferred_guard_scope"
down_revision = "0002_terminal_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Keep the trigger's same-turn invariant check effective after a definer claim returns to runtime RLS."""
    op.execute("ALTER FUNCTION taskify_exact_turn_messages() SECURITY DEFINER;")


def downgrade() -> None:
    """Preserve deferred worker integrity through reviewed forward migrations only."""
    raise RuntimeError("Use a reviewed forward migration for worker validation scope.")
