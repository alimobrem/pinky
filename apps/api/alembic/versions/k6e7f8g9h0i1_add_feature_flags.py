"""Add feature_flags table.

Revision ID: k6e7f8g9h0i1
Revises: j5d6e7f8g9h0
Create Date: 2026-05-22 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "k6e7f8g9h0i1"
down_revision = "j5d6e7f8g9h0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("flag_name", sa.String(100), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean, server_default="false", nullable=False),
        sa.Column("scope_type", sa.String(20), server_default="global", nullable=False),
        sa.Column("scope_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
