"""The pure status resolver.

``resolve(now, state, config) -> ResolvedStatus`` decides the single
color the flag should show. It is a pure function of its inputs (no I/O,
no device, no clock-of-its-own) so it is trivially testable and is the
behavioral contract the UI renders from.

Priority ladder (highest first), matching the Beacon design's
``resolveStatus``:

  1. paused        — engine writes nothing
  2. disconnected  — no working HID handle
  3. preview       — live color preview while the user is picking
  4. call          — mic capture detected (when call_detection on)
  5. locked        — screen locked (when lock_detection on)
  6. override       — manual override, not expired
  7. routine       — a matching enabled scheduled block (later start wins)
  8. floor          — off / dim / available, per settings.off_behavior

A real call (3) outranks a manual override (4): if you're talking, you're
busy regardless of what you set. Paused/disconnected outrank everything
because there is no meaningful color to show.

The resolver emits both ``routine`` (the winning source) and ``kind``
(the rendering bucket the UI switches on): one of
``paused | disconnected | call | override | routine | available | off | dim``.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from engine.config import Config, Routine
from engine.palette import name_of


@dataclass
class ResolvedStatus:
    routine: str  # winning source id
    color: str  # palette slot name or "#RRGGBB" custom color
    reason: str  # human-readable explanation
    kind: str  # rendering bucket (see module docstring)
    off: bool = False  # LEDs should be dark
    dim: bool = False  # available color, reduced brightness
    effect: dict | None = None  # None = solid; see engine.effects


def _to_min(hhmm: str) -> int:
    h, m = (int(x) for x in hhmm.split(":"))
    return h * 60 + m


def _today_idx(now: dt.datetime) -> int:
    """Monday=0 .. Sunday=6 (matches Routine.days indexing)."""
    return now.weekday()


def _fmt12(hhmm: str) -> str:
    h, m = (int(x) for x in hhmm.split(":"))
    ap = "am" if h < 12 else "pm"
    hh = ((h + 11) % 12) + 1
    return f"{hh}:{m:02d}{ap}"


def active_routine(routines: list[Routine], now: dt.datetime) -> Routine | None:
    """The routine whose window contains ``now``; later start wins on overlap.

    Iterating in list order and keeping the last match makes "later start
    wins" deterministic as long as routines are stored start-ordered; to be
    robust regardless of stored order we explicitly prefer the greater
    start time.
    """
    di = _today_idx(now)
    mins = now.hour * 60 + now.minute
    best: Routine | None = None
    for r in routines:
        if not r.enabled or di not in r.days:
            continue
        if _to_min(r.start) <= mins < _to_min(r.end):
            if best is None or _to_min(r.start) >= _to_min(best.start):
                best = r
    return best


def _format_override_reason(color: str, expiry: str | None, now: dt.datetime) -> str:
    if expiry is None:
        return f"Manual: {name_of(color)} until you clear it."
    try:
        until = dt.datetime.fromisoformat(expiry)
        label = until.strftime("%I:%M%p").lstrip("0").lower()
    except ValueError:
        label = "soon"
    return f"Manual: {name_of(color)} until {label}."


def resolve(now: dt.datetime, state, config: Config) -> ResolvedStatus:
    """Pure resolution. ``state`` is the live engine State (duck-typed:
    needs ``paused``, ``device_connected``, ``in_call``, ``manual_override``).
    """
    s = config.settings

    # 1. paused
    if state.paused:
        return ResolvedStatus(
            "paused", "off", "Paused — the flag isn't being controlled.",
            kind="paused", off=True,
        )

    # 2. disconnected
    if not state.device_connected:
        return ResolvedStatus(
            "disconnected", "off", "Flag disconnected — plug your Luxafor back in.",
            kind="disconnected", off=True,
        )

    # 3. live preview — while the user is actively picking a color, show it
    #    above everything so they see exactly what they'll get.
    pv = getattr(state, "preview", None)
    if pv and pv.get("color"):
        return ResolvedStatus(
            "preview", pv["color"], "Preview — choosing a color.",
            kind="preview", effect=pv.get("effect"),
        )

    # 4. live call (beats override)
    if s.call_detection and state.in_call:
        return ResolvedStatus(
            "on_call", s.call_color, "In a call — detected automatically.",
            kind="call",
        )

    # 5. screen locked — you stepped away
    if getattr(s, "lock_detection", False) and getattr(state, "locked", False):
        return ResolvedStatus(
            "locked", s.lock_color, "Screen locked — you're away.",
            kind="locked",
        )

    # 6. manual override
    ov = state.manual_override
    if ov:
        color = ov.get("color")
        expiry = ov.get("expiry")
        return ResolvedStatus(
            "override", color, _format_override_reason(color, expiry, now),
            kind="override", effect=ov.get("effect"),
        )

    # 7. active scheduled routine
    r = active_routine(config.routines, now)
    if r:
        return ResolvedStatus(
            "routine", r.color,
            f"{r.name} ({_fmt12(r.start)}–{_fmt12(r.end)}).",
            kind="routine", effect=getattr(r, "effect", None),
        )

    # 8. floor — depends on off_behavior
    ob = s.off_behavior
    if ob == "off":
        return ResolvedStatus(
            "available", "off", "Off — no routine active right now.",
            kind="off", off=True,
        )
    if ob == "dim":
        return ResolvedStatus(
            "available", s.available_color, "Dimmed — available, nothing scheduled.",
            kind="dim", dim=True,
        )
    # off_behavior is an explicit slot name
    return ResolvedStatus(
        "available", s.available_color, "Available — nothing scheduled.",
        kind="available",
    )
