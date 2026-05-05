"""Add correlation_key to observations table.

Revision ID: c3b7a1d29f84
Revises: a2f8e91c4d53
"""
from alembic import op
import sqlalchemy as sa

revision = "c3b7a1d29f84"
down_revision = "a2f8e91c4d53"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("observations", sa.Column("correlation_key", sa.String(), nullable=True))
    op.create_index("idx_observations_correlation_key", "observations", ["correlation_key"])


def downgrade():
    op.drop_index("idx_observations_correlation_key")
    op.drop_column("observations", "correlation_key")
