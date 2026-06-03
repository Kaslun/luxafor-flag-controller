"""The Beacon engine orchestrator and tick loop.

``BeaconEngine`` owns the shared State, Config, device handle, and history
log, and exposes the command methods the API and tray call (override,
pause, replace config, recheck conflict). Its ``run`` coroutine is the
tick loop:

  - Every 5s: sample the mic, expire stale overrides, resolve, and write
    the resulting color to the flag.
  - **Write on change:** when the resolved color differs from the last
    written one, write immediately (twice, per the report quirk).
  - **Heartbeat reassert:** every ``heartbeat_interval_seconds`` re-send
    the current color even if unchanged, to correct silent desync from
    any other process writing the shared HID handle.
  - **Pause** suppresses the heartbeat. Pausing turns the flag off with a
    single change-driven write, then no further writes occur until resume.

Periodically it refreshes conflict detection (60s) and the update check
(startup + 24h), both off-thread so they never stall the loop.
"""

from __future__ import annotations

import asyncio
import datetime as dt

from engine import autostart, conflict, effects, updater
from engine.config import Config, load_config, save_config
from engine.device import Flag
from engine.history import History
from engine.logging_setup import get_logger
from engine.mic import mic_in_use
from engine.palette import dim_rgb, is_color, resolve_rgb
from engine.resolver import ResolvedStatus, resolve
from engine.state import State

log = get_logger()

TICK_SECONDS = 5
CONFLICT_EVERY = 60  # seconds
# Re-check for updates every 6h (plus on startup). The release manifest is a
# static CDN asset with no rate limit, so frequent checks are cheap — this
# keeps long-running instances from sitting on a stale version for a day.
UPDATE_EVERY = 6 * 60 * 60  # seconds


