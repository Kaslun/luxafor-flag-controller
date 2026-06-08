"""Editable palette + brightness: config parsing, defaults, migration."""

from __future__ import annotations

import pytest

from engine.config import config_from_dict, default_config, ConfigError


def test_default_palette_has_six_with_one_off():
    cfg = default_config()
    assert len(cfg.palette) == 6
    offs = [c for c in cfg.palette if c.off]
    assert len(offs) == 1 and offs[0].slot == "off"
    # the default seed carries LED-tuned hex for non-off slots
    avail = next(c for c in cfg.palette if c.slot == "available")
    assert avail.led is not None


def test_config_without_palette_migrates_to_default():
    cfg = config_from_dict({"routines": [], "triggers": [], "settings": {}})
    assert len(cfg.palette) == 6


def test_custom_palette_roundtrips():
    pal = [
        {"slot": "available", "name": "Free", "hex": "#11FF22"},
        {"slot": "c1", "name": "Teal", "hex": "#00CCBB", "led": "#00FFCC"},
        {"slot": "off", "name": "Off", "off": True},
    ]
    cfg = config_from_dict({"routines": [], "triggers": [], "palette": pal, "settings": {}})
    by = {c.slot: c for c in cfg.palette}
    assert by["available"].hex == "#11FF22"
    assert by["c1"].led == "#00FFCC"
    assert by["off"].off is True


def test_palette_rejects_duplicate_slots():
    pal = [
        {"slot": "x", "name": "X", "hex": "#111111"},
        {"slot": "x", "name": "Y", "hex": "#222222"},
        {"slot": "off", "name": "Off", "off": True},
    ]
    with pytest.raises(ConfigError):
        config_from_dict({"routines": [], "palette": pal, "settings": {}})


def test_palette_requires_exactly_one_off():
    with pytest.raises(ConfigError):
        config_from_dict(
            {"routines": [], "palette": [{"slot": "a", "name": "A", "hex": "#111111"}], "settings": {}}
        )


def test_palette_rejects_bad_hex():
    pal = [
        {"slot": "a", "name": "A", "hex": "nothex"},
        {"slot": "off", "name": "Off", "off": True},
    ]
    with pytest.raises(ConfigError):
        config_from_dict({"routines": [], "palette": pal, "settings": {}})


def test_brightness_clamped_and_parsed():
    cfg = config_from_dict({"routines": [], "settings": {"brightness": 250}})
    assert cfg.settings.brightness == 100
    cfg2 = config_from_dict({"routines": [], "settings": {"brightness": 1}})
    assert cfg2.settings.brightness == 10
    cfg3 = config_from_dict({"routines": [], "settings": {}})
    assert cfg3.settings.brightness == 80


def test_loop_resolves_palette_and_brightness(monkeypatch):
    # _palette_rgb resolves a slot's led hex; _scaled applies brightness
    from engine.loop import BeaconEngine

    eng = BeaconEngine()
    eng.config = config_from_dict(
        {
            "routines": [],
            "triggers": [],
            "palette": [
                {"slot": "busy", "name": "Busy", "hex": "#FF0000", "led": "#FF0000"},
                {"slot": "off", "name": "Off", "off": True},
            ],
            "settings": {"brightness": 50},
        }
    )
    assert eng._palette_rgb("busy") == (255, 0, 0)
    assert eng._palette_rgb("off") == (0, 0, 0)
    assert eng._palette_rgb("gone") == (0, 0, 0)  # deleted slot -> black
    assert eng._palette_rgb("#00FF00") == (0, 255, 0)
    # brightness 50 halves the channels
    assert eng._scaled((200, 100, 0)) == (100, 50, 0)
