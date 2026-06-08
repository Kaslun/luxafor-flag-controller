"""Windows session state — is the workstation locked?

Detected via the Terminal Services session flags
(``WTSQuerySessionInformation`` / ``WTSSessionInfoEx``), which report the
*actual* lock state of the current session. This is preferred over the old
input-desktop probe for two reasons:

  - It flips the moment the session locks/unlocks, independent of whether
    the user has touched the lock screen yet.
  - It does NOT trip on the secure desktop a UAC elevation prompt shows —
    a UAC prompt is not a session lock, so the flag won't go "away" for it.

Windows-only; returns False elsewhere so the engine/tests run anywhere.
"""

from __future__ import annotations

import sys

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _WTS_CURRENT_SERVER_HANDLE = 0
    _WTS_CURRENT_SESSION = 0xFFFFFFFF  # (DWORD)-1
    _WTSSessionInfoEx = 25
    # On Windows 8/10/11: LOCK == 0, UNLOCK == 1. (Win7/2008R2 reversed the
    # two due to a defect, but those are out of scope here.)
    _WTS_SESSIONSTATE_LOCK = 0
    _WTS_SESSIONSTATE_UNLOCK = 1

    class _WTSINFOEX_LEVEL1_W(ctypes.Structure):
        _fields_ = [
            ("SessionId", wintypes.LONG),
            ("SessionState", ctypes.c_int),
            ("SessionFlags", wintypes.LONG),
            ("WinStationName", wintypes.WCHAR * 33),
            ("UserName", wintypes.WCHAR * 21),
            ("DomainName", wintypes.WCHAR * 18),
            ("LogonTime", wintypes.LARGE_INTEGER),
            ("ConnectTime", wintypes.LARGE_INTEGER),
            ("DisconnectTime", wintypes.LARGE_INTEGER),
            ("LastInputTime", wintypes.LARGE_INTEGER),
            ("CurrentTime", wintypes.LARGE_INTEGER),
        ]

    class _WTSINFOEX_LEVEL_W(ctypes.Union):
        _fields_ = [("WTSInfoExLevel1", _WTSINFOEX_LEVEL1_W)]

    class _WTSINFOEXW(ctypes.Structure):
        _fields_ = [("Level", wintypes.DWORD), ("Data", _WTSINFOEX_LEVEL_W)]


def screen_locked() -> bool:
    if not _IS_WINDOWS:
        return False
    try:
        wts = ctypes.windll.wtsapi32
        buf = ctypes.POINTER(_WTSINFOEXW)()
        nbytes = wintypes.DWORD(0)
        ok = wts.WTSQuerySessionInformationW(
            _WTS_CURRENT_SERVER_HANDLE,
            _WTS_CURRENT_SESSION,
            _WTSSessionInfoEx,
            ctypes.byref(buf),
            ctypes.byref(nbytes),
        )
        if not ok or not buf:
            return False
        try:
            info = buf.contents
            # only the Level-1 union member is documented for this class
            if info.Level != 1:
                return False
            flags = info.Data.WTSInfoExLevel1.SessionFlags
        finally:
            ctypes.windll.wtsapi32.WTSFreeMemory(buf)
        return flags == _WTS_SESSIONSTATE_LOCK
    except Exception:
        return False
