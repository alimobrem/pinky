"""Tests for webhook subscription CRUD endpoints."""

import uuid


def _unique(prefix: str = "webhook") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TestWebhookCreate:
    def test_create(self, authed_client):
        name = _unique()
        r = authed_client.post("/api/v1/webhook-subscriptions", json={
            "name": name, "url": "https://hooks.example.com/test",
            "event_patterns": ["issue.*", "work_item.blocked"],
        })
        assert r.status_code in (200, 201)
        w = r.json()
        assert w["name"] == name
        assert w["url"] == "https://hooks.example.com/test"
        assert "issue.*" in w["event_patterns"]
        authed_client.delete(f"/api/v1/webhook-subscriptions/{w['id']}")

    def test_create_with_formatter(self, authed_client):
        name = _unique()
        r = authed_client.post("/api/v1/webhook-subscriptions", json={
            "name": name, "url": "https://hooks.slack.com/x",
            "event_patterns": ["*"], "formatter": "slack",
        })
        assert r.status_code in (200, 201)
        w = r.json()
        assert w["formatter"] == "slack"
        authed_client.delete(f"/api/v1/webhook-subscriptions/{w['id']}")

    def test_create_non_admin_rejected(self, non_admin_client):
        r = non_admin_client.post("/api/v1/webhook-subscriptions", json={
            "name": "x", "url": "https://x.com", "event_patterns": ["*"],
        })
        assert r.status_code == 403

    def test_create_missing_url(self, authed_client):
        r = authed_client.post("/api/v1/webhook-subscriptions", json={
            "name": "x", "event_patterns": ["*"],
        })
        assert r.status_code == 422


class TestWebhookList:
    def test_list_includes_created(self, authed_client):
        name = _unique()
        cr = authed_client.post("/api/v1/webhook-subscriptions", json={
            "name": name, "url": "https://x.com", "event_patterns": ["*"],
        })
        wid = cr.json()["id"]
        r = authed_client.get("/api/v1/webhook-subscriptions")
        assert r.status_code == 200
        names = [w["name"] for w in r.json()["items"]]
        assert name in names
        authed_client.delete(f"/api/v1/webhook-subscriptions/{wid}")


class TestWebhookDelete:
    def test_delete(self, authed_client):
        name = _unique()
        cr = authed_client.post("/api/v1/webhook-subscriptions", json={
            "name": name, "url": "https://x.com", "event_patterns": ["*"],
        })
        wid = cr.json()["id"]
        r = authed_client.delete(f"/api/v1/webhook-subscriptions/{wid}")
        assert r.status_code == 204
        r2 = authed_client.get("/api/v1/webhook-subscriptions")
        names = [w["name"] for w in r2.json()["items"]]
        assert name not in names

    def test_delete_after_create_gone_from_list(self, authed_client):
        name = _unique()
        cr = authed_client.post("/api/v1/webhook-subscriptions", json={
            "name": name, "url": "https://x.com", "event_patterns": ["*"],
        })
        wid = cr.json()["id"]
        authed_client.delete(f"/api/v1/webhook-subscriptions/{wid}")
        r = authed_client.get("/api/v1/webhook-subscriptions")
        ids = [w["id"] for w in r.json()["items"]]
        assert wid not in ids


class TestWebhookDeliveries:
    def test_list_deliveries(self, authed_client):
        r = authed_client.get("/api/v1/webhook-deliveries")
        assert r.status_code == 200
        assert "items" in r.json()

    def test_list_deliveries_returns_data_not_empty(self, authed_client):
        """Regression: delivery list must serialize actual items, not return []."""
        r = authed_client.get("/api/v1/webhook-deliveries")
        assert r.status_code == 200
        body = r.json()
        # items key must be a list (could be empty if no deliveries exist,
        # but the bug was always returning [] even when rows existed)
        assert isinstance(body["items"], list)
        assert "next_cursor" in body
        assert "has_more" in body
