"""Detect the Luxafor v2 app, which fights Beacon for the shared HID handle.

The v2 app is an ongoing writer conflict, not a one-time setup step: while
it runs, last-writer-wins on the shared handle means it intermittently
overwrites Beacon's color. The heartbeat limits desync but doesn't end the
fight — v2 must be quit and removed from startup. Beacon can't do that for
the user (quitting/altering another app's startup looks like malware and
may exceed rights on a locked-down machine), so this module only detects
and the UI guides.

Detection is user-space, no admin:
  - running:  scan processes for the v2 executable.
  - startup:  per-user Run key + the Startup folder.

Returns the design's two-flag shape so the two-step conflict UI can render
each state independently:
    {"luxafor_v2_running": bool, "luxafor_v2_startup": bool}  or  None
``None`` means no conflict (both flags false).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from engine.logging_setup import get_logger

log = get_logger()

# The vendor executable is named "Luxafor.exe". We match case-insensitively
# and also accept any process whose name simply starts with "luxafor" (but
# never our own bundled "beacon.exe").
_V2_PROCESS_HINTS = ("luxafor",)
_SELF_HINTS = ("beacon",)

_IS_WINDOWS = sys.platform == "win32"

# Log the full process list once on first detection so we can confirm the
# exact executable name in the field.
_logged_process_names = False


def v2_running() -> bool:
    if not _IS_WINDOWS:
        return False
    try:
        import psutil
    except ImportError:  # pragma: no cover
        return False

    global _logged_process_names
    names: list[str] = []
    found = False
    for proc in psutil.process_iter(["name"]):
        name = (proc.info.get("name") or "").lower()
        if not name:
            continue
        names.append(name)
        if any(name.startswith(h) for h in _SELF_HINTS):
            continue
        if any(h in name for h in _V2_PROCESS_HINTS):
            found = True

    if found and not _logged_process_names:
        log.info("Luxafor v2 conflict: matched process among %d running", len(names))
        _logged_process_names = True
    return found


def _startup_folder_has_luxafor() -> bool:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return False
    startup = (
        Path(appdata)
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )
    if not startup.exists():
        return False
    try:
        for entry in startup.iterdir():
            if "luxafor" in entry.name.lower():
                return True
    except OSError:
        return False
    return False


def _run_key_has_luxafor() -> bool:
    if not _IS_WINDOWS:
        return False
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                blob = f"{name} {value}".lower()
                if "luxafor" in blob and "beacon" not in blob:
                    return True
    except FileNotFoundError:
        return False
    return False


def v2_in_startup() -> bool:
    if not _IS_WINDOWS:
        return False
    try:
        return _run_key_has_luxafor() or _startup_folder_has_luxafor()
    except Exception as e:  # pragma: no cover - defensive
        log.debug("startup check failed: %s", e)
        return False


def detect() -> dict | None:
    """Run both checks. Returns the two-flag dict, or None if all clear."""
    running = v2_running()
    startup = v2_in_startup()
    if not running and not startup:
        return None
    return {"luxafor_v2_running": running, "luxafor_v2_startup": startup}
