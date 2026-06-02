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


@dataclass
class State:
    # resolved output (updated each tick)
    color: str = "off"  # palette slot name
    routine: str = "off"  # winning source
    kind: str = "off"  # rendering bucket
    reason: str = ""

    # control flags / inputs
    paused: bool = False
    in_call: bool = False  # mic detection result
    device_connected: bool = False
    manual_override: dict | None = None  # {color: slot, expiry: ISO|None}

    # ambient
    update_available: dict | None = None  # {version, url}
    conflict_detected: dict | None = None  # {luxafor_v2_running, luxafor_v2_startup}
    autostart_enabled: bool = False  # registered in the per-user Run key
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
                "paused": self.paused,
                "in_call": self.in_call,
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
                "updated_at": self.updated_at.isoformat(),
            }
