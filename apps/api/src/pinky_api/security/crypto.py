"""AES-256-GCM envelope encryption for sensitive fields.

All cluster tokens, observer bindings, and session material are encrypted
at the application level, not just database-level TDE.

Blob format: [1 byte key version][12 bytes nonce][ciphertext+tag]
AAD binds ciphertext to its storage context (table:id) to prevent relocation.
"""

import hashlib
import hmac
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_VERSION = b"\x01"


def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _get_master_key() -> bytes:
    key_hex = os.environ.get("PINKY_ENCRYPTION_KEY")
    if not key_hex:
        raise RuntimeError("PINKY_ENCRYPTION_KEY environment variable is required")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise RuntimeError("PINKY_ENCRYPTION_KEY must be 64 hex characters (32 bytes)")
    if key == b"\x00" * 32 and os.environ.get("PINKY_DEBUG") != "true":
        raise RuntimeError("All-zero encryption key is only allowed in debug/test mode")
    return key


def encrypt(plaintext: bytes, aad: str = "") -> bytes:
    key = _get_master_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    aad_bytes = aad.encode() if aad else None
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad_bytes)
    return KEY_VERSION + nonce + ciphertext


def decrypt(blob: bytes, aad: str = "") -> bytes:
    if len(blob) < 13:
        raise ValueError("Invalid encrypted blob: too short")
    version = blob[0:1]
    if version != KEY_VERSION:
        raise ValueError(f"Unknown key version: {version!r}")
    key = _get_master_key()
    nonce = blob[1:13]
    ciphertext = blob[13:]
    aesgcm = AESGCM(key)
    aad_bytes = aad.encode() if aad else None
    return aesgcm.decrypt(nonce, ciphertext, aad_bytes)


def hash_token(token: str) -> str:
    key = _get_master_key()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
