"""Raw HID device layer for the Luxafor Flag 2.

Settled constraints (do not substitute — see build spec):
  - Use raw ``hidapi``, not busylight-core (its writes never landed on
    Windows).
  - The validated write report is 8 bytes:
    ``[0x00, 0x01, 0xFF, R, G, B, 0x00, 0x00]`` (report id, static-color
    command, all-LEDs target, RGB), written **twice** to beat a
    first-write-drop quirk.
  - Device IDs: VID 0x04D8 / PID 0xF372.

This module is hardened beyond the prototype: a write that fails (e.g.
the Luxafor v2 app grabbed the shared handle) marks the device
disconnected and the next ``set`` transparently reopens. The loop —
not the device — decides change-vs-heartbeat, so ``set`` always writes
what it's told (no last-value short-circuit).
"""

from __future__ import annotations

from engine.logging_setup import get_logger

VID = 0x04D8
PID = 0xF372

log = get_logger()


class Flag:
    """Owns the HID handle. Resilient to the handle dying under us."""

    def __init__(self) -> None:
        self._dev = None  # hid.device | None
        self.connected = False
        self._open()

    def _open(self) -> bool:
        try:
            import hid

            dev = hid.device()
            dev.open(VID, PID)
            dev.set_nonblocking(0)
            self._dev = dev
            self.connected = True
            log.info("Luxafor Flag opened (VID=%#06x PID=%#06x)", VID, PID)
            return True
        except Exception as e:  # device absent or grabbed by another app
            self._dev = None
            self.connected = False
            log.debug("Flag open failed: %s: %s", type(e).__name__, e)
            return False

    def write(self, report: list[int]) -> bool:
        """Write a raw 8-byte HID report (twice). Reopens if the handle died.

        Returns True if the write landed, False if the device is
        unavailable. Always writes when connected — the loop owns
        change/heartbeat logic. The report is built by ``engine.effects``;
        for a plain color it's the validated static-color command.
        """
        if self._dev is None and not self._open():
            return False
        try:
            self._dev.write(report)
            self._dev.write(report)  # guard against first-write drop
            self.connected = True
            return True
        except Exception as e:
            log.warning("Flag write failed, will reopen: %s: %s", type(e).__name__, e)
            self._close_handle()
            self.connected = False
            return False

    def set(self, rgb: tuple[int, int, int]) -> bool:
        """Convenience: write a solid color (the validated static command)."""
        r, g, b = rgb
        return self.write([0x00, 0x01, 0xFF, int(r), int(g), int(b), 0x00, 0x00])

    def off(self) -> bool:
        return self.set((0, 0, 0))

    def _close_handle(self) -> None:
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass
        self._dev = None

    def close(self) -> None:
        """Turn the flag off and release the handle."""
        try:
            self.off()
        except Exception:
            pass
        self._close_handle()
        self.connected = False
