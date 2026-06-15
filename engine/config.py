"""Engine-owned configuration: routines + settings.

Persisted as JSON in ``%APPDATA%\\Beacon\\config.json``, read/written via
the API, never edited by hand. Ships with defaults pre-populated so the
app works untouched. Writes are atomic (temp file + os.replace) so a
crash mid-write can't corrupt the file.

Field names follow the Beacon design handoff (``call_detection``,
``call_color``, ``off_behavior``), which is authoritative for the
settings shape. Routine days are weekday indices Mon=0..Sun=6.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engine.effects import EffectError, normalize_effect
from engine.logging_setup import get_logger
from engine.paths import config_path
from engine.palette import PALETTE, is_color, is_hex

log = get_logger()

BRIGHTNESS_MIN, BRIGHTNESS_MAX = 10, 100


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


class ConfigError(ValueError):
    """Raised when an incoming config fails validation."""


# Trigger condition types. Each maps to a detector evaluated each tick
# (see engine.loop). "mic" and "lock" are the unified successors of the old
# call_detection / lock_detection settings.
TRIGGER_TYPES = ("mic", "mic_app", "webcam", "lock", "hotkey")

# Triggers resolve in importance bands relative to the manual override and to
# routines (see engine.resolver). A trigger with priority strictly above
# OVERRIDE_PRIORITY beats a manual override; one above ROUTINE_PRIORITY (but
# not the override) beats routines; below that it only shows when nothing else
# is active. The four UI tiers map onto these bands:
#   Low=20 (below routines) · Normal=40 (above routines, below override)
#   High=70 / Critical=90 (above override). 50 == the override itself.
PRIORITY_MIN, PRIORITY_MAX = 0, 100
OVERRIDE_PRIORITY = 50
ROUTINE_PRIORITY = 30


def triggers_meta() -> dict:
    """Trigger vocabulary for the UI (GET /api/triggers/meta)."""
    return {
        "types": [
            {"id": "mic", "name": "In a call (mic in use)", "needs_app": False, "needs_hotkey": False},
            {"id": "mic_app", "name": "Specific app on mic", "needs_app": True, "needs_hotkey": False},
            {"id": "webcam", "name": "Webcam in use", "needs_app": False, "needs_hotkey": False},
            {"id": "lock", "name": "Screen locked", "needs_app": False, "needs_hotkey": False},
            {"id": "hotkey", "name": "Keyboard shortcut", "needs_app": False, "needs_hotkey": True},
        ],
        "priority_min": PRIORITY_MIN,
        "priority_max": PRIORITY_MAX,
        "override_priority": OVERRIDE_PRIORITY,
    }


@dataclass
class PaletteColor:
    """A user-editable template colour.

    ``hex`` is the on-screen/display colour. ``led`` is an optional LED-tuned
    hex written to the physical flag instead of ``hex`` (saturated RGB LEDs
    render some display colours poorly); it defaults to ``hex`` and is dropped
    when the user recolours a slot. ``off`` marks the special locked "lights
    off" slot.
    """

    slot: str
    name: str
    hex: str
    off: bool = False
    led: str | None = None


@dataclass
class Trigger:
    id: str
    name: str
    enabled: bool
    type: str  # one of TRIGGER_TYPES
    color: str  # palette slot name or "#RRGGBB" custom color
    priority: int = 50  # 0..100, higher wins; 50 == manual override
    params: dict = field(default_factory=dict)  # e.g. {"app": "teams"}
    effect: dict = field(default_factory=lambda: {"type": "solid"})


@dataclass
class Routine:
    id: str
    name: str
    enabled: bool
    days: list[int]  # weekday indices, Mon=0 .. Sun=6
    start: str  # "HH:MM"
    end: str  # "HH:MM"
    color: str  # palette slot name or "#RRGGBB" custom color
    effect: dict = field(default_factory=lambda: {"type": "solid"})


@dataclass
class Settings:
    available_color: str = "available"
    off_behavior: str = "off"  # "off" | "dim" | <slot name>
    heartbeat_interval_seconds: int = 60
    brightness: int = 80  # 10..100, scales the device colour


@dataclass
class Config:
    routines: list[Routine] = field(default_factory=list)
    triggers: list[Trigger] = field(default_factory=list)
    palette: list[PaletteColor] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def to_dict(self) -> dict:
        return {
            "routines": [asdict(r) for r in self.routines],
            "triggers": [asdict(t) for t in self.triggers],
            "palette": [asdict(p) for p in self.palette],
            "settings": asdict(self.settings),
        }


def default_palette() -> list[PaletteColor]:
    """Seed the editable palette from the design's closed slot set, carrying
    the LED-tuned device colours so the physical flag reads correctly out of
    the box (the ``off`` slot stays locked)."""
    out: list[PaletteColor] = []
    for s in PALETTE:
        if s.off:
            out.append(PaletteColor("off", "Off", "#000000", off=True))
        else:
            out.append(
                PaletteColor(s.slot, s.name, s.hex, led=_rgb_to_hex(s.led_rgb))
            )
    return out


def default_triggers() -> list[Trigger]:
    """The two seed triggers — the unified successors of call/lock detection."""
    return [
        Trigger("t_call", "In a call", True, "mic", "busy", 70),
        Trigger("t_lock", "Screen locked", True, "lock", "away", 60),
    ]


def default_config() -> Config:
    """Defaults from the design's DEFAULT_ROUTINES + seed triggers."""
    return Config(
        routines=[
            Routine("r1", "Lunch", True, [0, 1, 2, 3, 4], "12:00", "12:30", "lunch"),
            Routine(
                "r2", "Wind-down focus", True, [0, 1, 2, 3, 4], "16:00", "17:30", "focus"
            ),
        ],
        triggers=default_triggers(),
        palette=default_palette(),
        settings=Settings(),
    )


