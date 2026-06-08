"""Flag effects: solid color plus Luxafor's animated commands.

The validated, proven command in this project is the static color
(``0x01``). The animated commands below (fade, strobe, wave, built-in
pattern) follow Luxafor's documented HID protocol but have **not** been
validated on the physical Flag here — they ship behind the new effect
picker for live testing and tuning.

An ``effect`` is a plain dict carried on routines and the manual override:

    {"type": "solid"|"fade"|"strobe"|"wave"|"pattern",
     "speed": 0..255,          # animation speed/duration byte
     "wave_type": 1..5,        # only for type == "wave"
     "pattern_id": 1..8}       # only for type == "pattern"

``build_report(rgb, effect)`` returns the 8-byte HID report (report id
first) to write to the device. All reports keep the proven 8-byte framing
``[0x00, command, target, p1, p2, p3, p4, p5]``.

Built-in patterns are firmware animations that ignore the color.
"""

from __future__ import annotations

LED_ALL = 0xFF

EFFECT_TYPES = ["solid", "fade", "strobe", "wave", "pattern"]

# wave_type / pattern_id labels are exposed to the UI for selection.
WAVE_TYPES = [
    {"id": 1, "name": "Short"},
    {"id": 2, "name": "Long"},
    {"id": 3, "name": "Overlapping short"},
    {"id": 4, "name": "Overlapping long"},
    {"id": 5, "name": "Sweep"},
]
PATTERN_IDS = [
    {"id": 1, "name": "Luxafor"},
    {"id": 2, "name": "Random 1"},
    {"id": 3, "name": "Random 2"},
    {"id": 4, "name": "Random 3"},
    {"id": 5, "name": "Police"},
    {"id": 6, "name": "Random 4"},
    {"id": 7, "name": "Random 5"},
    {"id": 8, "name": "Rainbow wave"},
]

SPEED_MIN, SPEED_MAX = 0, 255
DEFAULT_SPEED = 40

DEFAULT_EFFECT: dict = {
    "type": "solid",
    "speed": DEFAULT_SPEED,
    "wave_type": 1,
    "pattern_id": 1,
}

# patterns are firmware animations; they ignore the chosen color
COLOR_IGNORED_TYPES = {"pattern"}


class EffectError(ValueError):
    """Raised when an effect dict fails validation."""


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def normalize_effect(d: dict | None) -> dict:
    """Validate and fill defaults. Returns a fresh, complete effect dict."""
    if d is None:
        return dict(DEFAULT_EFFECT)
    if not isinstance(d, dict):
        raise EffectError("effect must be an object")

    t = str(d.get("type", "solid"))
    if t not in EFFECT_TYPES:
        raise EffectError(f"unknown effect type {t!r}")

    try:
        speed = int(d.get("speed", DEFAULT_SPEED))
        wave_type = int(d.get("wave_type", 1))
        pattern_id = int(d.get("pattern_id", 1))
    except (TypeError, ValueError):
        raise EffectError("effect speed/wave_type/pattern_id must be integers")

    if not (1 <= wave_type <= len(WAVE_TYPES)):
        raise EffectError(f"wave_type out of range: {wave_type}")
    if not (1 <= pattern_id <= len(PATTERN_IDS)):
        raise EffectError(f"pattern_id out of range: {pattern_id}")

    return {
        "type": t,
        "speed": _clamp(speed, SPEED_MIN, SPEED_MAX),
        "wave_type": wave_type,
        "pattern_id": pattern_id,
    }


def is_solid(effect: dict | None) -> bool:
    return effect is None or effect.get("type", "solid") == "solid"


# A running firmware animation (built-in pattern 0x06, strobe 0x03, wave
# 0x04) is NOT reliably stopped by a static-color write — the firmware keeps
# animating. Sending the pattern command with id 0 resets the animation
# engine (verified on the device for patterns; applied to strobe/wave too).
PATTERN_CMD = 0x06
STROBE_CMD = 0x03
WAVE_CMD = 0x04
PATTERN_OFF_REPORT = [0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]


def report_is_pattern(report: list[int] | None) -> bool:
    """True if a built-in pattern animation is running for this report."""
    return bool(report) and len(report) > 2 and report[1] == PATTERN_CMD and report[2] != 0


def report_is_animation(report: list[int] | None) -> bool:
    """True if this report drives any firmware animation (strobe/wave/pattern)
    that must be explicitly stopped before a clean static write."""
    if not report or len(report) < 2:
        return False
    cmd = report[1]
    if cmd == PATTERN_CMD:
        return len(report) > 2 and report[2] != 0
    return cmd in (STROBE_CMD, WAVE_CMD)


def ignores_color(effect: dict | None) -> bool:
    return bool(effect) and effect.get("type") in COLOR_IGNORED_TYPES


def build_report(rgb: tuple[int, int, int], effect: dict | None) -> list[int]:
    """Build the 8-byte HID report for a color + effect.

    Report framing: ``[report_id, command, target, p1, p2, p3, p4, p5]``.
    """
    e = normalize_effect(effect)
    r, g, b = (int(c) & 0xFF for c in rgb)
    spd = e["speed"]
    t = e["type"]

    if t == "solid":
        return [0x00, 0x01, LED_ALL, r, g, b, 0x00, 0x00]
    if t == "fade":
        # [id, 0x02, LED, R, G, B, fade_duration, 0]
        return [0x00, 0x02, LED_ALL, r, g, b, spd, 0x00]
    if t == "strobe":
        # [id, 0x03, LED, R, G, B, speed, repeat] — repeat 0 = continuous
        return [0x00, 0x03, LED_ALL, r, g, b, spd, 0x00]
    if t == "wave":
        # [id, 0x04, wave_type, R, G, B, repeat, speed] — repeat 0 = continuous
        return [0x00, 0x04, e["wave_type"], r, g, b, 0x00, spd]
    if t == "pattern":
        # [id, 0x06, pattern_id, repeat, 0, 0, 0, 0] — color ignored by firmware
        return [0x00, 0x06, e["pattern_id"], 0x00, 0x00, 0x00, 0x00, 0x00]

    # unreachable (normalize_effect guards), but keep a safe fallback
    return [0x00, 0x01, LED_ALL, r, g, b, 0x00, 0x00]


def as_payload() -> dict:
    """Effect vocabulary for the UI (GET /api/effects)."""
    return {
        "types": EFFECT_TYPES,
        "wave_types": WAVE_TYPES,
        "pattern_ids": PATTERN_IDS,
        "speed_min": SPEED_MIN,
        "speed_max": SPEED_MAX,
        "default": dict(DEFAULT_EFFECT),
        "color_ignored_types": sorted(COLOR_IGNORED_TYPES),
    }
