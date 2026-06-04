"""Windows webcam-capture detection via the consent-store registry.

A direct sibling of ``engine.mic``: same CapabilityAccessManager consent
store, ``webcam`` capability instead of ``microphone``. A capture stream is
live when it has a ``LastUsedTimeStart`` and no ``LastUsedTimeStop``
(``== 0``). Top-level keys catch packaged apps; the ``NonPackaged`` branch
catches classic desktop apps (Zoom, OBS, etc).

Windows-only. On other platforms the public functions degrade to
"not in use" so the engine and tests run anywhere.
"""

from __future__ import annotations

import sys

_CAM_BASE = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion"
    r"\CapabilityAccessManager\ConsentStore\webcam"
)

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import winreg
else:  # pragma: no cover - non-Windows dev/CI fallback
    winreg = None  # type: ignore[assignment]


def _enum_subkeys(key) -> list[str]:
    out: list[str] = []
    i = 0
    while True:
        try:
            out.append(winreg.EnumKey(key, i))
            i += 1
        except OSError:
            return out


def _cam_active(start, stop) -> bool:
    """Live when it has a start time and no stop time (stop == 0)."""
    return bool(start) and (stop == 0 or stop is None)


def _read_app(root, path: str, app: str):
    """Return (start, stop) for an app key, or None if the key is absent."""
    try:
        with winreg.OpenKey(root, path + "\\" + app) as k:
            try:
                start, _ = winreg.QueryValueEx(k, "LastUsedTimeStart")
            except FileNotFoundError:
                start = None
            try:
                stop, _ = winreg.QueryValueEx(k, "LastUsedTimeStop")
            except FileNotFoundError:
                stop = None
            return (start, stop)
    except FileNotFoundError:
        return None


def webcam_capturers() -> list[str]:
    """Names of apps currently holding an active webcam capture stream."""
    if not _IS_WINDOWS:
        return []

    root = winreg.HKEY_CURRENT_USER
    active: list[str] = []
    try:
        with winreg.OpenKey(root, _CAM_BASE) as base:
            apps = _enum_subkeys(base)
    except FileNotFoundError:
        return active

    for app in apps:
        if app == "NonPackaged":
            np = _CAM_BASE + "\\NonPackaged"
            try:
                with winreg.OpenKey(root, np) as npk:
                    subs = _enum_subkeys(npk)
            except FileNotFoundError:
                subs = []
            for s in subs:
                v = _read_app(root, np, s)
                if v and _cam_active(*v):
                    active.append(s)
        else:
            v = _read_app(root, _CAM_BASE, app)
            if v and _cam_active(*v):
                active.append(app)
    return active


def webcam_in_use() -> bool:
    return len(webcam_capturers()) > 0


if __name__ == "__main__":  # ad-hoc debugging: prints live capturers
    caps = webcam_capturers()
    print("webcam in use:", bool(caps))
    for c in caps:
        print("  -", c)