# ---------------------------------------------------------------- parsing

def _parse_hhmm(value: str, label: str) -> int:
    """Validate "HH:MM" and return minutes since midnight."""
    try:
        h, m = (int(x) for x in str(value).split(":"))
    except (ValueError, AttributeError):
        raise ConfigError(f"{label!r} must be 'HH:MM', got {value!r}")
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ConfigError(f"{label!r} out of range: {value!r}")
    return h * 60 + m


def _routine_from_dict(d: dict) -> Routine:
    try:
        rid = str(d["id"])
        name = str(d.get("name", ""))
        enabled = bool(d["enabled"])
        days = [int(x) for x in d["days"]]
        start = str(d["start"])
        end = str(d["end"])
        color = str(d["color"])
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"malformed routine: {e}")

    if any(x < 0 or x > 6 for x in days):
        raise ConfigError(f"routine {rid!r}: days must be 0..6, got {days}")
    if _parse_hhmm(start, "start") >= _parse_hhmm(end, "end"):
        raise ConfigError(f"routine {rid!r}: start must be before end (no midnight span)")
    if not is_color(color):
        raise ConfigError(f"routine {rid!r}: invalid color {color!r} (slot name or #RRGGBB)")
    try:
        effect = normalize_effect(d.get("effect"))
    except EffectError as e:
        raise ConfigError(f"routine {rid!r}: {e}")
    return Routine(rid, name, enabled, days, start, end, color, effect)


def _trigger_from_dict(d: dict) -> Trigger:
    try:
        tid = str(d["id"])
        name = str(d.get("name", ""))
        enabled = bool(d["enabled"])
        ttype = str(d["type"])
        color = str(d["color"])
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"malformed trigger: {e}")

    if ttype not in TRIGGER_TYPES:
        raise ConfigError(f"trigger {tid!r}: unknown type {ttype!r}")
    if not is_color(color):
        raise ConfigError(
            f"trigger {tid!r}: invalid color {color!r} (slot name or #RRGGBB)"
        )

    params = d.get("params") or {}
    if not isinstance(params, dict):
        raise ConfigError(f"trigger {tid!r}: params must be an object")
    # mic_app with an empty/absent app is allowed: it simply never matches
    # (capturer_matches("") is False). This keeps a half-finished trigger from
    # failing the whole-config save while the user is still typing the name.

    try:
        priority = int(d.get("priority", 50))
    except (TypeError, ValueError):
        raise ConfigError(f"trigger {tid!r}: priority must be an integer")
    priority = max(PRIORITY_MIN, min(PRIORITY_MAX, priority))

    try:
        effect = normalize_effect(d.get("effect"))
    except EffectError as e:
        raise ConfigError(f"trigger {tid!r}: {e}")

    return Trigger(tid, name, enabled, ttype, color, priority, params, effect)


def _palette_from_dict(d: dict) -> PaletteColor:
    try:
        slot = str(d["slot"])
        name = str(d.get("name", ""))
        off = bool(d.get("off", False))
    except (KeyError, TypeError, ValueError) as e:
        raise ConfigError(f"malformed palette colour: {e}")
    if off:
        return PaletteColor(slot, name or "Off", "#000000", off=True)
    hexv = str(d.get("hex", ""))
    if not is_hex(hexv):
        raise ConfigError(f"palette {slot!r}: invalid hex {hexv!r}")
    led = d.get("led")
    if led is not None:
        led = str(led)
        if not is_hex(led):
            raise ConfigError(f"palette {slot!r}: invalid led hex {led!r}")
    return PaletteColor(slot, name, hexv if hexv.startswith("#") else "#" + hexv,
                        off=False, led=led)


