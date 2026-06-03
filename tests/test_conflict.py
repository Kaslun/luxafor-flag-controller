"""Conflict detection: StartupApproved enabled/disabled flag parsing."""

from __future__ import annotations

from engine.conflict import _disabled_flag


def test_enabled_flag_byte_02():
    # 0x02 = enabled (the user has NOT disabled it)
    assert _disabled_flag(b"\x02\x00\x00\x00\x00\x00\x00\x00") is False


def test_disabled_flag_byte_03():
    # 0x03 = disabled (the real Luxafor case the user reported)
    assert _disabled_flag(b"\x03\x00\x00\x00\xfc\xf1\x3b\x9b") is True


def test_missing_or_empty_is_enabled():
    assert _disabled_flag(b"") is False
    assert _disabled_flag(None) is False
