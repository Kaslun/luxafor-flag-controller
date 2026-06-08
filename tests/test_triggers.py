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
    for t in ("mic", "mic_app", "webcam", "lock"):
        params = {"app": "teams"} if t == "mic_app" else {}
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
    assert type_ids == {"mic", "mic_app", "webcam", "lock"}
    assert m["override_priority"] == 50
    needs = {t["id"]: t["needs_app"] for t in m["types"]}
    assert needs["mic_app"] is True and needs["mic"] is False
