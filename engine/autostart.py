"""Optional "start with Windows" via the per-user Run key.

Writes ``HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`` — a
user-space key that needs no admin rights and only affects the current
user. The value points at the running executable: the bundled
``beacon.exe`` when frozen, or ``python -m engine`` in development.

This is the supported path to a set-and-forget desk light: enable it once
and Beacon relaunches on every sign-in. Disabling removes the value.

Windows-only; on other platforms the functions are safe no-ops so the
engine and tests run anywhere.
"""

from __future__ import annotations

import sys

from engine.logging_setup import get_logger

log = get_logger()

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "Beacon"

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import winreg
else:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore[assignment]


def _launch_command() -> str:
    """The command Windows should run at sign-in."""
    if getattr(sys, "frozen", False):
        # one-file/one-dir bundle: sys.executable is beacon.exe
        return f'"{sys.executable}"'
    # development: re-run the module with the same interpreter
    return f'"{sys.executable}" -m engine'


def is_enabled() -> bool:
    if not _IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, _VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError as e:  # pragma: no cover - defensive
        log.debug("autostart read failed: %s", e)
        return False


def set_enabled(enabled: bool) -> bool:
    """Enable or disable autostart. Returns the resulting state."""
    if not _IS_WINDOWS:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as k:
            if enabled:
                winreg.SetValueEx(
                    k, _VALUE_NAME, 0, winreg.REG_SZ, _launch_command()
                )
            else:
                try:
                    winreg.DeleteValue(k, _VALUE_NAME)
                except FileNotFoundError:
                    pass
        log.info("autostart %s", "enabled" if enabled else "disabled")
        return enabled
    except OSError as e:
        log.warning("autostart write failed: %s", e)
        return is_enabled()
