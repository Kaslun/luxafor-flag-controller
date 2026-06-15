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
  4. urgent triggers — active triggers with priority > OVERRIDE_PRIORITY
  5. override      — manual override
  6. normal triggers — active triggers with priority > ROUTINE_PRIORITY
  7. routine       — a matching enabled scheduled block (later start wins)
  8. low triggers  — any remaining active trigger
  9. floor          — off / dim / available, per settings.off_behavior

Triggers resolve in *importance bands* (the four UI tiers), not one block:
High/Critical (priority > OVERRIDE_PRIORITY) outrank a manual override;
Normal (> ROUTINE_PRIORITY) beats routines but yields to an override; Low
only wins when nothing else is active. Within a band the highest priority
wins (ties → config order). The loop evaluates each enabled trigger's
condition and hands the resolver the list of *active* triggers as plain
dicts on ``state.active_triggers``; this keeps the resolver pure — all I/O
(mic/lock/webcam sampling) happens in the loop.

The resolver emits both ``routine`` (the winning source id) and ``kind``
(the rendering bucket the UI switches on): one of
``paused | disconnected | preview | trigger | override | routine | available | off | dim``.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from engine.config import OVERRIDE_PRIORITY, ROUTINE_PRIORITY, Config, Routine


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

    # 4–8. trigger importance bands interleaved with override and routines.
    # active_triggers is sorted highest-priority-first so the first match in
    # each band is the band winner.
    active = sorted(
        getattr(state, "active_triggers", None) or [],
        key=lambda t: t.get("priority", OVERRIDE_PRIORITY),
        reverse=True,
    )

    def _trigger(t) -> ResolvedStatus:
        return ResolvedStatus(
            t.get("id", "trigger"), t["color"], t.get("name") or "Trigger",
            kind="trigger", effect=t.get("effect"),
        )

    def _first(pred):
        return next((t for t in active if pred(t.get("priority", OVERRIDE_PRIORITY))), None)

    ov = state.manual_override

    # band: urgent triggers (above the override)
    urgent = _first(lambda p: p > OVERRIDE_PRIORITY)
    if urgent is not None:
        return _trigger(urgent)

    # band: manual override
    if ov:
        return ResolvedStatus(
            "override", ov.get("color"), "Manual",
            kind="override", effect=ov.get("effect"),
        )

    # band: normal triggers (above routines, below the override)
    normal = _first(lambda p: p > ROUTINE_PRIORITY)
    if normal is not None:
        return _trigger(normal)

    # band: active scheduled routine
    r = active_routine(config.routines, now)
    if r:
        return ResolvedStatus(
            "routine", r.color, r.name or "Routine",
            kind="routine", effect=getattr(r, "effect", None),
        )

    # band: low triggers (only when nothing above is active)
    if active:
        return _trigger(active[0])

    # 8. floor — depends on off_behavior
    ob = s.off_behavior
    if ob == "off":
        return ResolvedStatus(
            "available", "off", "Off-hours", kind="off", off=True,
        )
    if ob == "dim":
        return ResolvedStatus(
            "available", s.available_color, "Resting", kind="dim", dim=True,
        )
    # off_behavior is an explicit slot name
    return ResolvedStatus(
        "available", s.available_color, "At your desk", kind="available",
    )
