"""SQLite history of state transitions.

A single ``transitions`` table in ``%APPDATA%\\Beacon\\history.sqlite``.
The loop calls ``record`` only on an actual change (it owns the
change-detection), so each row is a genuine transition. No retention
policy in v1.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import threading
from pathlib import Path

from engine.logging_setup import get_logger
from engine.paths import history_path

log = get_logger()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transitions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    routine TEXT NOT NULL,
    slot    TEXT NOT NULL,
    kind    TEXT NOT NULL,
    reason  TEXT NOT NULL
);
"""


class History:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or history_path()
        self._lock = threading.Lock()
        # check_same_thread=False: the loop task and tray may both touch it;
        # the lock serializes access.
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def record(self, routine: str, slot: str, kind: str, reason: str) -> None:
        ts = dt.datetime.now().isoformat()
        try:
            with self._lock:
                self._conn.execute(
                    "INSERT INTO transitions (ts, routine, slot, kind, reason) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (ts, routine, slot, kind, reason),
                )
                self._conn.commit()
        except sqlite3.Error as e:  # never let history kill the loop
            log.warning("history write failed: %s", e)

    def recent(self, limit: int = 50) -> list[dict]:
        try:
            with self._lock:
                cur = self._conn.execute(
                    "SELECT ts, routine, slot, kind, reason FROM transitions "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
                rows = cur.fetchall()
        except sqlite3.Error as e:
            log.warning("history read failed: %s", e)
            return []
        return [
            {"ts": r[0], "routine": r[1], "slot": r[2], "kind": r[3], "reason": r[4]}
            for r in rows
        ]

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
