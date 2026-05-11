"""Drop unused tables: history_events, eval_runs, session_audit_log, projection_cursors.

history_events: events written to domain_events, this table was never queried.
eval_runs: evals scaffolding, never populated.
session_audit_log: sessions use Redis only, audit log never implemented.
projection_cursors: event sourcing scaffolding, never used.

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
    op.drop_table("eval_runs")
    op.drop_table("session_audit_log")
    op.drop_table("projection_cursors")


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
    op.create_table(
        "eval_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("fixture_id", sa.String, nullable=False),
        sa.Column("scores", JSONB, nullable=False),
        sa.Column("token_usage", JSONB),
        sa.Column("model_version", sa.String),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default="now()"),
    )
    op.create_table(
        "session_audit_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("event_type", sa.String, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default="now()"),
        sa.Column("metadata", JSONB, server_default="{}"),
    )
    op.create_table(
        "projection_cursors",
        sa.Column("workflow_id", sa.String, primary_key=True),
        sa.Column("last_event_id", sa.Integer, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default="now()"),
    )