class BeaconEngine:
    def __init__(self) -> None:
        self.state = State()
        self.config: Config = load_config()
        self.device = Flag()
        self.history = History()

        self.state.device_connected = self.device.connected
        self.state.autostart_enabled = autostart.is_enabled()

        self._loop: asyncio.AbstractEventLoop | None = None
        self._wake = asyncio.Event()
        self._stop = asyncio.Event()

        # write bookkeeping
        self._last_report: list[int] | None = None
        self._last_write_at: dt.datetime | None = None

        # history bookkeeping
        self._last_logged: tuple[str, str, str] | None = None

    # ------------------------------------------------------------ commands

    def request_tick(self) -> None:
        """Wake the loop for an immediate re-resolve (thread-safe)."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._wake.set)

    def set_override(
        self, color: str, duration_minutes: int | None, effect: dict | None = None
    ) -> dict:
        if not is_color(color) or color == "off":
            raise ValueError(f"invalid override color {color!r}")
        try:
            norm_effect = effects.normalize_effect(effect)
        except effects.EffectError as e:
            raise ValueError(str(e))
        expiry = None
        if duration_minutes is not None:
            if duration_minutes <= 0:
                raise ValueError("duration_minutes must be positive or null")
            expiry = (
                dt.datetime.now() + dt.timedelta(minutes=duration_minutes)
            ).isoformat()
        ov = {"color": color, "expiry": expiry, "effect": norm_effect}
        with self.state.lock:
            self.state.manual_override = ov
        self.request_tick()
        return ov

    def clear_override(self) -> None:
        with self.state.lock:
            self.state.manual_override = None
        self.request_tick()

    def set_paused(self, paused: bool) -> None:
        with self.state.lock:
            self.state.paused = paused
        self.request_tick()

    def replace_config(self, cfg: Config) -> None:
        self.config = cfg
        save_config(cfg)
        self.request_tick()

    def set_autostart(self, enabled: bool) -> bool:
        result = autostart.set_enabled(enabled)
        with self.state.lock:
            self.state.autostart_enabled = result
        return result

    def recheck_conflict(self) -> dict | None:
        """Synchronous conflict re-check (for the UI 'Re-check' button)."""
        result = conflict.detect()
        with self.state.lock:
            self.state.conflict_detected = result
        return result

    def recheck_update(self) -> dict | None:
        """Synchronous update re-check (for the UI 'Check for updates' button)."""
        result = updater.check()
        with self.state.lock:
            self.state.update_available = result
        return result

    # ------------------------------------------------------------ resolve/write

    def _target_report(self, resolved: ResolvedStatus) -> list[int]:
        """The 8-byte HID report for the resolved status.

        off/paused/disconnected -> solid black; dim -> solid dimmed
        available color; otherwise the color's RGB with its effect applied.
        """
        if resolved.off:
            return effects.build_report((0, 0, 0), None)
        if resolved.dim:
            return effects.build_report(dim_rgb(resolve_rgb(resolved.color)), None)
        return effects.build_report(resolve_rgb(resolved.color), resolved.effect)

    def _apply_resolved(self, resolved: ResolvedStatus, now: dt.datetime) -> None:
        with self.state.lock:
            self.state.color = resolved.color
            self.state.routine = resolved.routine
            self.state.kind = resolved.kind
            self.state.reason = resolved.reason
            self.state.effect = resolved.effect
            self.state.updated_at = now

    def tick(self) -> None:
        """One resolve+write cycle. Safe to call from the loop only."""
        now = dt.datetime.now()

        # 1. sample inputs
        self.state.in_call = mic_in_use()

        # 2. expire a finished override
        ov = self.state.manual_override
        if ov and ov.get("expiry"):
            try:
                if now >= dt.datetime.fromisoformat(ov["expiry"]):
                    with self.state.lock:
                        self.state.manual_override = None
            except ValueError:
                with self.state.lock:
                    self.state.manual_override = None

        # 3. resolve with the connection state we currently believe
        self.state.device_connected = self.device.connected
        resolved = resolve(now, self.state, self.config)

        # 4. realize on the device
        if not self.state.paused:
            report = self._target_report(resolved)
            changed = report != self._last_report
            # Heartbeat re-asserts only solid colors. Animated effects are
            # device-side; re-sending would visibly restart them, so we
            # write those once on change only.
            heartbeat_due = (
                effects.is_solid(resolved.effect)
                and (
                    self._last_write_at is None
                    or (now - self._last_write_at).total_seconds()
                    >= self.config.settings.heartbeat_interval_seconds
                )
            )
            if changed or heartbeat_due:
                self.device.write(report)
                self._last_report = report
                self._last_write_at = now
                # the write tells us the true connection state; if it
                # flipped, re-resolve so the UI reflects it this tick
                if self.device.connected != self.state.device_connected:
                    self.state.device_connected = self.device.connected
                    resolved = resolve(now, self.state, self.config)
        # paused: suppress writes and heartbeat entirely

        # 5. publish + log transitions
        self._apply_resolved(resolved, now)
        sig = (resolved.routine, resolved.color, resolved.kind)
        if sig != self._last_logged:
            self.history.record(
                resolved.routine, resolved.color, resolved.kind, resolved.reason
            )
            self._last_logged = sig
            log.info(
                "%s  %s  (%s)", resolved.routine, resolved.color, resolved.reason
            )

    # ------------------------------------------------------------ run loop

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        log.info("engine loop starting")

        # initial ambient checks (off-thread so startup isn't blocked)
        await self._refresh_conflict()
        await self._refresh_update()

        last_conflict = dt.datetime.now()
        last_update = dt.datetime.now()

        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as e:  # never let one bad tick kill the loop
                log.exception("tick error: %s", e)

            now = dt.datetime.now()
            if (now - last_conflict).total_seconds() >= CONFLICT_EVERY:
                await self._refresh_conflict()
                last_conflict = now
            if (now - last_update).total_seconds() >= UPDATE_EVERY:
                await self._refresh_update()
                last_update = now

            # wait for the next tick or an immediate wake from a command
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=TICK_SECONDS)
            except asyncio.TimeoutError:
                pass
            self._wake.clear()

        log.info("engine loop stopped")

    async def _refresh_conflict(self) -> None:
        try:
            result = await asyncio.to_thread(conflict.detect)
            with self.state.lock:
                self.state.conflict_detected = result
        except Exception as e:
            log.debug("conflict refresh failed: %s", e)

    async def _refresh_update(self) -> None:
        try:
            result = await asyncio.to_thread(updater.check)
            with self.state.lock:
                self.state.update_available = result
        except Exception as e:
            log.debug("update refresh failed: %s", e)

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
            self._loop.call_soon_threadsafe(self._wake.set)

    def shutdown(self) -> None:
        """Final cleanup — turn the flag off, close handles."""
        try:
            self.device.close()
        except Exception:
            pass
        try:
            self.history.close()
        except Exception:
            pass
