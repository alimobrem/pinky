"""Tests for analytics event emission on approval decisions."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pinky_api.models.analytics import AnalyticsEvent
from pinky_api.repositories.analytics import AnalyticsRepository

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pinky:pinky@localhost:5432/pinky",
)

_test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_analytics_repository_record_creates_event():
    """Verify AnalyticsRepository.record() creates an analytics event with correct fields."""
    async with _test_session_factory() as session:
        analytics = AnalyticsRepository(session)
        execution_id = uuid4()

        event = await analytics.record(
            "approval_decided",
            {"decision": "approved", "execution_id": str(execution_id)},
            execution_id=execution_id,
        )

        assert event is not None
        assert isinstance(event, AnalyticsEvent)
        assert event.event_type == "approval_decided"
        assert event.payload["decision"] == "approved"
        assert event.payload["execution_id"] == str(execution_id)
        assert event.execution_id == execution_id
        assert event.occurred_at is not None


@pytest.mark.asyncio
async def test_analytics_repository_record_with_reason():
    """Verify AnalyticsRepository.record() stores payload with reason field."""
    async with _test_session_factory() as session:
        analytics = AnalyticsRepository(session)
        execution_id = uuid4()

        event = await analytics.record(
            "approval_decided",
            {"decision": "rejected", "execution_id": str(execution_id), "reason": "Not safe"},
            execution_id=execution_id,
        )

        assert event is not None
        assert event.event_type == "approval_decided"
        assert event.payload["decision"] == "rejected"
        assert event.payload["reason"] == "Not safe"
        assert event.execution_id == execution_id
