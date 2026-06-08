"""Resolver behavior — the priority ladder, overlap rule, and floor."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pytest

from engine.config import Config, ConfigError, Routine, Settings, config_from_dict
from engine.resolver import active_routine, resolve

# A fixed Wednesday 10:00 (weekday()==2) for deterministic time-window tests.
WED_10 = dt.datetime(2026, 6, 3, 10, 0)


# Lightweight stand-in for the live engine State — the resolver only
# duck-types these attributes, so we don't need the real threaded State.
# Kept local (not in conftest) so the test module has no cross-module import.
@dataclass
class FakeState:
    paused: bool = False
    device_connected: bool = True
    in_call: bool = False
    locked: bool = False
    manual_override: dict | None = None
    preview: dict | None = None
    active_triggers: list = field(default_factory=list)


def trig(id="t", name="T", color="busy", priority=70, effect=None):
    """A firing-trigger dict as the loop hands it to the resolver."""
    return {"id": id, "name": name, "color": color, "priority": priority, "effect": effect}


def routine(**kw) -> Routine:
    base = dict(
        id="r",
        name="R",
        enabled=True,
        days=[0, 1, 2, 3, 4, 5, 6],
        start="09:00",
        end="17:00",
        color="available",
    )
    base.update(kw)
    return Routine(**base)


def cfg(routines=None, **settings):
    return Config(routines=routines or [], settings=Settings(**settings))


# ----------------------------------------------------------- priority ladder

def test_paused_beats_everything():
    s = FakeState(paused=True, device_connected=False, active_triggers=[trig()])
    r = resolve(WED_10, s, cfg())
    assert r.kind == "paused"
    assert r.off is True


def test_disconnected_beats_trigger():
    s = FakeState(device_connected=False, active_triggers=[trig()])
    r = resolve(WED_10, s, cfg())
    assert r.kind == "disconnected"
    assert r.off is True


def test_preview_beats_trigger_and_override():
    s = FakeState(
        active_triggers=[trig()],
        manual_override={"color": "focus", "expiry": None},
        preview={"color": "#123456", "effect": {"type": "solid"}},
    )
    r = resolve(WED_10, s, cfg())
    assert r.kind == "preview"
    assert r.color == "#123456"


def test_active_trigger_resolves():
    s = FakeState(active_triggers=[trig(name="Screen locked", color="away")])
    r = resolve(WED_10, s, cfg())
    assert r.kind == "trigger"
    assert r.color == "away"
    assert "Screen locked" in r.reason


def test_highest_priority_trigger_wins():
    s = FakeState(
        active_triggers=[
            trig(id="lo", color="lunch", priority=40),
            trig(id="hi", color="focus", priority=90),
        ]
    )
    r = resolve(WED_10, s, cfg())
    assert r.kind == "trigger"
    assert r.color == "focus"


def test_trigger_beats_override_when_higher():
    s = FakeState(
        active_triggers=[trig(color="busy", priority=70)],
        manual_override={"color": "focus", "expiry": None},
    )
    r = resolve(WED_10, s, cfg(routines=[routine(color="lunch")]))
    assert r.kind == "trigger"
    assert r.color == "busy"


def test_override_beats_trigger_when_lower_or_equal():
    # priority == OVERRIDE_PRIORITY (50): override wins (strictly-greater rule)
    s = FakeState(
        active_triggers=[trig(color="busy", priority=50)],
        manual_override={"color": "focus", "expiry": None},
    )
    r = resolve(WED_10, s, cfg())
    assert r.kind == "override"
    assert r.color == "focus"


def test_no_active_triggers_falls_through():
    s = FakeState(active_triggers=[])
    r = resolve(WED_10, s, cfg(off_behavior="off"))
    assert r.kind == "off"


def test_override_beats_routine():
    s = FakeState(manual_override={"color": "focus", "expiry": None})
    r = resolve(WED_10, s, cfg(routines=[routine(color="lunch")]))
    assert r.kind == "override"
    assert r.color == "focus"
    assert r.reason == "Manual"


def test_override_reason_is_minimal():
    expiry = (WED_10 + dt.timedelta(minutes=30)).isoformat()
    s = FakeState(manual_override={"color": "focus", "expiry": expiry})
    r = resolve(WED_10, s, cfg())
    assert r.kind == "override"
    assert r.reason == "Manual"


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


def test_config_accepts_unknown_slot_reference():
    # palette is editable, so any slot-name token is accepted and resolved at
    # runtime (falls back to black if the slot was deleted) — only bad hex fails
    cfg = config_from_dict(
        {
            "routines": [
                {
                    "id": "x",
                    "name": "x",
                    "enabled": True,
                    "days": [0],
                    "start": "09:00",
                    "end": "10:00",
                    "color": "my_custom_slot",
                }
            ],
            "settings": {},
        }
    )
    assert cfg.routines[0].color == "my_custom_slot"


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
    # a slot-name off_behavior is accepted (resolves to the resting colour);
    # only a malformed hex is rejected
    with pytest.raises(ConfigError):
        config_from_dict({"routines": [], "settings": {"off_behavior": "#ZZZ"}})


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
    assert len(rebuilt.triggers) == 2
    assert len(rebuilt.palette) == 6
    assert rebuilt.settings.available_color == "available"
    assert rebuilt.settings.brightness == 80
