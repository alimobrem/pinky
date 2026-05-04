import httpx
import pytest
import typer

from pinky_cli import main


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200
        self.text = "ok"

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_get_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, params: dict | None = None, timeout: int = 10) -> _FakeResponse:
        assert url == f"{main.API_URL}/api/v1/work-items"
        assert params == {"status": "ready"}
        assert timeout == 10
        return _FakeResponse({"items": []})

    monkeypatch.setattr(main.httpx, "get", fake_get)

    result = main._get("/api/v1/work-items", {"status": "ready"})

    assert result == {"items": []}


def test_get_raises_exit_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", f"{main.API_URL}/api/v1/work-items")
    response = httpx.Response(500, request=request, text="boom")

    def fake_get(url: str, params: dict | None = None, timeout: int = 10) -> _FakeResponse:
        class _ErrorResponse(_FakeResponse):
            def raise_for_status(self) -> None:
                raise httpx.HTTPStatusError("server error", request=request, response=response)

        return _ErrorResponse({})

    monkeypatch.setattr(main.httpx, "get", fake_get)

    with pytest.raises(typer.Exit) as exc_info:
        main._get("/api/v1/work-items")

    assert exc_info.value.exit_code == 1


def test_tasks_list_passes_filters_to_api(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict | None]] = []

    def fake_get(path: str, params: dict | None = None) -> dict:
        calls.append((path, params))
        return {
            "items": [
                {
                    "id": "1234567890",
                    "title": "Investigate pod restarts",
                    "status": "ready",
                    "priority": "high",
                    "confidence": 0.9,
                }
            ]
        }

    monkeypatch.setattr(main, "_get", fake_get)

    main.tasks_list(status="ready", cluster="cluster-a")

    assert calls == [
        ("/api/v1/work-items", {"status": "ready", "cluster_id": "cluster-a"})
    ]
