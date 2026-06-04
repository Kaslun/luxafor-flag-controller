"""The live engine State — single source of truth the API and tray read.

One ``State`` instance exists per process. The loop mutates it each tick;
the FastAPI handlers and the tray thread read it (and post commands to
it). All access goes through the instance lock.

``snapshot()`` produces the wire format consumed by ``GET /api/state`` and
the React UI. The shape follows the build spec's State JSON contract, with
the two design-aligned adjustments documented in the plan:

  - ``conflict_detected`` uses the design's two-flag shape
    ``{luxafor_v2_running, luxafor_v2_startup} | null`` (the spec's single
    discriminator can't express both-true, which the two-step conflict UI
    needs).
  - ``manual_override.expiry`` is an ISO timestamp or null on the wire
    (spec-authoritative); the UI converts to/from its own representation.

``kind`` is added alongside ``routine`` so the UI can switch on a stable
rendering bucket without recomputing status.
"""

from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass, field

from engine.version import __version__


@dataclass
class State:
    # resolved output (updated each tick)
    color: str = "off"  # palette slot name or "#RRGGBB" custom color
    routine: str = "off"  # winning source
    kind: str = "off"  # rendering bucket
    reason: str = ""
    effect: dict | None = None  # resolved effect (None = solid)

    # control flags / inputs
    paused: bool = False
    in_call: bool = False  # mic detection result (derived from signals.mic)
    locked: bool = False  # screen-lock detection result (derived)
    device_connected: bool = False
    manual_override: dict | None = None  # {color: slot, expiry: ISO|None}
    preview: dict | None = None  # {color, effect} live preview while picking

    # triggers (events): raw sampled signals + the currently-firing triggers
    signals: dict = field(default_factory=dict)  # {mic, webcam, lock, *_capturers}
    active_triggers: list = field(default_factory=list)  # [{id,name,color,...}]

    # ambient
    update_available: dict | None = None  # {version, url}
    conflict_detected: dict | None = None  # {luxafor_v2_running, luxafor_v2_startup}
    autostart_enabled: bool = False  # registered in the per-user Run key
    version: str = __version__  # running engine version
    port: int = 0  # bound localhost port (for tray "Open Beacon")

    updated_at: dt.datetime = field(default_factory=dt.datetime.now)

    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    def snapshot(self) -> dict:
        """Thread-safe serializable view for the API/UI."""
        with self.lock:
            return {
                "color": self.color,
                "routine": self.routine,
                "kind": self.kind,
                "reason": self.reason,
                "effect": dict(self.effect) if self.effect else None,
                "paused": self.paused,
                "in_call": self.in_call,
                "locked": self.locked,
                "signals": dict(self.signals),
                "active_triggers": [dict(t) for t in self.active_triggers],
                "device_connected": self.device_connected,
                "manual_override": (
                    dict(self.manual_override) if self.manual_override else None
                ),
                "update_available": (
                    dict(self.update_available) if self.update_available else None
                ),
                "conflict_detected": (
                    dict(self.conflict_detected) if self.conflict_detected else None
                ),
                "autostart_enabled": self.autostart_enabled,
                "version": self.version,
                "updated_at": self.updated_at.isoformat(),
            }
