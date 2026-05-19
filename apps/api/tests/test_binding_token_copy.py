"""Tests for _copy_token_from_sibling binding token propagation."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pinky_api.fleet.routes import _copy_token_from_sibling


def _make_binding(
    binding_id: uuid.UUID | None = None,
    encrypted_token: bytes | None = None,
    status: str = "valid",
) -> MagicMock:
    b = MagicMock()
    b.id = binding_id or uuid.uuid4()
    b.encrypted_token = encrypted_token
    b.status = status
    return b


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_copies_token_from_valid_sibling(mock_repo: AsyncMock) -> None:
    target = _make_binding(encrypted_token=None)
    sibling = _make_binding(encrypted_token=b"enc-data", status="valid")
    mock_repo.list_for_principal.return_value = [target, sibling]

    with (
        patch("pinky_api.security.crypto.decrypt", return_value=b"raw-token") as mock_decrypt,
        patch("pinky_api.fleet.routes.encrypt", return_value=b"re-encrypted") as mock_encrypt,
    ):
        await _copy_token_from_sibling(mock_repo, uuid.uuid4(), target)

    mock_decrypt.assert_called_once()
    mock_encrypt.assert_called_once_with(
        b"raw-token", aad=f"cluster_identity_bindings:{target.id}",
    )
    mock_repo.refresh_token.assert_called_once_with(target.id, b"re-encrypted")


@pytest.mark.asyncio
async def test_skips_self(mock_repo: AsyncMock) -> None:
    target = _make_binding(encrypted_token=b"has-token")
    mock_repo.list_for_principal.return_value = [target]

    await _copy_token_from_sibling(mock_repo, uuid.uuid4(), target)
    mock_repo.refresh_token.assert_not_called()


@pytest.mark.asyncio
async def test_skips_siblings_without_token(mock_repo: AsyncMock) -> None:
    target = _make_binding(encrypted_token=None)
    sibling = _make_binding(encrypted_token=None, status="valid")
    mock_repo.list_for_principal.return_value = [target, sibling]

    await _copy_token_from_sibling(mock_repo, uuid.uuid4(), target)
    mock_repo.refresh_token.assert_not_called()


@pytest.mark.asyncio
async def test_skips_revoked_siblings(mock_repo: AsyncMock) -> None:
    target = _make_binding(encrypted_token=None)
    sibling = _make_binding(encrypted_token=b"enc-data", status="revoked")
    mock_repo.list_for_principal.return_value = [target, sibling]

    await _copy_token_from_sibling(mock_repo, uuid.uuid4(), target)
    mock_repo.refresh_token.assert_not_called()


@pytest.mark.asyncio
async def test_accepts_expiring_sibling(mock_repo: AsyncMock) -> None:
    target = _make_binding(encrypted_token=None)
    sibling = _make_binding(encrypted_token=b"enc-data", status="expiring")
    mock_repo.list_for_principal.return_value = [target, sibling]

    with (
        patch("pinky_api.security.crypto.decrypt", return_value=b"raw-token"),
        patch("pinky_api.fleet.routes.encrypt", return_value=b"re-encrypted"),
    ):
        await _copy_token_from_sibling(mock_repo, uuid.uuid4(), target)

    mock_repo.refresh_token.assert_called_once()


@pytest.mark.asyncio
async def test_continues_on_decrypt_failure(mock_repo: AsyncMock) -> None:
    target = _make_binding(encrypted_token=None)
    bad_sibling = _make_binding(encrypted_token=b"corrupt", status="valid")
    good_sibling = _make_binding(encrypted_token=b"good", status="valid")
    mock_repo.list_for_principal.return_value = [target, bad_sibling, good_sibling]

    call_count = 0

    def side_effect(blob, aad=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("decrypt failed")
        return b"raw-token"

    with (
        patch("pinky_api.security.crypto.decrypt", side_effect=side_effect),
        patch("pinky_api.fleet.routes.encrypt", return_value=b"re-encrypted"),
    ):
        await _copy_token_from_sibling(mock_repo, uuid.uuid4(), target)

    mock_repo.refresh_token.assert_called_once()


@pytest.mark.asyncio
async def test_no_siblings_does_nothing(mock_repo: AsyncMock) -> None:
    target = _make_binding(encrypted_token=None)
    mock_repo.list_for_principal.return_value = [target]

    await _copy_token_from_sibling(mock_repo, uuid.uuid4(), target)
    mock_repo.refresh_token.assert_not_called()
