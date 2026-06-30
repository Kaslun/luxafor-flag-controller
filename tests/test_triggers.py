"""Trigger config: validation, legacy migration, and mic_app matching."""

from __future__ import annotations

import pytest

from engine import mic
from engine.config import (
    ConfigError,
    config_from_dict,
    default_config,
    triggers_meta,
)


def _trigger(**kw) -> dict:
    base = {
        "id": "t1",
        "name": "T",
        "enabled": True,
        "type": "mic",
        "color": "busy",
        "priority": 70,
        "params": {},
    }
    base.update(kw)
    return base


# ----------------------------------------------------------- validation

def test_accepts_all_known_types():
    from engine.config import TRIGGER_TYPES

    for t in TRIGGER_TYPES:
        params = {"app": "teams"} if t in ("mic_app", "foreground", "process") else {}
        if t == "idle":
            params = {"minutes": 10}
        cfg = config_from_dict(
            {"routines": [], "triggers": [_trigger(type=t, params=params)], "settings": {}}
        )
        assert cfg.triggers[0].type == t


def test_rejects_unknown_type():
    with pytest.raises(ConfigError):
        config_from_dict(
            {"routines": [], "triggers": [_trigger(type="telepathy")], "settings": {}}
        )


def test_priority_is_clamped():
    cfg = config_from_dict(
        {"routines": [], "triggers": [_trigger(priority=9999)], "settings": {}}
    )
    assert cfg.triggers[0].priority == 100
    cfg2 = config_from_dict(
        {"routines": [], "triggers": [_trigger(priority=-5)], "settings": {}}
    )
    assert cfg2.triggers[0].priority == 0


def test_mic_app_empty_is_allowed_but_inert():
    # an empty app is accepted (never matches) so half-finished edits still save
    cfg = config_from_dict(
        {"routines": [], "triggers": [_trigger(type="mic_app", params={})], "settings": {}}
    )
    assert cfg.triggers[0].type == "mic_app"


def test_rejects_duplicate_trigger_ids():
    with pytest.raises(ConfigError):
        config_from_dict(
            {
                "routines": [],
                "triggers": [_trigger(id="dup"), _trigger(id="dup")],
                "settings": {},
            }
        )


def test_rejects_bad_hex_color():
    # a '#'-prefixed value must be valid hex; bad hex still fails
    with pytest.raises(ConfigError):
        config_from_dict(
            {"routines": [], "triggers": [_trigger(color="#12345")], "settings": {}}
        )


def test_accepts_slot_reference_color():
    # non-'#' tokens are slot references (palette is editable), accepted as-is
    cfg = config_from_dict(
        {"routines": [], "triggers": [_trigger(color="anything")], "settings": {}}
    )
    assert cfg.triggers[0].color == "anything"


def test_rejects_bad_effect():
    with pytest.raises(ConfigError):
        config_from_dict(
            {
                "routines": [],
                "triggers": [_trigger(effect={"type": "disco"})],
                "settings": {},
            }
        )


# ----------------------------------------------------------- migration

def test_migrates_legacy_settings_to_triggers():
    # a config predating triggers: no "triggers" key, legacy call_/lock_ settings
    cfg = config_from_dict(
        {
            "routines": [],
            "settings": {
                "call_detection": True,
                "call_color": "busy",
                "lock_detection": True,
                "lock_color": "away",
            },
        }
    )
    by_id = {t.id: t for t in cfg.triggers}
    assert by_id["t_call"].type == "mic" and by_id["t_call"].priority == 70
    assert by_id["t_call"].color == "busy"
    assert by_id["t_lock"].type == "lock" and by_id["t_lock"].priority == 60
    assert by_id["t_lock"].color == "away"


def test_migration_honors_disabled_legacy_detection():
    cfg = config_from_dict(
        {"routines": [], "settings": {"call_detection": False, "lock_detection": True}}
    )
    ids = {t.id for t in cfg.triggers}
    assert "t_call" not in ids
    assert "t_lock" in ids


def test_empty_triggers_list_is_respected_not_migrated():
    # an explicit empty list means "no triggers", not "migrate from settings"
    cfg = config_from_dict(
        {"routines": [], "triggers": [], "settings": {"call_detection": True}}
    )
    assert cfg.triggers == []


def test_default_config_seeds_two_triggers():
    cfg = default_config()
    assert {t.id for t in cfg.triggers} == {"t_call", "t_lock"}


