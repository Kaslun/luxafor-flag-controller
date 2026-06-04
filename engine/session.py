"""Windows session state — currently: is the screen locked?

Detected without admin by inspecting the input desktop. When the machine
is locked, the secure "Winlogon" desktop is active and a normal process
either can't open the input desktop or sees a non-"Default" desktop name.

Windows-only; returns False elsewhere so the engine/tests run anywhere.
"""

from __future__ import annotations

import sys

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes

    _DESKTOP_SWITCHDESKTOP = 0x0100
    _UOI_NAME = 2


def screen_locked() -> bool:
    if not _IS_WINDOWS:
        return False
    user32 = ctypes.windll.user32
    hdesk = user32.OpenInputDesktop(0, False, _DESKTOP_SWITCHDESKTOP)
    if not hdesk:
        # secure desktop active (lock screen / UAC) -> treat as locked
        return True
    try:
        needed = ctypes.c_ulong(0)
        user32.GetUserObjectInformationW(hdesk, _UOI_NAME, None, 0, ctypes.byref(needed))
        size = max(needed.value, 2)
        buf = ctypes.create_unicode_buffer(size // 2 + 1)
        ok = user32.GetUserObjectInformationW(
            hdesk, _UOI_NAME, buf, size, ctypes.byref(needed)
        )
        name = buf.value if ok else "Default"
    finally:
        user32.CloseDesktop(hdesk)
    return name.lower() != "default"
