"""Add indexes for analytics queries."""

from alembic import op

revision = "m8g9h0i1j2k3"
down_revision = "l7f8g9h0i1j2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_execution_events_llm_calls",
        "execution_events",
        ["event_type", "occurred_at"],
        postgresql_where="event_type = 'llm_call'",
    )
    op.create_index(
        "idx_analytics_events_type_time",
        "analytics_events",
        ["event_type", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_analytics_events_type_time")
    op.drop_index("idx_execution_events_llm_calls")
