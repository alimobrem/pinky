"""Drop investigation unique constraint that blocks legitimate execution completions.

The constraint uq_one_completed_investigation_per_work_item fires on UPDATEs
(status → completed) even though it was meant to prevent INSERTs. The cooldown
check in _dispatch_investigation already prevents duplicate investigations at
the application level.

Revision ID: h3b4c5d6e7f8
Revises: g2a3b4c5d6e7
Create Date: 2026-05-13
"""

from typing import Union

from alembic import op

revision: str = "h3b4c5d6e7f8"
down_revision: Union[str, None] = "g2a3b4c5d6e7"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.drop_index(
        "uq_one_completed_investigation_per_work_item",
        table_name="executions",
    )


def downgrade() -> None:
    op.create_index(
        "uq_one_completed_investigation_per_work_item",
        "executions",
        ["work_item_id"],
        unique=True,
        postgresql_where="execution_type = 'investigation' AND status = 'completed'",
    )
