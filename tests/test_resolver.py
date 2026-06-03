"""Resolver behavior — the priority ladder, overlap rule, and floor."""

from __future__ import annotations

import datetime as dt

import pytest

from engine.config import Config, ConfigError, Settings, config_from_dict
from engine.resolver import active_routine, resolve
from tests.conftest import FakeState, routine

# A fixed Wednesday 10:00 (weekday()==2) for deterministic time-window tests.
WED_10 = dt.datetime(2026, 6, 3, 10, 0)


def cfg(routines=None, **settings):
    return Config(routines=routines or [], settings=Settings(**settings))


# ----------------------------------------------------------- priority ladder

def test_paused_beats_everything():
    s = FakeState(paused=True, in_call=True, device_connected=False)
    r = resolve(WED_10, s, cfg())
    assert r.kind == "paused"
    assert r.off is True


def test_disconnected_beats_call():
    s = FakeState(device_connected=False, in_call=True)
    r = resolve(WED_10, s, cfg())
    assert r.kind == "disconnected"
    assert r.off is True


def test_call_beats_override_and_routine():
    s = FakeState(in_call=True, manual_override={"color": "focus", "expiry": None})
    r = resolve(WED_10, s, cfg(routines=[routine(color="lunch")]))
    assert r.kind == "call"
    assert r.color == "busy"  # default call_color


def test_call_disabled_falls_through():
    s = FakeState(in_call=True)
    r = resolve(WED_10, s, cfg(call_detection=False))
    # no override, no routine, default off_behavior "off" -> floor off
    assert r.kind == "off"


def test_override_beats_routine():
    s = FakeState(manual_override={"color": "focus", "expiry": None})
    r = resolve(WED_10, s, cfg(routines=[routine(color="lunch")]))
    assert r.kind == "override"
    assert r.color == "focus"
    assert "until you clear it" in r.reason


def test_override_with_expiry_reason():
    expiry = (WED_10 + dt.timedelta(minutes=30)).isoformat()
    s = FakeState(manual_override={"color": "focus", "expiry": expiry})
    r = resolve(WED_10, s, cfg())
    assert r.kind == "override"
    assert "Focus" in r.reason


def test_routine_when_active():
    s = FakeState()
    r = resolve(WED_10, s, cfg(routines=[routine(start="09:00", end="11:00", color="lunch")]))
    assert r.kind == "routine"
    assert r.color == "lunch"


def test_routine_ignored_when_disabled():
    s = FakeState()
    r = resolve(WED_10, s, cfg(routines=[routine(enabled=False, color="lunch")]))
    assert r.kind != "routine"


def test_routine_ignored_off_day():
    # Sunday=6; routine only weekdays
    sun = dt.datetime(2026, 6, 7, 10, 0)
    s = FakeState()
    r = resolve(sun, s, cfg(routines=[routine(days=[0, 1, 2, 3, 4], color="lunch")]))
    assert r.kind != "routine"


# ----------------------------------------------------------- overlap rule

def test_overlap_later_start_wins():
    early = routine(id="early", start="09:00", end="12:00", color="lunch")
    late = routine(id="late", start="09:30", end="12:00", color="focus")
    # order shouldn't matter — later start (09:30) wins
    assert active_routine([early, late], WED_10).id == "late"
    assert active_routine([late, early], WED_10).id == "late"


# ----------------------------------------------------------- floor / off_behavior

def test_floor_off():
    r = resolve(WED_10, FakeState(), cfg(off_behavior="off"))
    assert r.kind == "off" and r.off is True


def test_floor_dim():
    r = resolve(WED_10, FakeState(), cfg(off_behavior="dim", available_color="available"))
    assert r.kind == "dim" and r.dim is True
    assert r.color == "available"


def test_floor_available_slot():
    r = resolve(WED_10, FakeState(), cfg(off_behavior="available", available_color="available"))
    assert r.kind == "available"
    assert r.color == "available"


# ----------------------------------------------------------- config validation

def test_config_rejects_midnight_span():
    with pytest.raises(ConfigError):
        config_from_dict(
            {
                "routines": [
                    {
                        "id": "x",
                        "name": "x",
                        "enabled": True,
                        "days": [0],
                        "start": "22:00",
                        "end": "02:00",
                        "color": "focus",
                    }
                ],
                "settings": {},
            }
        )


def test_config_rejects_unknown_slot():
    with pytest.raises(ConfigError):
        config_from_dict(
            {
                "routines": [
                    {
                        "id": "x",
                        "name": "x",
                        "enabled": True,
                        "days": [0],
                        "start": "09:00",
                        "end": "10:00",
                        "color": "chartreuse",
                    }
                ],
                "settings": {},
            }
        )


def test_config_rejects_duplicate_ids():
    rr = {
        "id": "dup",
        "name": "x",
        "enabled": True,
        "days": [0],
        "start": "09:00",
        "end": "10:00",
        "color": "focus",
    }
    with pytest.raises(ConfigError):
        config_from_dict({"routines": [rr, dict(rr)], "settings": {}})


def test_config_rejects_bad_off_behavior():
    with pytest.raises(ConfigError):
        config_from_dict({"routines": [], "settings": {"off_behavior": "sparkle"}})


def test_config_accepts_custom_hex_color():
    cfg = config_from_dict(
        {
            "routines": [
                {
                    "id": "x",
                    "name": "Custom",
                    "enabled": True,
                    "days": [0],
                    "start": "09:00",
                    "end": "10:00",
                    "color": "#FF00AA",
                    "effect": {"type": "strobe", "speed": 30},
                }
            ],
            "settings": {},
        }
    )
    r = cfg.routines[0]
    assert r.color == "#FF00AA"
    assert r.effect["type"] == "strobe"


def test_config_rejects_bad_hex_color():
    with pytest.raises(ConfigError):
        config_from_dict(
            {
                "routines": [
                    {
                        "id": "x",
                        "name": "x",
                        "enabled": True,
                        "days": [0],
                        "start": "09:00",
                        "end": "10:00",
                        "color": "#ZZZ",
                    }
                ],
                "settings": {},
            }
        )


def test_config_rejects_bad_effect():
    with pytest.raises(ConfigError):
        config_from_dict(
            {
                "routines": [
                    {
                        "id": "x",
                        "name": "x",
                        "enabled": True,
                        "days": [0],
                        "start": "09:00",
                        "end": "10:00",
                        "color": "focus",
                        "effect": {"type": "disco"},
                    }
                ],
                "settings": {},
            }
        )


def test_resolver_carries_routine_effect():
    r = routine(start="09:00", end="11:00", color="#112233")
    r.effect = {"type": "wave", "speed": 20, "wave_type": 2, "pattern_id": 1}
    res = resolve(WED_10, FakeState(), cfg(routines=[r]))
    assert res.color == "#112233"
    assert res.effect["type"] == "wave"


def test_resolver_carries_override_effect():
    ov = {"color": "#00FF00", "expiry": None, "effect": {"type": "strobe", "speed": 10}}
    res = resolve(WED_10, FakeState(manual_override=ov), cfg())
    assert res.kind == "override"
    assert res.color == "#00FF00"
    assert res.effect["type"] == "strobe"


def test_config_roundtrip_defaults():
    from engine.config import default_config

    d = default_config().to_dict()
    rebuilt = config_from_dict(d)
    assert len(rebuilt.routines) == 2
    assert rebuilt.settings.call_color == "busy"
