"""Tests for webhook formatters."""

from pinky_worker.webhooks.formatters import format_event, format_generic, format_slack, format_teams


EVENT = {
    "event_type": "work_item.accepted",
    "aggregate_type": "work_item",
    "aggregate_id": "abc-123",
    "payload": {"status": "accepted", "owner": "user-1"},
    "occurred_at": "2026-05-02T12:00:00Z",
}


def test_generic_formatter() -> None:
    result = format_generic(EVENT)
    assert result["event_type"] == "work_item.accepted"
    assert result["aggregate_type"] == "work_item"
    assert isinstance(result["payload"], dict)


def test_slack_formatter() -> None:
    result = format_slack(EVENT)
    assert "blocks" in result
    assert len(result["blocks"]) > 0
    assert "work_item.accepted" in result["blocks"][0]["text"]["text"]


def test_teams_formatter() -> None:
    result = format_teams(EVENT)
    assert "attachments" in result
    body = result["attachments"][0]["content"]["body"]
    assert "work_item.accepted" in body[0]["text"]


def test_format_event_dispatches() -> None:
    assert "blocks" in format_event(EVENT, "slack")
    assert "attachments" in format_event(EVENT, "teams")
    assert "event_type" in format_event(EVENT, "generic")
    assert "event_type" in format_event(EVENT, "unknown_formatter")