def _parse_palette(palette_in) -> list[PaletteColor]:
    if not isinstance(palette_in, list):
        raise ConfigError("palette must be a list")
    colors = [_palette_from_dict(c) for c in palette_in]
    slots = [c.slot for c in colors]
    if len(slots) != len(set(slots)):
        raise ConfigError("palette slots must be unique")
    if sum(1 for c in colors if c.off) != 1:
        raise ConfigError("palette must contain exactly one 'off' colour")
    return colors


def _migrate_triggers(settings_d: dict) -> list[Trigger]:
    """Seed triggers from legacy call_*/lock_* settings for configs that
    predate the triggers list. Mirrors the prior built-in behavior exactly:
    mic at priority 70 and lock at 60 (both above a manual override)."""
    out: list[Trigger] = []
    if bool(settings_d.get("call_detection", True)):
        out.append(
            Trigger("t_call", "In a call", True, "mic",
                    str(settings_d.get("call_color", "busy")), 70)
        )
    if bool(settings_d.get("lock_detection", True)):
        out.append(
            Trigger("t_lock", "Screen locked", True, "lock",
                    str(settings_d.get("lock_color", "away")), 60)
        )
    return out


def _settings_from_dict(d: dict) -> Settings:
    s = Settings()
    if not isinstance(d, dict):
        raise ConfigError("settings must be an object")
    s.available_color = str(d.get("available_color", s.available_color))
    s.off_behavior = str(d.get("off_behavior", s.off_behavior))
    s.heartbeat_interval_seconds = int(
        d.get("heartbeat_interval_seconds", s.heartbeat_interval_seconds)
    )
    try:
        s.brightness = int(d.get("brightness", s.brightness))
    except (TypeError, ValueError):
        raise ConfigError("brightness must be an integer")
    s.brightness = max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, s.brightness))

    if not is_color(s.available_color):
        raise ConfigError(f"invalid available_color {s.available_color!r}")
    # off_behavior is "off", "dim", or any color (slot name or #RRGGBB).
    if s.off_behavior not in ("off", "dim") and not is_color(s.off_behavior):
        raise ConfigError(f"invalid off_behavior {s.off_behavior!r}")
    if s.heartbeat_interval_seconds < 5:
        raise ConfigError("heartbeat_interval_seconds must be >= 5")
    return s


def config_from_dict(d: dict) -> Config:
    """Validate and build a Config from a plain dict (API input or file)."""
    if not isinstance(d, dict):
        raise ConfigError("config must be an object")
    routines_in = d.get("routines", [])
    if not isinstance(routines_in, list):
        raise ConfigError("routines must be a list")
    routines = [_routine_from_dict(r) for r in routines_in]

    ids = [r.id for r in routines]
    if len(ids) != len(set(ids)):
        raise ConfigError("routine ids must be unique")

    settings = _settings_from_dict(d.get("settings", {}))

    # Triggers are authoritative when present; otherwise migrate from the
    # legacy call_*/lock_* settings (one-time, transparent on next save).
    if "triggers" in d:
        triggers_in = d.get("triggers") or []
        if not isinstance(triggers_in, list):
            raise ConfigError("triggers must be a list")
        triggers = [_trigger_from_dict(t) for t in triggers_in]
    else:
        triggers = _migrate_triggers(d.get("settings", {}))

    tids = [t.id for t in triggers]
    if len(tids) != len(set(tids)):
        raise ConfigError("trigger ids must be unique")

    # Palette is authoritative when present; otherwise seed the defaults
    # (transparent migration for configs that predate the editable palette).
    if "palette" in d:
        palette = _parse_palette(d.get("palette") or [])
    else:
        palette = default_palette()

    return Config(
        routines=routines, triggers=triggers, palette=palette, settings=settings
    )


# ---------------------------------------------------------------- persistence

def load_config(path: Path | None = None) -> Config:
    """Load config from disk; write+return defaults if missing or corrupt."""
    p = path or config_path()
    if not p.exists():
        cfg = default_config()
        save_config(cfg, p)
        return cfg
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return config_from_dict(data)
    except (json.JSONDecodeError, ConfigError, OSError) as e:
        log.warning("config load failed (%s); rewriting defaults", e)
        cfg = default_config()
        save_config(cfg, p)
        return cfg


def save_config(cfg: Config, path: Path | None = None) -> None:
    """Atomically persist config: write temp, fsync, os.replace."""
    p = path or config_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg.to_dict(), f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)
