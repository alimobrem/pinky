"""Cleanup duplicate investigation executions and add unique constraint.

The observer re-dispatched investigations for the same issue after cooldown
expired, creating hundreds of duplicate completed executions per work_item.
This migration deletes the duplicates (keeping the most recent) and adds a
partial unique index to prevent recurrence.

Revision ID: g2a3b4c5d6e7
Revises: f1a2b3c4d5e6
Create Date: 2026-05-12
"""

from typing import Union

from alembic import op

revision: str = "g2a3b4c5d6e7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("""
        WITH keepers AS (
            SELECT DISTINCT ON (work_item_id)
                id
            FROM executions
            WHERE execution_type = 'investigation'
              AND status = 'completed'
              AND work_item_id IS NOT NULL
            ORDER BY work_item_id, completed_at DESC NULLS LAST
        )
        DELETE FROM execution_events
        WHERE execution_id IN (
            SELECT e.id FROM executions e
            WHERE e.execution_type = 'investigation'
              AND e.status = 'completed'
              AND e.work_item_id IS NOT NULL
              AND e.id NOT IN (SELECT id FROM keepers)
        )
    """)

    op.execute("""
        WITH keepers AS (
            SELECT DISTINCT ON (work_item_id)
                id
            FROM executions
            WHERE execution_type = 'investigation'
              AND status = 'completed'
              AND work_item_id IS NOT NULL
            ORDER BY work_item_id, completed_at DESC NULLS LAST
        )
        DELETE FROM executions
        WHERE execution_type = 'investigation'
          AND status = 'completed'
          AND work_item_id IS NOT NULL
          AND id NOT IN (SELECT id FROM keepers)
    """)

    op.execute("""
        WITH keepers AS (
            SELECT DISTINCT ON (work_item_id)
                id
            FROM executions
            WHERE execution_type = 'investigation'
              AND status = 'failed'
              AND work_item_id IS NOT NULL
            ORDER BY work_item_id, completed_at DESC NULLS LAST
        )
        DELETE FROM execution_events
        WHERE execution_id IN (
            SELECT e.id FROM executions e
            WHERE e.execution_type = 'investigation'
              AND e.status = 'failed'
              AND e.work_item_id IS NOT NULL
              AND e.id NOT IN (SELECT id FROM keepers)
        )
    """)

    op.execute("""
        WITH keepers AS (
            SELECT DISTINCT ON (work_item_id)
                id
            FROM executions
            WHERE execution_type = 'investigation'
              AND status = 'failed'
              AND work_item_id IS NOT NULL
            ORDER BY work_item_id, completed_at DESC NULLS LAST
        )
        DELETE FROM executions
        WHERE execution_type = 'investigation'
          AND status = 'failed'
          AND work_item_id IS NOT NULL
          AND id NOT IN (SELECT id FROM keepers)
    """)

    op.create_index(
        "uq_one_completed_investigation_per_work_item",
        "executions",
        ["work_item_id"],
        unique=True,
        postgresql_where="execution_type = 'investigation' AND status = 'completed'",
    )


def downgrade() -> None:
    op.drop_index("uq_one_completed_investigation_per_work_item", table_name="executions")
