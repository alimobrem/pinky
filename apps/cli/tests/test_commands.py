"""CLI command tests — all commands against mocked API."""

from __future__ import annotations

import tempfile

import httpx
import pytest
import typer

from pinky_cli import main


def _mock_get(monkeypatch, response: dict):
    calls: list[tuple[str, dict | None]] = []

    def fake(path: str, params: dict | None = None) -> dict:
        calls.append((path, params))
        return response

    monkeypatch.setattr(main, "_get", fake)
    return calls


def _mock_post(monkeypatch, response: dict):
    calls: list[tuple[str, dict | None]] = []

    def fake(path: str, data: dict | None = None) -> dict:
        calls.append((path, data))
        return response

    monkeypatch.setattr(main, "_post", fake)
    return calls


def test_post_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeResponse:
        status_code = 200
        text = "ok"

        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "accepted"}

    monkeypatch.setattr(main.httpx, "post", lambda *a, **kw: _FakeResponse())
    result = main._post("/api/v1/work-items/123/accept")
    assert result == {"status": "accepted"}


def test_post_raises_exit_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", f"{main.API_URL}/test")
    response = httpx.Response(500, request=request, text="boom")

    def fake_post(*a, **kw):
        class _Err:
            status_code = 500
            text = "boom"

            def raise_for_status(self):
                raise httpx.HTTPStatusError("fail", request=request, response=response)

            def json(self):
                return {}

        return _Err()

    monkeypatch.setattr(main.httpx, "post", fake_post)

    with pytest.raises(typer.Exit) as exc_info:
        main._post("/test")
    assert exc_info.value.exit_code == 1


def test_post_missing_connect_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(*a, **kw):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(main.httpx, "post", fake_post)

    with pytest.raises((typer.Exit, httpx.ConnectError)):
        main._post("/test")


def test_tasks_accept(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_post(monkeypatch, {"title": "Fix pod"})
    main.tasks_accept("task-123")
    assert calls == [("/api/v1/work-items/task-123/accept", None)]


def test_tasks_start(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_post(monkeypatch, {"title": "Fix pod"})
    main.tasks_start("task-456")
    assert calls == [("/api/v1/work-items/task-456/start", None)]


def test_tasks_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_post(monkeypatch, {"title": "Fix pod"})
    main.tasks_complete("task-789")
    assert calls == [("/api/v1/work-items/task-789/complete", None)]


def test_clusters_list(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_get(monkeypatch, {
        "items": [
            {
                "id": "c1-uuid-long", "display_name": "prod",
                "api_endpoint": "https://api:6443", "onboarding_state": "ready",
            },
        ],
    })
    main.clusters_list()
    assert calls == [("/api/v1/clusters", None)]


def test_definitions_list(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_get(monkeypatch, {
        "items": [{"kind": "scanner", "name": "pod-health", "version": "1.0.0", "enabled": True}],
    })
    main.definitions_list(kind="scanner")
    assert calls == [("/api/v1/definitions", {"kind": "scanner"})]


def test_definitions_list_no_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_get(monkeypatch, {"items": []})
    main.definitions_list(kind=None)
    assert calls == [("/api/v1/definitions", {})]


def test_definitions_create(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_post(monkeypatch, {"id": "def-1"})

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("---\nkind: scanner\nname: test-scan\nversion: 2.0.0\n---\nBody content here\n")
        f.flush()
        main.definitions_create(f.name)

    assert len(calls) == 1
    assert calls[0][0] == "/api/v1/definitions"
    assert calls[0][1]["kind"] == "scanner"
    assert calls[0][1]["name"] == "test-scan"
    assert calls[0][1]["version"] == "2.0.0"
    assert "Body content" in calls[0][1]["body"]


def test_definitions_create_rejects_no_frontmatter(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("No frontmatter here\n")
        f.flush()
        with pytest.raises(typer.Exit):
            main.definitions_create(f.name)


def test_analytics_roi_table(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_get(monkeypatch, {
        "period": "30d",
        "metrics": {"hours_saved": 42, "tasks_completed": 15},
    })
    main.analytics_roi(since="30d", format="table")
    assert calls == [("/api/v1/analytics/roi", {"since": "30d"})]


def test_analytics_roi_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_get(monkeypatch, {"period": "7d", "metrics": {}})
    main.analytics_roi(since="7d", format="json")
    assert calls[0][1] == {"since": "7d"}


def test_analytics_scanners_table(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_get(monkeypatch, {
        "scanners": [{"scanner": "pod-health", "signal_total": 42}],
    })
    main.analytics_scanners(format="table")
    assert calls == [("/api/v1/analytics/scanners", None)]


def test_analytics_scanners_json(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _mock_get(monkeypatch, {"scanners": []})
    main.analytics_scanners(format="json")
    assert calls == [("/api/v1/analytics/scanners", None)]
