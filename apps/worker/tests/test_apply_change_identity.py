"""Tests for apply_change identity isolation — user binding token must be used for cluster changes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


ACTIVITIES = "pinky_worker.execution.activities"
K8S_CLIENT = "pinky_worker.observation.k8s_client"


@pytest.fixture(autouse=True)
def _mock_activity_context():
    with patch("temporalio.activity.heartbeat"):
        yield


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


@pytest.mark.asyncio
async def test_apply_change_uses_user_binding_token():
    """apply_change must decrypt the user's binding token and pass it to create_client."""
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

    mock_k8s = MagicMock()
    mock_k8s.close = AsyncMock()
    captured_create_args: dict = {}

    async def capture_create_client(**kwargs):
        captured_create_args.update(kwargs)
        return mock_k8s

    step = {"action": "scale", "namespace": "default", "resource": "deployment/web", "params": {"replicas": 3}}

    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
        patch(f"{K8S_CLIENT}.create_client", side_effect=capture_create_client) as mock_create,
        patch("pinky_worker.security.decrypt", return_value=fake_token),
        patch(f"{K8S_CLIENT}.scale_deployment", AsyncMock(return_value={"status": "scaled", "replicas": 3})),
    ):
        result = await apply_change(exec_id, cluster_id, binding_id, step)

    assert result["status"] == "scaled"
    assert captured_create_args["api_endpoint"] == api_endpoint
    assert captured_create_args["token"] == "user-oauth-token-12345"


@pytest.mark.asyncio
async def test_apply_change_falls_back_to_observer_without_binding():
    """Without binding_id, apply_change falls back to observer SA (create_client with no args)."""
    from pinky_worker.execution.activities import apply_change

    exec_id = str(uuid.uuid4())
    cluster_id = str(uuid.uuid4())

    mock_k8s = MagicMock()
    mock_k8s.close = AsyncMock()
    captured_create_args: dict = {}

    async def capture_create_client(**kwargs):
        captured_create_args.update(kwargs)
        return mock_k8s

    step = {"action": "scale", "namespace": "default", "resource": "deployment/web", "params": {"replicas": 2}}

    with (
        patch(f"{K8S_CLIENT}.create_client", side_effect=capture_create_client),
        patch(f"{K8S_CLIENT}.scale_deployment", AsyncMock(return_value={"status": "scaled", "replicas": 2})),
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=FakePool())),
    ):
        result = await apply_change(exec_id, cluster_id, "", step)

    assert result["status"] == "scaled"
    assert captured_create_args.get("api_endpoint") is None
    assert captured_create_args.get("token") is None


@pytest.mark.asyncio
async def test_apply_change_never_uses_observer_when_binding_exists():
    """Even if token decryption works, verify create_client receives the user token, not None."""
    from pinky_worker.execution.activities import apply_change

    binding_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    cluster_id = str(uuid.uuid4())

    pool = FakePool(
        binding_row={"encrypted_token": b"enc", "cluster_id": uuid.uuid4()},
        cluster_row={"api_endpoint": "https://api.test:6443"},
    )

    create_client_calls = []

    async def track_create(**kwargs):
        create_client_calls.append(kwargs)
        mock = MagicMock()
        mock.close = AsyncMock()
        return mock

    step = {"action": "delete_pod", "namespace": "ns", "resource": "pod/crash-pod"}

    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
        patch(f"{K8S_CLIENT}.create_client", side_effect=track_create),
        patch("pinky_worker.security.decrypt", return_value=b"real-user-token"),
        patch(f"{K8S_CLIENT}.delete_pod", AsyncMock(return_value={"status": "deleted"})),
    ):
        await apply_change(exec_id, cluster_id, binding_id, step)

    assert len(create_client_calls) == 1
    assert create_client_calls[0]["token"] == "real-user-token"
    assert create_client_calls[0]["api_endpoint"] == "https://api.test:6443"


@pytest.mark.asyncio
async def test_command_sequence_uses_step_index():
    """Command events must use step-specific sequence numbers, not hardcoded 500."""
    from pinky_worker.execution.activities import apply_change

    exec_id = str(uuid.uuid4())
    emit_calls = []

    original_emit = None

    async def capture_emit(pool, eid, seq, cmd, output, exit_code, action, resource):
        emit_calls.append({"seq": seq, "cmd": cmd})

    mock_k8s = MagicMock()
    mock_k8s.close = AsyncMock()

    for step_idx in [0, 1, 2]:
        emit_calls.clear()
        step = {
            "action": "scale", "namespace": "default", "resource": "deployment/web",
            "params": {"replicas": 3}, "_step_index": step_idx,
        }

        with (
            patch(f"{K8S_CLIENT}.create_client", AsyncMock(return_value=mock_k8s)),
            patch(f"{K8S_CLIENT}.scale_deployment", AsyncMock(return_value={"status": "scaled"})),
            patch("pinky_worker.db.get_pool", AsyncMock(return_value=FakePool())),
            patch(f"{ACTIVITIES}._emit_command_event", side_effect=capture_emit),
        ):
            await apply_change(exec_id, "cluster", "", step)

        assert emit_calls[0]["seq"] == 500 + step_idx * 10


def test_create_client_with_token_sets_bearer_auth():
    """create_client with api_endpoint+token must configure bearer auth, not SA token."""
    import asyncio
    from pinky_worker.observation.k8s_client import create_client

    async def run():
        client = await create_client(
            api_endpoint="https://api.test:6443",
            token="user-token-xyz",
        )
        cfg = client.configuration
        assert cfg.host == "https://api.test:6443"
        assert cfg.api_key.get("BearerToken") == "user-token-xyz"
        assert cfg.verify_ssl is False
        await client.close()

    asyncio.get_event_loop().run_until_complete(run())
