"""Atomic single-instance guard via a Windows named mutex.

A lock file + port probe races when two copies start at once (both see no
lock, both bind). A named kernel mutex is atomic: the second process learns
it's second the instant it tries to create the mutex. We keep the lock file
too, but only to discover which port the existing instance is on (so we can
open its dashboard).

The mutex handle is held for the process lifetime — do not close it.
"""

from __future__ import annotations

import sys

_MUTEX_NAME = "Local\\Beacon-Luxafor-SingleInstance"
_ERROR_ALREADY_EXISTS = 183

_IS_WINDOWS = sys.platform == "win32"
_handle = None  # kept alive for the process lifetime


def acquire() -> bool:
    """Return True if we are the first/only instance, False if another holds it."""
    global _handle
    if not _IS_WINDOWS:
        return True
    import ctypes

    kernel32 = ctypes.windll.kernel32
    _handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not _handle:
        return True  # couldn't create the mutex; don't block startup
    return kernel32.GetLastError() != _ERROR_ALREADY_EXISTS
