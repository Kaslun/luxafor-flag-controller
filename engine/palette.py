"""The closed palette of semantic status slots.

Names, hex, and meanings are the final values from the Beacon design
handoff. Routines, override, and settings reference slots by name; the
engine maps a slot -> RGB at device-write time. Exposed to the UI via
``GET /api/palette``.

The ``off`` slot is special: it writes black (LEDs off) rather than a
visible color.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    slot: str
    name: str
    rgb: tuple[int, int, int]
    meaning: str
    off: bool = False

    @property
    def hex(self) -> str:
        if self.off:
            return "off"
        r, g, b = self.rgb
        return f"#{r:02X}{g:02X}{b:02X}"


PALETTE: list[Slot] = [
    Slot("available", "Available", (47, 203, 111), "Free — interrupt me anytime."),
    Slot("busy", "Busy", (255, 59, 59), "In a call or do-not-disturb."),
    Slot("focus", "Focus", (76, 125, 255), "Heads-down. Ping, don't tap."),
    Slot("lunch", "Lunch", (255, 138, 43), "Out for food, back soon."),
    Slot("away", "Away", (255, 201, 61), "Stepped away from the desk."),
    Slot("off", "Off", (0, 0, 0), "Light off — outside hours.", off=True),
]

SLOTS: dict[str, Slot] = {s.slot: s for s in PALETTE}

# Slots a user can choose for routines / override / settings (everything
# except the special "off" slot).
SELECTABLE = [s.slot for s in PALETTE if not s.off]


def is_slot(name: str) -> bool:
    return name in SLOTS


def rgb_of(slot: str) -> tuple[int, int, int]:
    """RGB for a slot name; unknown slots fall back to off (black)."""
    s = SLOTS.get(slot)
    return s.rgb if s else (0, 0, 0)


def name_of(slot: str) -> str:
    s = SLOTS.get(slot)
    return s.name if s else slot


def dim_rgb(rgb: tuple[int, int, int], factor: float = 0.15) -> tuple[int, int, int]:
    """Scale an RGB triple toward black for the 'dim' off-behavior."""
    return tuple(max(0, min(255, round(c * factor))) for c in rgb)  # type: ignore[return-value]


def as_payload() -> list[dict]:
    """Serializable palette for GET /api/palette."""
    return [
        {
            "slot": s.slot,
            "name": s.name,
            "hex": s.hex,
            "meaning": s.meaning,
            "off": s.off,
        }
        for s in PALETTE
    ]
