"""Windows mic-capture detection via the consent-store registry.

This is the validated approach from the prototype: we read the
CapabilityAccessManager consent store for active microphone capture
streams (``LastUsedTimeStart`` set, ``LastUsedTimeStop == 0``) rather
than sampling audio volume — volume is wrong in a noisy open office.

Top-level keys catch packaged apps (new Teams, Slack huddles); the
``NonPackaged`` branch catches Zoom, classic Teams, and desktop Slack.

Windows-only. On other platforms ``mic_in_use`` returns False so the
rest of the engine (and the test suite) runs anywhere.
"""

from __future__ import annotations

import sys

_MIC_BASE = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion"
    r"\CapabilityAccessManager\ConsentStore\microphone"
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


def _mic_active(start, stop) -> bool:
    """A capture stream is live when it has a start time and no stop time.

    ``stop == 0`` means "currently capturing". ``start`` being falsy (0 or
    None) means the app has never captured, so it's inactive.
    """
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


def mic_capturers() -> list[str]:
    """Names of apps currently holding an active mic capture stream."""
    if not _IS_WINDOWS:
        return []

    root = winreg.HKEY_CURRENT_USER
    active: list[str] = []
    try:
        with winreg.OpenKey(root, _MIC_BASE) as base:
            apps = _enum_subkeys(base)
    except FileNotFoundError:
        return active

    for app in apps:
        if app == "NonPackaged":
            np = _MIC_BASE + "\\NonPackaged"
            try:
                with winreg.OpenKey(root, np) as npk:
                    subs = _enum_subkeys(npk)
            except FileNotFoundError:
                subs = []
            for s in subs:
                v = _read_app(root, np, s)
                if v and _mic_active(*v):
                    active.append(s)
        else:
            v = _read_app(root, _MIC_BASE, app)
            if v and _mic_active(*v):
                active.append(app)
    return active


def mic_in_use() -> bool:
    return len(mic_capturers()) > 0


def capturer_matches(app: str, capturers: list[str] | None = None) -> bool:
    """True if any current mic capturer's name contains ``app`` (case-insensitive).

    Registry capturer names are munged executable paths (e.g.
    ``C:#Program Files#Zoom#bin#Zoom.exe``), so a substring match on a short
    token like ``"zoom"`` or ``"teams"`` is the practical matching rule.
    Empty ``app`` never matches.
    """
    needle = (app or "").strip().lower()
    if not needle:
        return False
    caps = mic_capturers() if capturers is None else capturers
    return any(needle in c.lower() for c in caps)


if __name__ == "__main__":  # ad-hoc debugging: prints live capturers
    caps = mic_capturers()
    print("mic in use:", bool(caps))
    for c in caps:
        print("  -", c)
