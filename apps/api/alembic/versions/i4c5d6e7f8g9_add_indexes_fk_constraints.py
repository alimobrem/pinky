"""Add FK constraints, indexes, and partial unique index for execution integrity.

Revision ID: i4c5d6e7f8g9
Revises: h3b4c5d6e7f8
Create Date: 2026-05-20
"""

from alembic import op

revision = "i4c5d6e7f8g9"
down_revision = "h3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM execution_events WHERE execution_id NOT IN (SELECT id FROM executions)"
    )
    op.create_foreign_key(
        "fk_execution_events_execution_id",
        "execution_events",
        "executions",
        ["execution_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "idx_execution_events_execution_id",
        "execution_events",
        ["execution_id"],
    )

    op.create_index(
        "idx_approvals_execution_id",
        "approvals",
        ["execution_id"],
    )

    op.create_index(
        "idx_executions_status_cluster",
        "executions",
        ["cluster_id", "status", "execution_type", "created_at"],
    )

    op.execute(
        """CREATE UNIQUE INDEX IF NOT EXISTS idx_executions_active_per_work_item
           ON executions (work_item_id, execution_type)
           WHERE status NOT IN ('completed', 'failed', 'cancelled', 'timed_out')"""
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_executions_active_per_work_item")
    op.drop_index("idx_executions_status_cluster")
    op.drop_index("idx_approvals_execution_id")
    op.drop_index("idx_execution_events_execution_id")
    op.drop_constraint("fk_execution_events_execution_id", "execution_events")
