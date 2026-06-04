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
import os
import threading
import time

from engine import autostart, conflict, effects, mic, selfupdate, session, updater, webcam
from engine.config import Config, Trigger, load_config, save_config
from engine.device import Flag
from engine.history import History
from engine.logging_setup import get_logger
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

    def set_preview(self, color: str, effect: dict | None) -> dict:
        """Live preview while the user picks a color (highest priority)."""
        if not is_color(color):
            raise ValueError(f"invalid preview color {color!r}")
        pv = {"color": color, "effect": effects.normalize_effect(effect)}
        with self.state.lock:
            self.state.preview = pv
        self.request_tick()
        return pv

    def clear_preview(self) -> None:
        with self.state.lock:
            self.state.preview = None
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

    def apply_update(self) -> dict:
        """Download + verify the update, launch the swap, then exit so the
        new exe can replace this one and relaunch. Raises on failure."""
        info = self.state.update_available
        result = selfupdate.apply(info)  # raises if not frozen / no update / bad checksum
        # give the HTTP response time to flush, then exit hard so the file
        # unlocks for the swap script (which waits on our PID).
        threading.Timer(1.0, self._exit_for_update).start()
        return result

    def _exit_for_update(self) -> None:
        try:
            self.device.close()
        except Exception:
            pass
        os._exit(0)

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

    def _trigger_active(self, t: Trigger, signals: dict) -> bool:
        """Evaluate one trigger's condition against the sampled signals."""
        if t.type == "mic":
            return signals["mic"]
        if t.type == "lock":
            return signals["lock"]
        if t.type == "webcam":
            return signals["webcam"]
        if t.type == "mic_app":
            return mic.capturer_matches(
                t.params.get("app", ""), signals["mic_capturers"]
            )
        return False

    def _evaluate_triggers(self) -> tuple[dict, list[dict]]:
        """Sample raw signals once, then evaluate every enabled trigger.

        Each detector is isolated: a bad app string or a flaky registry read
        can't take down the tick. Returns (signals, active_triggers) where
        active_triggers is the resolver-/UI-ready list of firing triggers.
        """
        def _safe(fn, default):
            try:
                return fn()
            except Exception:
                log.debug("signal sample failed: %s", fn, exc_info=True)
                return default

        mic_caps = _safe(mic.mic_capturers, [])
        cam_caps = _safe(webcam.webcam_capturers, [])
        locked = _safe(session.screen_locked, False)
        signals = {
            "mic": bool(mic_caps),
            "webcam": bool(cam_caps),
            "lock": bool(locked),
            "mic_capturers": mic_caps,
            "webcam_capturers": cam_caps,
        }

        active: list[dict] = []
        for t in self.config.triggers:
            if not t.enabled:
                continue
            try:
                if self._trigger_active(t, signals):
                    active.append(
                        {
                            "id": t.id,
                            "name": t.name,
                            "type": t.type,
                            "color": t.color,
                            "priority": t.priority,
                            "effect": t.effect,
                        }
                    )
            except Exception:
                log.debug("trigger %r evaluation failed", t.id, exc_info=True)
        return signals, active

    def tick(self) -> None:
        """One resolve+write cycle. Safe to call from the loop only."""
        now = dt.datetime.now()

        # 1. sample inputs + evaluate triggers
        signals, active = self._evaluate_triggers()
        with self.state.lock:
            self.state.signals = signals
            self.state.active_triggers = active
            self.state.in_call = signals["mic"]  # derived convenience
            self.state.locked = signals["lock"]

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
                # Leaving a built-in pattern? A static write alone won't stop
                # it (the firmware resumes the animation), so send an explicit
                # pattern-off first. ``_last_report is None`` covers startup,
                # where the device may still be mid-pattern from a prior run.
                target_is_pattern = effects.report_is_pattern(report)
                was_pattern = effects.report_is_pattern(self._last_report)
                if not target_is_pattern and (was_pattern or self._last_report is None):
                    self.device.write(effects.PATTERN_OFF_REPORT)
                    time.sleep(0.06)  # let the firmware settle before the color
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

        last_conflict = 0.0
        last_update = 0.0

        # The whole iteration is guarded: an unhandled error here would
        # silently kill the task (its traceback goes to a None stderr in the
        # windowed exe), freezing the flag on its last color. Nothing short
        # of _stop may end this loop.
        while not self._stop.is_set():
            try:
                self.tick()
                now = dt.datetime.now().timestamp()
                if now - last_conflict >= CONFLICT_EVERY:
                    await self._refresh_conflict()
                    last_conflict = now
                if now - last_update >= UPDATE_EVERY:
                    await self._refresh_update()
                    last_update = now
            except Exception:
                log.exception("engine loop iteration failed (continuing)")

            # wait for the next tick or an immediate wake from a command;
            # never let the wait itself end the loop
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=TICK_SECONDS)
            except (asyncio.TimeoutError, TimeoutError):
                pass
            except Exception:
                log.exception("engine loop wait failed; backing off")
                try:
                    await asyncio.sleep(TICK_SECONDS)
                except Exception:
                    pass
            finally:
                try:
                    self._wake.clear()
                except Exception:
                    pass

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
