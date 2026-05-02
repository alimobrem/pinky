import os

import pytest

from pinky_api.security.crypto import decrypt, encrypt, generate_csrf_token, generate_session_token, hash_token


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key = os.urandom(32).hex()
    monkeypatch.setenv("PINKY_ENCRYPTION_KEY", key)


def test_encrypt_decrypt_roundtrip() -> None:
    plaintext = b"cluster-token-secret-value"
    blob = encrypt(plaintext)
    assert blob != plaintext
    result = decrypt(blob)
    assert result == plaintext


def test_encrypt_decrypt_with_aad() -> None:
    plaintext = b"cluster-token"
    aad = "cluster_identity_bindings:abc-123"
    blob = encrypt(plaintext, aad=aad)
    result = decrypt(blob, aad=aad)
    assert result == plaintext


def test_aad_mismatch_fails() -> None:
    plaintext = b"secret"
    blob = encrypt(plaintext, aad="table_a:row_1")
    with pytest.raises(Exception):
        decrypt(blob, aad="table_b:row_2")


def test_key_version_prefix() -> None:
    blob = encrypt(b"test")
    assert blob[0:1] == b"\x01"


def test_different_encryptions_produce_different_blobs() -> None:
    plaintext = b"same-input"
    blob1 = encrypt(plaintext)
    blob2 = encrypt(plaintext)
    assert blob1 != blob2


def test_tampered_blob_fails() -> None:
    plaintext = b"secret"
    blob = encrypt(plaintext)
    tampered = blob[:-1] + bytes([blob[-1] ^ 0xFF])
    with pytest.raises(Exception):
        decrypt(tampered)


def test_session_token_is_url_safe() -> None:
    token = generate_session_token()
    assert len(token) > 32
    assert " " not in token


def test_csrf_token_is_url_safe() -> None:
    token = generate_csrf_token()
    assert len(token) > 20


def test_hash_token_deterministic() -> None:
    token = "my-token"
    h1 = hash_token(token)
    h2 = hash_token(token)
    assert h1 == h2
    assert h1 != token
