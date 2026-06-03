"""The closed palette of semantic status slots.

Names, display hex, and meanings are the final values from the Beacon
design handoff. Routines, override, and settings reference slots by name;
the engine maps a slot -> RGB at device-write time. Exposed to the UI via
``GET /api/palette``.

Display vs device color: the design hex are tuned to look good on a
*screen*, where partial channel values read fine. A saturated RGB LED is
unforgiving — e.g. the design green ``#2FCB6F`` carries blue=111, which
renders as turquoise on the flag, and the design yellow's blue=61 washes
it out. So each slot has two colors:

  - ``rgb``        — the display color (drives the UI swatch via ``hex``).
  - ``device_rgb`` — an LED-tuned color (saturated, muddying channels cut)
                     actually written to the flag. Defaults to ``rgb``.

This keeps the on-screen design intact while making the physical flag read
as the color the user picked.

The ``off`` slot is special: it writes black (LEDs off) rather than a
visible color.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Slot:
    slot: str
    name: str
    rgb: tuple[int, int, int]  # display color (UI swatch)
    meaning: str
    off: bool = False
    device_rgb: tuple[int, int, int] | None = None  # LED-tuned; defaults to rgb

    @property
    def hex(self) -> str:
        if self.off:
            return "off"
        r, g, b = self.rgb
        return f"#{r:02X}{g:02X}{b:02X}"

    @property
    def led_rgb(self) -> tuple[int, int, int]:
        return self.device_rgb if self.device_rgb is not None else self.rgb


# device_rgb values are saturated for the RGB LED: the dominant channel(s)
# pushed up and the muddying channel(s) cut toward 0, so each reads clearly
# as its named color on the physical flag.
PALETTE: list[Slot] = [
    Slot("available", "Available", (47, 203, 111), "Free — interrupt me anytime.",
         device_rgb=(0, 230, 40)),
    Slot("busy", "Busy", (255, 59, 59), "In a call or do-not-disturb.",
         device_rgb=(255, 15, 10)),
    Slot("focus", "Focus", (76, 125, 255), "Heads-down. Ping, don't tap.",
         device_rgb=(20, 80, 255)),
    Slot("lunch", "Lunch", (255, 138, 43), "Out for food, back soon.",
         device_rgb=(255, 90, 0)),
    Slot("away", "Away", (255, 201, 61), "Stepped away from the desk.",
         device_rgb=(255, 190, 0)),
    Slot("off", "Off", (0, 0, 0), "Light off — outside hours.", off=True),
]

SLOTS: dict[str, Slot] = {s.slot: s for s in PALETTE}

# Slots a user can choose for routines / override / settings (everything
# except the special "off" slot).
SELECTABLE = [s.slot for s in PALETTE if not s.off]


def is_slot(name: str) -> bool:
    return name in SLOTS


def rgb_of(slot: str) -> tuple[int, int, int]:
    """LED-tuned RGB written to the flag; unknown slots fall back to black."""
    s = SLOTS.get(slot)
    return s.led_rgb if s else (0, 0, 0)


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
