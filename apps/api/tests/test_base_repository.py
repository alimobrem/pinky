"""Base repository helper tests — cursor encoding, limit clamping."""

from __future__ import annotations

from pinky_api.repositories.base import clamp_limit, decode_cursor, encode_cursor


def test_encode_decode_cursor_roundtrip() -> None:
    data = {"v": "2026-01-01T00:00:00+00:00"}
    assert decode_cursor(encode_cursor(data)) == data


def test_encode_decode_cursor_numeric() -> None:
    data = {"v": 42}
    assert decode_cursor(encode_cursor(data)) == data


def test_clamp_limit_lower_bound() -> None:
    assert clamp_limit(0) == 1


def test_clamp_limit_negative() -> None:
    assert clamp_limit(-10) == 1


def test_clamp_limit_upper_bound() -> None:
    assert clamp_limit(500) == 200


def test_clamp_limit_at_max() -> None:
    assert clamp_limit(200) == 200


def test_clamp_limit_normal() -> None:
    assert clamp_limit(50) == 50


def test_clamp_limit_one() -> None:
    assert clamp_limit(1) == 1
