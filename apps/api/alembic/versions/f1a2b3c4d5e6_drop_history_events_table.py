"""Drop unused history_events table.

Events are written to domain_events via emit(). The history_events table
was created in the initial schema but never used by the public API.

Revision ID: f1a2b3c4d5e6
Revises: e7b2c4f19a60
Create Date: 2026-05-08
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e7b2c4f19a60"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.drop_table("history_events")


def downgrade() -> None:
    op.create_table(
        "history_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("aggregate_type", sa.String, nullable=False),
        sa.Column("aggregate_id", UUID, nullable=False),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("cluster_id", UUID),
        sa.Column("principal_id", UUID),
        sa.Column("payload", JSONB, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