# ----------------------------------------------------------- mic_app matching

def test_capturer_matches_substring_case_insensitive():
    caps = ["C:#Program Files#Zoom#bin#Zoom.exe", "MSTeams_8wekyb3d8bbwe"]
    assert mic.capturer_matches("zoom", caps)
    assert mic.capturer_matches("TEAMS", caps)
    assert not mic.capturer_matches("slack", caps)


def test_capturer_matches_empty_never_matches():
    assert not mic.capturer_matches("", ["Zoom.exe"])
    assert not mic.capturer_matches("   ", ["Zoom.exe"])


# ----------------------------------------------------------- meta

def test_triggers_meta_shape():
    m = triggers_meta()
    type_ids = {t["id"] for t in m["types"]}
    assert type_ids == {
        "mic", "mic_app", "webcam", "lock", "hotkey",
        "idle", "foreground", "presentation", "process",
    }
    assert m["override_priority"] == 50
    needs = {t["id"]: t["needs_app"] for t in m["types"]}
    assert needs["mic_app"] is True and needs["mic"] is False
    assert needs["foreground"] is True and needs["process"] is True
    hk = next(t for t in m["types"] if t["id"] == "hotkey")
    assert hk["needs_hotkey"] is True
    idle = next(t for t in m["types"] if t["id"] == "idle")
    assert idle["needs_minutes"] is True


def test_new_trigger_dispatch():
    from engine.loop import BeaconEngine
    from engine.config import Trigger

    eng = BeaconEngine()
    probes = {
        "mic": False, "webcam": False, "lock": False,
        "mic_capturers": [], "webcam_capturers": [],
        "idle_seconds": 0.0, "foreground": ("", ""),
        "presentation": False, "processes": [],
    }

    def trig(type, **params):
        return Trigger("x", "X", True, type, "busy", 50, params, {"type": "solid"})

    # idle: fires once past the threshold
    probes["idle_seconds"] = 0.0
    assert eng._trigger_active(trig("idle", minutes=5), probes) is False
    probes["idle_seconds"] = 5 * 60 + 1
    assert eng._trigger_active(trig("idle", minutes=5), probes) is True

    # foreground: matches exe or title
    probes["foreground"] = ("powerpnt.exe", "deck — powerpoint")
    assert eng._trigger_active(trig("foreground", app="powerpnt"), probes) is True
    assert eng._trigger_active(trig("foreground", app="zoom"), probes) is False

    # presentation
    probes["presentation"] = True
    assert eng._trigger_active(trig("presentation"), probes) is True

    # process: substring over running names
    probes["processes"] = ["explorer.exe", "code.exe"]
    assert eng._trigger_active(trig("process", app="code"), probes) is True
    assert eng._trigger_active(trig("process", app="photoshop"), probes) is False


def test_test_trigger_forces_active():
    from engine.loop import BeaconEngine

    eng = BeaconEngine()
    eng.config = config_from_dict(
        {
            "routines": [],
            "triggers": [_trigger(id="t1", type="webcam", color="focus")],
            "settings": {},
        }
    )
    _, active = eng._evaluate_triggers()
    assert active == []  # webcam not in use
    eng.test_trigger("t1", seconds=30)
    _, active = eng._evaluate_triggers()
    assert [a["id"] for a in active] == ["t1"]


def test_hotkey_trigger_toggle():
    from engine.loop import BeaconEngine

    eng = BeaconEngine()
    eng.config = config_from_dict(
        {
            "routines": [],
            "triggers": [
                {
                    "id": "hk",
                    "name": "DND",
                    "enabled": True,
                    "type": "hotkey",
                    "color": "busy",
                    "priority": 90,
                    "params": {"ctrl": True, "alt": True, "key": "B", "vk": 66},
                }
            ],
            "settings": {},
        }
    )
    # not toggled -> not active
    _, active = eng._evaluate_triggers()
    assert [a["id"] for a in active if a["id"] == "hk"] == []
    # press -> active
    eng.toggle_hotkey("hk")
    _, active = eng._evaluate_triggers()
    assert [a["id"] for a in active] == ["hk"]
    # press again -> off
    eng.toggle_hotkey("hk")
    _, active = eng._evaluate_triggers()
    assert [a["id"] for a in active if a["id"] == "hk"] == []
