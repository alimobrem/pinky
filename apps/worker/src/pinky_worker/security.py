"""Minimal crypto for decrypting cluster binding tokens — mirrors pinky_api.security.crypto."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_VERSION = b"\x01"


def _get_master_key() -> bytes:
    hex_key = os.environ.get("PINKY_ENCRYPTION_KEY", "")
    if not hex_key:
        raise RuntimeError("PINKY_ENCRYPTION_KEY not set")
    return bytes.fromhex(hex_key)


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
