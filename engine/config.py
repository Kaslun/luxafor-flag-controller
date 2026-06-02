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

from engine.logging_setup import get_logger
from engine.paths import config_path
from engine.palette import is_slot

log = get_logger()


class ConfigError(ValueError):
    """Raised when an incoming config fails validation."""


@dataclass
class Routine:
    id: str
    name: str
    enabled: bool
    days: list[int]  # weekday indices, Mon=0 .. Sun=6
    start: str  # "HH:MM"
    end: str  # "HH:MM"
    color: str  # palette slot name


@dataclass
class Settings:
    call_detection: bool = True
    call_color: str = "busy"
    available_color: str = "available"
    off_behavior: str = "off"  # "off" | "dim" | <slot name>
    heartbeat_interval_seconds: int = 60


@dataclass
class Config:
    routines: list[Routine] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    def to_dict(self) -> dict:
        return {
            "routines": [asdict(r) for r in self.routines],
            "settings": asdict(self.settings),
        }


def default_config() -> Config:
    """Defaults from the design's DEFAULT_ROUTINES."""
    return Config(
        routines=[
            Routine("r1", "Lunch", True, [0, 1, 2, 3, 4], "12:00", "12:30", "lunch"),
            Routine(
                "r2", "Wind-down focus", True, [0, 1, 2, 3, 4], "16:00", "17:30", "focus"
            ),
        ],
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
    if not is_slot(color):
        raise ConfigError(f"routine {rid!r}: unknown color slot {color!r}")
    return Routine(rid, name, enabled, days, start, end, color)


def _settings_from_dict(d: dict) -> Settings:
    s = Settings()
    if not isinstance(d, dict):
        raise ConfigError("settings must be an object")
    s.call_detection = bool(d.get("call_detection", s.call_detection))
    s.call_color = str(d.get("call_color", s.call_color))
    s.available_color = str(d.get("available_color", s.available_color))
    s.off_behavior = str(d.get("off_behavior", s.off_behavior))
    s.heartbeat_interval_seconds = int(
        d.get("heartbeat_interval_seconds", s.heartbeat_interval_seconds)
    )

    if not is_slot(s.call_color):
        raise ConfigError(f"unknown call_color slot {s.call_color!r}")
    if not is_slot(s.available_color):
        raise ConfigError(f"unknown available_color slot {s.available_color!r}")
    # off_behavior is "off", "dim", or any known slot name.
    if s.off_behavior not in ("off", "dim") and not is_slot(s.off_behavior):
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
    return Config(routines=routines, settings=settings)


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
