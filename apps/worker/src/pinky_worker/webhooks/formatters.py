"""Webhook formatters — transform domain events for different targets."""

from __future__ import annotations

import json


def format_generic(event: dict) -> dict:
    return {
        "event_type": event.get("event_type"),
        "aggregate_type": event.get("aggregate_type"),
        "aggregate_id": str(event.get("aggregate_id", "")),
        "payload": event.get("payload", {}),
        "occurred_at": str(event.get("occurred_at", "")),
    }


def format_slack(event: dict) -> dict:
    event_type = event.get("event_type", "unknown")
    aggregate = event.get("aggregate_type", "")
    payload = event.get("payload", {})

    text = f"*{event_type}* on {aggregate}"
    if isinstance(payload, dict):
        details = ", ".join(f"{k}: {v}" for k, v in list(payload.items())[:5])
        if details:
            text += f"\n{details}"

    return {
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
        ],
    }


def format_teams(event: dict) -> dict:
    event_type = event.get("event_type", "unknown")
    aggregate = event.get("aggregate_type", "")

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": f"**{event_type}** on {aggregate}", "wrap": True},
                    ],
                },
            },
        ],
    }


FORMATTERS = {
    "generic": format_generic,
    "slack": format_slack,
    "teams": format_teams,
}


def format_event(event: dict, formatter_name: str) -> dict:
    formatter = FORMATTERS.get(formatter_name, format_generic)
    return formatter(event)
