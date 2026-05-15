"""Tests for apply_change identity isolation — user binding token must be used for cluster changes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ACTIVITIES = "pinky_worker.execution.activities"


class FakePool:
    def __init__(self, binding_row=None, cluster_row=None):
        self._binding_row = binding_row
        self._cluster_row = cluster_row
        self.calls: list[tuple] = []

    async def fetchrow(self, query: str, *args):
        if "cluster_identity_bindings" in query:
            return self._binding_row
        if "cluster_registry" in query:
            return self._cluster_row
        return None

    async def execute(self, query: str, *args):
        self.calls.append((query, *args))


@pytest.fixture(autouse=True)
def _mock_activity_context():
    with patch("temporalio.activity.heartbeat"):
        yield


@pytest.mark.asyncio
async def test_apply_change_uses_user_binding_token():
    """apply_change must decrypt the user's binding token and pass it to _k8s_apply."""
    from pinky_worker.execution.activities import apply_change

    binding_id = str(uuid.uuid4())
    cluster_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    fake_token = b"user-oauth-token-12345"
    api_endpoint = "https://api.cluster.example:6443"

    pool = FakePool(
        binding_row={"encrypted_token": b"encrypted-blob", "cluster_id": uuid.uuid4()},
        cluster_row={"api_endpoint": api_endpoint},
    )

    captured_args: dict = {}

    async def capture_k8s_apply(ep, token, action, kind, name, ns, params):
        captured_args.update({"endpoint": ep, "token": token, "action": action, "kind": kind, "name": name})
        return {"status": "scaled", "replicas": 3}

    step = {"action": "scale", "namespace": "default", "resource": "deployment/web", "params": {"replicas": 3}}

    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.security.decrypt", return_value=fake_token),
        patch(f"{ACTIVITIES}._k8s_apply", side_effect=capture_k8s_apply),
        patch(f"{ACTIVITIES}._emit_command_event", AsyncMock()),
    ):
        result = await apply_change(exec_id, cluster_id, binding_id, step)

    assert result["status"] == "scaled"
    assert captured_args["endpoint"] == api_endpoint
    assert captured_args["token"] == "user-oauth-token-12345"


@pytest.mark.asyncio
async def test_apply_change_raises_without_binding():
    """Without binding_id, apply_change raises (no endpoint/token available)."""
    from pinky_worker.execution.activities import apply_change

    step = {"action": "scale", "namespace": "default", "resource": "deployment/web", "params": {"replicas": 2}}

    with (
        patch(f"{ACTIVITIES}._emit_command_event", AsyncMock()),
        pytest.raises(RuntimeError, match="No cluster endpoint"),
    ):
        await apply_change(str(uuid.uuid4()), str(uuid.uuid4()), "", step)


@pytest.mark.asyncio
async def test_apply_change_never_uses_observer_when_binding_exists():
    """Verify _k8s_apply receives the user token, not observer SA."""
    from pinky_worker.execution.activities import apply_change

    binding_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    pool = FakePool(
        binding_row={"encrypted_token": b"enc", "cluster_id": uuid.uuid4()},
        cluster_row={"api_endpoint": "https://api.test:6443"},
    )

    k8s_calls = []

    async def track_k8s(ep, token, *args):
        k8s_calls.append({"endpoint": ep, "token": token})
        return {"status": "deleted"}

    step = {"action": "delete_pod", "namespace": "ns", "resource": "pod/crash-pod"}

    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.security.decrypt", return_value=b"real-user-token"),
        patch(f"{ACTIVITIES}._k8s_apply", side_effect=track_k8s),
        patch(f"{ACTIVITIES}._emit_command_event", AsyncMock()),
    ):
        await apply_change(exec_id, "cluster", binding_id, step)

    assert len(k8s_calls) == 1
    assert k8s_calls[0]["token"] == "real-user-token"
    assert k8s_calls[0]["endpoint"] == "https://api.test:6443"


@pytest.mark.asyncio
async def test_command_sequence_uses_step_index():
    """Command events must use step-specific sequence numbers."""
    from pinky_worker.execution.activities import apply_change

    emit_calls = []

    async def capture_emit(pool, eid, seq, cmd, output, exit_code, action, resource):
        emit_calls.append({"seq": seq})

    pool = FakePool(
        binding_row={"encrypted_token": b"enc", "cluster_id": uuid.uuid4()},
        cluster_row={"api_endpoint": "https://api.test:6443"},
    )

    for step_idx in [0, 1, 2]:
        emit_calls.clear()
        step = {
            "action": "scale", "namespace": "default", "resource": "deployment/web",
            "params": {"replicas": 3}, "_step_index": step_idx,
        }

        with (
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
            patch("pinky_worker.security.decrypt", return_value=b"token"),
            patch(f"{ACTIVITIES}._k8s_apply", AsyncMock(return_value={"status": "scaled"})),
            patch(f"{ACTIVITIES}._emit_command_event", side_effect=capture_emit),
        ):
            await apply_change(str(uuid.uuid4()), "cluster", str(uuid.uuid4()), step)

        assert emit_calls[0]["seq"] == 500 + step_idx * 10


@pytest.mark.asyncio
async def test_k8s_apply_patch_handles_string_body():
    """_k8s_apply must handle patch body that's already a JSON string."""
    from pinky_worker.execution.activities import _k8s_apply

    captured: dict = {}

    async def mock_patch(url, **kwargs):
        captured["body"] = kwargs.get("content", "")
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        return resp

    mock_client = AsyncMock()
    mock_client.patch = mock_patch
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await _k8s_apply(
            "https://api.test:6443", "token", "patch",
            "deployment", "web", "default",
            {"patch": '{"spec":{"replicas":3}}'},
        )

    # Should NOT double-encode — body should be the raw string, not '"{\\"spec\\"...}"'
    assert captured["body"] == '{"spec":{"replicas":3}}'
    assert '\\"' not in captured["body"]


@pytest.mark.asyncio
async def test_k8s_apply_patch_uses_strategic_merge():
    """_k8s_apply must use strategic-merge-patch content type."""
    from pinky_worker.execution.activities import _k8s_apply

    captured_request: dict = {}

    async def mock_patch(url, **kwargs):
        captured_request["url"] = str(url)
        captured_request["headers"] = kwargs.get("headers", {})
        captured_request["body"] = kwargs.get("content", "")
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {"kind": "Deployment"}
        return resp

    mock_client = AsyncMock()
    mock_client.patch = mock_patch
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _k8s_apply(
            "https://api.test:6443", "token", "patch",
            "deployment", "web", "default", {"patch": {"spec": {"replicas": 3}}},
        )

    assert result["status"] == "patched"
    assert captured_request["headers"]["Content-Type"] == "application/strategic-merge-patch+json"
    assert '"replicas": 3' in captured_request["body"]
