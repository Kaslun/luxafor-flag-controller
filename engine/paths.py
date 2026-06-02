"""Per-user AppData paths. Created on first use.

Everything Beacon persists — config, history DB, log — lives under
``%APPDATA%\\Beacon``. On non-Windows (dev machines, CI) we fall back to
a platform-appropriate user directory so the engine and tests still run.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "Beacon"


def app_dir() -> Path:
    """Return (and create) the per-user Beacon data directory."""
    base = os.environ.get("APPDATA")
    if base:
        root = Path(base)
    else:
        # dev / non-Windows fallback
        root = Path.home() / ".config"
    d = root / APP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return app_dir() / "config.json"


def history_path() -> Path:
    return app_dir() / "history.sqlite"


def log_path() -> Path:
    return app_dir() / "beacon.log"
