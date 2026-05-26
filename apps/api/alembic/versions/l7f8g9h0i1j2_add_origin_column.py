"""Add origin column to work_items and issues.

Revision ID: l7f8g9h0i1j2
Revises: k6e7f8g9h0i1
Create Date: 2026-05-22 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "l7f8g9h0i1j2"
down_revision = "k6e7f8g9h0i1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("work_items", sa.Column("origin", sa.String(20), server_default="pinky"))
    op.add_column("issues", sa.Column("origin", sa.String(20), server_default="pinky"))


def downgrade() -> None:
    op.drop_column("work_items", "origin")
    op.drop_column("issues", "origin")
