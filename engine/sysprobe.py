"""Local Windows signal probes for the extra trigger types.

All probes are user-space, no admin, and degrade to a safe "inactive" value
off Windows so the engine and tests run anywhere:

  - ``idle_seconds()``     — seconds since the last keyboard/mouse input
                             (GetLastInputInfo).
  - ``foreground()``       — (exe_name, window_title), both lower-cased, of the
                             focused window (GetForegroundWindow).
  - ``in_presentation()``  — True while a full-screen / presentation / busy
                             app is running (SHQueryUserNotificationState).
  - ``process_names()``    — lower-cased names of running processes (psutil).
"""

from __future__ import annotations

import sys

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    _shell32 = ctypes.windll.shell32

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    _user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    _shell32.SHQueryUserNotificationState.argtypes = [ctypes.POINTER(ctypes.c_int)]
    _shell32.SHQueryUserNotificationState.restype = ctypes.c_long


def idle_seconds() -> float:
    if not _IS_WINDOWS:
        return 0.0
    try:
        lii = _LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        if not _user32.GetLastInputInfo(ctypes.byref(lii)):
            return 0.0
        # GetTickCount wraps ~49.7 days; the modulo keeps the delta sane
        millis = (_kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF
        return max(0.0, millis / 1000.0)
    except Exception:
        return 0.0


def foreground() -> tuple[str, str]:
    if not _IS_WINDOWS:
        return ("", "")
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return ("", "")
        length = _user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        _user32.GetWindowTextW(hwnd, buf, length + 1)
        title = (buf.value or "").lower()
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = ""
        try:
            import psutil

            exe = psutil.Process(pid.value).name().lower()
        except Exception:
            pass
        return (exe, title)
    except Exception:
        return ("", "")


# QUNS_BUSY=2 (a full-screen app is running), QUNS_RUNNING_D3D_FULL_SCREEN=3,
# QUNS_PRESENTATION_MODE=4 — all "don't disturb me" states.
_PRESENTATION_STATES = {2, 3, 4}


def in_presentation() -> bool:
    if not _IS_WINDOWS:
        return False
    try:
        state = ctypes.c_int(0)
        hr = _shell32.SHQueryUserNotificationState(ctypes.byref(state))
        if hr != 0:
            return False
        return state.value in _PRESENTATION_STATES
    except Exception:
        return False


def process_names() -> list[str]:
    if not _IS_WINDOWS:
        return []
    try:
        import psutil
    except Exception:
        return []
    names: list[str] = []
    for proc in psutil.process_iter(["name"]):
        n = (proc.info.get("name") or "").lower()
        if n:
            names.append(n)
    return names
