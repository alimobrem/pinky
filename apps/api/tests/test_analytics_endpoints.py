"""Tests for analytics endpoints."""


class TestAnalyticsRoi:
    def test_roi_default_period(self, authed_client):
        r = authed_client.get("/api/v1/analytics/roi")
        assert r.status_code == 200
        data = r.json()
        assert "metrics" in data
        m = data["metrics"]
        assert "issues_total" in m
        assert "issues_resolved" in m
        assert "tasks_total" in m
        assert "tasks_completed" in m
        assert "executions_total" in m
        assert "task_completion_rate" in m

    def test_roi_7d_period(self, authed_client):
        r = authed_client.get("/api/v1/analytics/roi?since=7d")
        assert r.status_code == 200

    def test_roi_90d_period(self, authed_client):
        r = authed_client.get("/api/v1/analytics/roi?since=90d")
        assert r.status_code == 200


class TestAnalyticsScanners:
    def test_scanners_default(self, authed_client):
        r = authed_client.get("/api/v1/analytics/scanners")
        assert r.status_code == 200
        data = r.json()
        assert "scanners" in data
        assert isinstance(data["scanners"], list)

    def test_scanners_90d(self, authed_client):
        r = authed_client.get("/api/v1/analytics/scanners?since=90d")
        assert r.status_code == 200


class TestAnalyticsExport:
    def test_export_json(self, authed_client):
        r = authed_client.get("/api/v1/analytics/export?format=json")
        assert r.status_code == 200
        data = r.json()
        assert "roi" in data or "metrics" in data or "scanners" in data
