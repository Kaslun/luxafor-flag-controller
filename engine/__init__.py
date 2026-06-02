"""Beacon engine — Luxafor Flag 2 desk-light status bridge.

The engine owns the HID handle, runs the pure resolver, reads the mic-
capture registry, serves a localhost FastAPI, and drives a tray icon —
all in one process. See README.md for the architecture overview.
"""

from engine.version import __version__

__all__ = ["__version__"]
