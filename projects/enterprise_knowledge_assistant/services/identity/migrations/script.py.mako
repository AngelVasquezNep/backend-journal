"""${message}."""
from alembic import op
import sqlalchemy as sa
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Apply the service-owned schema revision."""
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    """Revert the service-owned schema revision."""
    ${downgrades if downgrades else "pass"}
