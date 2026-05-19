"""Tests for worker crypto — decrypt with AES-256-GCM."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from pinky_worker.security import KEY_VERSION, _get_master_key, decrypt


def _encrypt(plaintext: bytes, key: bytes, aad: str = "") -> bytes:
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    aad_bytes = aad.encode() if aad else None
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
    return KEY_VERSION + nonce + ciphertext


class TestGetMasterKey:
    def test_returns_bytes_from_hex(self) -> None:
        hex_key = os.urandom(32).hex()
        with patch.dict("os.environ", {"PINKY_ENCRYPTION_KEY": hex_key}):
            result = _get_master_key()
            assert result == bytes.fromhex(hex_key)
            assert len(result) == 32

    def test_raises_when_not_set(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(RuntimeError, match="PINKY_ENCRYPTION_KEY not set"),
        ):
            _get_master_key()


class TestDecrypt:
    def test_roundtrip(self) -> None:
        key = os.urandom(32)
        plaintext = b"my-secret-token"
        blob = _encrypt(plaintext, key)

        with patch.dict("os.environ", {"PINKY_ENCRYPTION_KEY": key.hex()}):
            result = decrypt(blob)

        assert result == plaintext

    def test_roundtrip_with_aad(self) -> None:
        key = os.urandom(32)
        plaintext = b"token-with-aad"
        aad = "cluster_identity_bindings:some-uuid"
        blob = _encrypt(plaintext, key, aad=aad)

        with patch.dict("os.environ", {"PINKY_ENCRYPTION_KEY": key.hex()}):
            result = decrypt(blob, aad=aad)

        assert result == plaintext

    def test_wrong_aad_fails(self) -> None:
        key = os.urandom(32)
        blob = _encrypt(b"token", key, aad="correct-aad")

        with (
            patch.dict("os.environ", {"PINKY_ENCRYPTION_KEY": key.hex()}),
            pytest.raises(Exception),
        ):
            decrypt(blob, aad="wrong-aad")

    def test_blob_too_short(self) -> None:
        with pytest.raises(ValueError, match="too short"):
            decrypt(b"short")

    def test_unknown_key_version(self) -> None:
        blob = b"\x99" + os.urandom(12) + b"ciphertext"
        with pytest.raises(ValueError, match="Unknown key version"):
            decrypt(blob)

    def test_wrong_key_fails(self) -> None:
        encrypt_key = os.urandom(32)
        wrong_key = os.urandom(32)
        blob = _encrypt(b"secret", encrypt_key)

        with (
            patch.dict("os.environ", {"PINKY_ENCRYPTION_KEY": wrong_key.hex()}),
            pytest.raises(Exception),
        ):
            decrypt(blob)
