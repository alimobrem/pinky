"""Add outcome column to executions table."""

from alembic import op
import sqlalchemy as sa

revision = "j5d6e7f8g9h0"
down_revision = "i4c5d6e7f8g9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("executions", sa.Column("outcome", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("executions", "outcome")
