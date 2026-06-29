"""SQLite event persistence (Phase 11).

A thread-safe ``EventSink`` that stores confirmed events. It is written for
the detection runner's background thread (``check_same_thread=False`` plus a
lock), and exposes simple queries the UI uses for counts and history.

Only the events table is created here; the remaining tables (detections,
profiles, cameras, alerts, settings, reports) will be added as those features
land, alongside a small migration scheme.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from app.core.logging_config import get_logger
from app.core.models import Event

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id        TEXT PRIMARY KEY,
    timestamp       REAL NOT NULL,
    event_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    camera_id       TEXT NOT NULL,
    profile_id      TEXT NOT NULL,
    source_plugin   TEXT NOT NULL,
    message         TEXT NOT NULL,
    screenshot_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
"""


class SqliteEventSink:
    """Persists events to a SQLite database file."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info("Event database ready at %s", self._db_path)

    def handle_event(self, event: Event) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO events (event_id, timestamp, event_type, "
                "severity, camera_id, profile_id, source_plugin, message, "
                "screenshot_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event.event_id, event.timestamp, event.event_type,
                 event.severity.value, event.camera_id, event.profile_id,
                 event.source_plugin, event.message, event.screenshot_path),
            )
            self._conn.commit()

    def count_events(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) AS n FROM events")
            return int(cur.fetchone()["n"])

    def count_since(self, since_timestamp: float) -> int:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) AS n FROM events WHERE timestamp >= ?",
                (since_timestamp,))
            return int(cur.fetchone()["n"])

    def recent(self, limit: int = 100) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
            return cur.fetchall()

    def count_today(self) -> int:
        midnight = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
        return self.count_since(midnight)

    def close(self) -> None:
        with self._lock:
            self._conn.close()
