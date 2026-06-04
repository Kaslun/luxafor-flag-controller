"""Effects: report-byte construction and validation."""

from __future__ import annotations

import pytest

from engine.effects import (
    DEFAULT_EFFECT,
    EffectError,
    build_report,
    is_solid,
    normalize_effect,
)


def test_solid_report_is_validated_static_command():
    # the proven command: [id, 0x01, all-LEDs, R, G, B, 0, 0]
    assert build_report((10, 20, 30), None) == [0x00, 0x01, 0xFF, 10, 20, 30, 0, 0]
    assert build_report((10, 20, 30), {"type": "solid"}) == [0, 1, 255, 10, 20, 30, 0, 0]


def test_strobe_report():
    r = build_report((255, 0, 0), {"type": "strobe", "speed": 30})
    assert r[:3] == [0x00, 0x03, 0xFF]
    assert r[3:6] == [255, 0, 0]
    assert r[6] == 30  # speed


def test_fade_report():
    r = build_report((0, 255, 0), {"type": "fade", "speed": 50})
    assert r[:3] == [0x00, 0x02, 0xFF]
    assert r[6] == 50


def test_wave_report_uses_wave_type_and_speed():
    r = build_report((0, 0, 255), {"type": "wave", "wave_type": 3, "speed": 40})
    assert r[0:2] == [0x00, 0x04]
    assert r[2] == 3  # wave_type in the target byte
    assert r[3:6] == [0, 0, 255]
    assert r[7] == 40  # speed in the last byte


def test_pattern_report_ignores_color():
    r = build_report((123, 45, 67), {"type": "pattern", "pattern_id": 5})
    assert r[0:3] == [0x00, 0x06, 5]
    # color bytes are not present; pattern is a firmware animation
    assert r[3:] == [0, 0, 0, 0, 0]


def test_speed_is_clamped():
    e = normalize_effect({"type": "strobe", "speed": 9999})
    assert e["speed"] == 255
    e2 = normalize_effect({"type": "strobe", "speed": -5})
    assert e2["speed"] == 0


def test_normalize_fills_defaults():
    e = normalize_effect(None)
    assert e == DEFAULT_EFFECT
    assert e is not DEFAULT_EFFECT  # fresh copy


def test_normalize_rejects_unknown_type():
    with pytest.raises(EffectError):
        normalize_effect({"type": "sparkle"})


def test_normalize_rejects_out_of_range():
    with pytest.raises(EffectError):
        normalize_effect({"type": "wave", "wave_type": 99})
    with pytest.raises(EffectError):
        normalize_effect({"type": "pattern", "pattern_id": 0})


def test_is_solid():
    assert is_solid(None)
    assert is_solid({"type": "solid"})
    assert not is_solid({"type": "strobe"})


def test_report_is_pattern():
    from engine.effects import PATTERN_OFF_REPORT, report_is_pattern

    assert report_is_pattern(build_report((0, 0, 0), {"type": "pattern", "pattern_id": 5}))
    assert not report_is_pattern(build_report((1, 2, 3), None))  # solid
    assert not report_is_pattern(build_report((1, 2, 3), {"type": "strobe"}))
    assert not report_is_pattern(PATTERN_OFF_REPORT)  # id 0 = off, not running
    assert not report_is_pattern(None)
