"""AES-256-GCM envelope encryption for sensitive fields.

All cluster tokens, observer bindings, and session material are encrypted
at the application level, not just database-level TDE.
"""

import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _get_master_key() -> bytes:
    key_hex = os.environ.get("PINKY_ENCRYPTION_KEY")
    if not key_hex:
        raise RuntimeError("PINKY_ENCRYPTION_KEY environment variable is required")
    key = bytes.fromhex(key_hex)
    if len(key) != 32:
        raise RuntimeError("PINKY_ENCRYPTION_KEY must be 64 hex characters (32 bytes)")
    return key


def encrypt(plaintext: bytes) -> bytes:
    key = _get_master_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt(blob: bytes) -> bytes:
    key = _get_master_key()
    nonce = blob[:12]
    ciphertext = blob[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
