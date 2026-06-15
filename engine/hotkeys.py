"""Global keyboard-shortcut triggers via Win32 ``RegisterHotKey``.

A hotkey trigger toggles its status on/off when its combo is pressed,
anywhere — even when Beacon doesn't have focus. We use ``RegisterHotKey``
(not a low-level keyboard hook): the OS only ever notifies us about the
exact combos we registered, so this is NOT a keylogger and never sees any
other keystroke.

``RegisterHotKey`` with a NULL window posts ``WM_HOTKEY`` to the
*registering thread's* message queue, so all register/unregister calls and
the message loop live on one dedicated daemon thread. The engine posts
thread messages to ask it to re-register (config changed) or quit.

Windows-only; a no-op everywhere else so the engine/tests run anywhere.
"""

from __future__ import annotations

import sys
import threading

from engine.logging_setup import get_logger

log = get_logger()

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32

    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000

    WM_HOTKEY = 0x0312
    WM_APP_RELOAD = 0x8001  # WM_APP + 1
    WM_APP_SUSPEND = 0x8002  # unregister all (while the UI captures a combo)
    WM_APP_RESUME = 0x8003  # re-register after capture

    _user32.RegisterHotKey.restype = wintypes.BOOL
    _user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    _user32.UnregisterHotKey.restype = wintypes.BOOL
    _user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.GetMessageW.restype = ctypes.c_int
    _user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    _user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
    _user32.PostThreadMessageW.restype = wintypes.BOOL
    _user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p]


def _mods_of(params: dict) -> int:
    mods = 0
    if params.get("ctrl"):
        mods |= MOD_CONTROL
    if params.get("alt"):
        mods |= MOD_ALT
    if params.get("shift"):
        mods |= MOD_SHIFT
    if params.get("win"):
        mods |= MOD_WIN
    return mods


class HotkeyManager:
    """Owns the hotkey listener thread for the engine's hotkey triggers."""

    def __init__(self, engine) -> None:
        self.engine = engine
        self._thread: threading.Thread | None = None
        self._tid: int | None = None
        self._ready = threading.Event()

    # ------------------------------------------------------------ lifecycle

    def start(self) -> None:
        if not _IS_WINDOWS or self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="beacon-hotkeys"
        )
        self._thread.start()

    def reload(self) -> None:
        """Re-register hotkeys (call after the config changes)."""
        if not _IS_WINDOWS or not self._ready.is_set() or self._tid is None:
            return
        _user32.PostThreadMessageW(self._tid, WM_APP_RELOAD, None, None)

    def stop(self) -> None:
        if not _IS_WINDOWS or not self._ready.is_set() or self._tid is None:
            return
        _user32.PostThreadMessageW(self._tid, 0x0012, None, None)  # WM_QUIT

    def _post(self, msg: int) -> bool:
        if not _IS_WINDOWS or not self._ready.is_set() or self._tid is None:
            return False
        _user32.PostThreadMessageW(self._tid, msg, None, None)
        return True

    def suspend(self) -> None:
        """Temporarily release all combos so the UI can capture one of them."""
        self._post(WM_APP_SUSPEND)

    def resume(self) -> None:
        """Re-register combos after a capture."""
        self._post(WM_APP_RESUME)

    # ------------------------------------------------------------ internals

    def _specs(self) -> list[tuple[str, int, int]]:
        """(trigger_id, modifiers, vk) for each enabled, fully-defined hotkey."""
        out: list[tuple[str, int, int]] = []
        for t in self.engine.config.triggers:
            if t.type != "hotkey" or not t.enabled:
                continue
            p = t.params or {}
            try:
                vk = int(p.get("vk") or 0)
            except (TypeError, ValueError):
                vk = 0
            mods = _mods_of(p)
            if vk and mods:  # require a key + at least one modifier
                out.append((t.id, mods | MOD_NOREPEAT, vk))
        return out

    def _register_all(self, idmap: dict[int, str]) -> None:
        idmap.clear()
        failed: list[str] = []
        for i, (tid, mods, vk) in enumerate(self._specs(), start=1):
            try:
                if _user32.RegisterHotKey(None, i, mods, vk):
                    idmap[i] = tid
                else:
                    failed.append(tid)
                    log.warning("hotkey %s: combo unavailable (already in use?)", tid)
            except Exception as e:  # pragma: no cover - defensive
                failed.append(tid)
                log.debug("hotkey %s register error: %s", tid, e)
        self._report_errors(failed)

    def _report_errors(self, failed: list[str]) -> None:
        try:
            self.engine.set_hotkey_errors(failed)
        except Exception:
            pass

    def _unregister_all(self, idmap: dict[int, str]) -> None:
        for i in list(idmap):
            try:
                _user32.UnregisterHotKey(None, i)
            except Exception:
                pass
        idmap.clear()

    def _run(self) -> None:  # pragma: no cover - Windows message loop
        self._tid = _kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        # force the thread message queue into existence before we mark ready,
        # so PostThreadMessage from other threads isn't dropped
        _user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)
        idmap: dict[int, str] = {}
        suspended = False
        self._register_all(idmap)
        self._ready.set()
        log.info("hotkey listener started (%d registered)", len(idmap))
        try:
            while True:
                ret = _user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret in (0, -1):  # WM_QUIT or error
                    break
                if msg.message == WM_HOTKEY:
                    tid = idmap.get(int(msg.wParam))
                    if tid:
                        try:
                            self.engine.toggle_hotkey(tid)
                        except Exception:
                            log.exception("toggle_hotkey failed")
                elif msg.message == WM_APP_RELOAD:
                    if not suspended:
                        self._unregister_all(idmap)
                        self._register_all(idmap)
                elif msg.message == WM_APP_SUSPEND:
                    suspended = True
                    self._unregister_all(idmap)
                elif msg.message == WM_APP_RESUME:
                    suspended = False
                    self._unregister_all(idmap)
                    self._register_all(idmap)
        finally:
            self._unregister_all(idmap)
            log.info("hotkey listener stopped")
