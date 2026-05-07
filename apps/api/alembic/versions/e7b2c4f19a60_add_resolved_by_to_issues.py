"""add resolved_by to issues

Revision ID: e7b2c4f19a60
Revises: c3b7a1d29f84
Create Date: 2026-05-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e7b2c4f19a60"
down_revision: Union[str, None] = "c3b7a1d29f84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("issues", sa.Column("resolved_by", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("issues", "resolved_by")
