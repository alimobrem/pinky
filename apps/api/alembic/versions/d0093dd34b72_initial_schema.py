"""initial schema

Revision ID: d0093dd34b72
Revises:
Create Date: 2026-05-02 15:53:51.671174
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd0093dd34b72'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'principals',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('display_name', sa.String()),
        sa.Column('email', sa.String()),
        sa.Column('groups', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('provider', 'subject'),
    )

    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('principal_id', postgresql.UUID(), sa.ForeignKey('principals.id'), nullable=False),
        sa.Column('token_hash', sa.String(), unique=True, nullable=False),
        sa.Column('csrf_token', sa.String(), nullable=False),
        sa.Column('idle_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('absolute_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('rotated_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'session_audit_log',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('session_id', postgresql.UUID(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
    )

    op.create_table(
        'cluster_registry',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('api_endpoint', sa.String(), nullable=False),
        sa.Column('fleet_identifier', sa.String()),
        sa.Column('onboarding_state', sa.String(), server_default='pending'),
        sa.Column('offboarding_state', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'cluster_observer_bindings',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('cluster_id', postgresql.UUID(), sa.ForeignKey('cluster_registry.id'), nullable=False),
        sa.Column('auth_method', sa.String(), nullable=False),
        sa.Column('health_state', sa.String(), server_default='unknown'),
        sa.Column('last_observation_at', sa.DateTime(timezone=True)),
        sa.Column('encrypted_credential', sa.LargeBinary()),
        sa.Column('rbac_scope', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'cluster_identity_bindings',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('principal_id', postgresql.UUID(), sa.ForeignKey('principals.id'), nullable=False),
        sa.Column('cluster_id', postgresql.UUID(), sa.ForeignKey('cluster_registry.id'), nullable=False),
        sa.Column('cluster_username', sa.String()),
        sa.Column('cluster_groups', postgresql.JSONB(), server_default='[]'),
        sa.Column('binding_method', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='missing'),
        sa.Column('encrypted_token', sa.LargeBinary()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('principal_id', 'cluster_id'),
    )

    op.create_table(
        'observations',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('cluster_id', postgresql.UUID(), sa.ForeignKey('cluster_registry.id'), nullable=False),
        sa.Column('scanner', sa.String(), nullable=False),
        sa.Column('scanner_version', sa.String()),
        sa.Column('fingerprint', sa.String(), nullable=False),
        sa.Column('check_id', sa.String()),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('resource_kind', sa.String()),
        sa.Column('resource_namespace', sa.String()),
        sa.Column('resource_name', sa.String()),
        sa.Column('payload', postgresql.JSONB(), server_default='{}'),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_observations_fingerprint', 'observations', ['fingerprint'])
    op.create_index('idx_observations_cluster', 'observations', ['cluster_id', 'observed_at'])

    op.create_table(
        'issues',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('cluster_id', postgresql.UUID(), sa.ForeignKey('cluster_registry.id'), nullable=False),
        sa.Column('correlation_key', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='open'),
        sa.Column('labels', postgresql.JSONB(), server_default='{}'),
        sa.Column('annotations', postgresql.JSONB(), server_default='{}'),
        sa.Column('runbook_url', sa.String()),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('suppressed_until', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_issues_correlation', 'issues', ['correlation_key'])
    op.create_index('idx_issues_cluster', 'issues', ['cluster_id', 'status'])
    op.create_index('idx_issues_labels', 'issues', ['labels'], postgresql_using='gin')

    op.create_table(
        'work_items',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('issue_id', postgresql.UUID(), sa.ForeignKey('issues.id')),
        sa.Column('cluster_id', postgresql.UUID(), sa.ForeignKey('cluster_registry.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('why_now', sa.String()),
        sa.Column('recommended_next_step', sa.String()),
        sa.Column('status', sa.String(), server_default='ready'),
        sa.Column('owner_id', postgresql.UUID(), sa.ForeignKey('principals.id')),
        sa.Column('confidence', sa.Float()),
        sa.Column('priority', sa.String(), server_default='medium'),
        sa.Column('labels', postgresql.JSONB(), server_default='{}'),
        sa.Column('annotations', postgresql.JSONB(), server_default='{}'),
        sa.Column('runbook_url', sa.String()),
        sa.Column('artifact_refs', postgresql.JSONB(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_work_items_cluster', 'work_items', ['cluster_id', 'status'])
    op.create_index('idx_work_items_owner', 'work_items', ['owner_id', 'status'])
    op.create_index('idx_work_items_labels', 'work_items', ['labels'], postgresql_using='gin')

    op.create_table(
        'executions',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('work_item_id', postgresql.UUID(), sa.ForeignKey('work_items.id')),
        sa.Column('cluster_id', postgresql.UUID(), sa.ForeignKey('cluster_registry.id'), nullable=False),
        sa.Column('execution_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'execution_events',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('execution_id', postgresql.UUID(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('payload', postgresql.JSONB(), server_default='{}'),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'history_events',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('aggregate_type', sa.String(), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('cluster_id', postgresql.UUID()),
        sa.Column('principal_id', postgresql.UUID()),
        sa.Column('payload', postgresql.JSONB(), server_default='{}'),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'approvals',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('execution_id', postgresql.UUID(), sa.ForeignKey('executions.id'), nullable=False),
        sa.Column('approver_id', postgresql.UUID(), sa.ForeignKey('principals.id')),
        sa.Column('changeset_digest', sa.String(), nullable=False),
        sa.Column('target_resources', postgresql.JSONB(), nullable=False),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'analytics_events',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('principal_id', postgresql.UUID()),
        sa.Column('cluster_id', postgresql.UUID()),
        sa.Column('aggregate_id', postgresql.UUID()),
        sa.Column('execution_id', postgresql.UUID()),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'eval_runs',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('fixture_id', sa.String(), nullable=False),
        sa.Column('scores', postgresql.JSONB(), nullable=False),
        sa.Column('token_usage', postgresql.JSONB()),
        sa.Column('model_version', sa.String()),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'definitions',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), server_default='1.0.0'),
        sa.Column('frontmatter', postgresql.JSONB(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='true'),
        sa.Column('created_by', postgresql.UUID(), sa.ForeignKey('principals.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('kind', 'name'),
    )

    op.create_table(
        'service_bindings',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('service_type', sa.String(), nullable=False),
        sa.Column('cluster_id', postgresql.UUID(), sa.ForeignKey('cluster_registry.id')),
        sa.Column('base_url', sa.String(), nullable=False),
        sa.Column('auth_method', sa.String(), nullable=False),
        sa.Column('encrypted_credential', sa.LargeBinary(), nullable=False),
        sa.Column('health_state', sa.String(), server_default='unknown'),
        sa.Column('last_check_at', sa.DateTime(timezone=True)),
        sa.Column('created_by', postgresql.UUID(), sa.ForeignKey('principals.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('name', 'cluster_id'),
    )

    op.create_table(
        'domain_events',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('aggregate_type', sa.String(), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(), nullable=False),
        sa.Column('cluster_id', postgresql.UUID()),
        sa.Column('principal_id', postgresql.UUID()),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_domain_events_type', 'domain_events', ['event_type', 'occurred_at'])

    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('event_patterns', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('formatter', sa.String(), server_default='generic'),
        sa.Column('channel_config', postgresql.JSONB(), server_default='{}'),
        sa.Column('secret_hash', sa.String()),
        sa.Column('enabled', sa.Boolean(), server_default='true'),
        sa.Column('created_by', postgresql.UUID(), sa.ForeignKey('principals.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('subscription_id', postgresql.UUID(), sa.ForeignKey('webhook_subscriptions.id'), nullable=False),
        sa.Column('domain_event_id', postgresql.UUID(), sa.ForeignKey('domain_events.id'), nullable=False),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('attempts', sa.Integer(), server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True)),
        sa.Column('last_response_code', sa.Integer()),
        sa.Column('next_retry_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'policy_rules',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('description', sa.String()),
        sa.Column('priority', sa.Integer(), server_default='100'),
        sa.Column('enabled', sa.Boolean(), server_default='true'),
        sa.Column('conditions', postgresql.JSONB(), nullable=False),
        sa.Column('action', postgresql.JSONB(), nullable=False),
        sa.Column('created_by', postgresql.UUID(), sa.ForeignKey('principals.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'api_tokens',
        sa.Column('id', postgresql.UUID(), primary_key=True),
        sa.Column('principal_id', postgresql.UUID(), sa.ForeignKey('principals.id'), nullable=False),
        sa.Column('token_hash', sa.String(), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), server_default='{}'),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'projection_cursors',
        sa.Column('workflow_id', sa.String(), primary_key=True),
        sa.Column('last_event_id', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('projection_cursors')
    op.drop_table('api_tokens')
    op.drop_table('policy_rules')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_subscriptions')
    op.drop_index('idx_domain_events_type')
    op.drop_table('domain_events')
    op.drop_table('service_bindings')
    op.drop_table('definitions')
    op.drop_table('eval_runs')
    op.drop_table('analytics_events')
    op.drop_table('approvals')
    op.drop_table('history_events')
    op.drop_table('execution_events')
    op.drop_table('executions')
    op.drop_index('idx_work_items_labels')
    op.drop_index('idx_work_items_owner')
    op.drop_index('idx_work_items_cluster')
    op.drop_table('work_items')
    op.drop_index('idx_issues_labels')
    op.drop_index('idx_issues_cluster')
    op.drop_index('idx_issues_correlation')
    op.drop_table('issues')
    op.drop_index('idx_observations_cluster')
    op.drop_index('idx_observations_fingerprint')
    op.drop_table('observations')
    op.drop_table('cluster_identity_bindings')
    op.drop_table('cluster_observer_bindings')
    op.drop_table('cluster_registry')
    op.drop_table('session_audit_log')
    op.drop_table('sessions')
    op.drop_table('principals')
