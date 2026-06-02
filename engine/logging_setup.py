"""Rotating file logger.

In dev (stdout attached) we also log to the console; in the bundled
windowed exe there is no console, so the rotating file in AppData is the
only record. Update-check failures and HID hiccups are logged here and
never surfaced to the user (spec: fail silent).
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from engine.paths import log_path

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the root 'beacon' logger once. Idempotent."""
    global _CONFIGURED
    logger = logging.getLogger("beacon")
    if _CONFIGURED:
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path(), maxBytes=1_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Console handler only when a real stdout is attached (dev runs).
    if sys.stdout is not None and sys.stdout.isatty():
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(fmt)
        logger.addHandler(console)

    _CONFIGURED = True
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("beacon")
