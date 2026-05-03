"""add blocked_reason to work_items

Revision ID: a2f8e91c4d53
Revises: d0093dd34b72
Create Date: 2026-05-03 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a2f8e91c4d53'
down_revision: Union[str, None] = 'd0093dd34b72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('work_items', sa.Column('blocked_reason', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('work_items', 'blocked_reason')
