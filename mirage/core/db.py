"""SQLite event store for core. One table, events in contracts.Event shape."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from mirage.contracts import Event

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    type TEXT NOT NULL,
    host TEXT NOT NULL,
    user TEXT NOT NULL DEFAULT '',
    ref TEXT NOT NULL DEFAULT '',
    details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS events_ts ON events (ts);
"""


class EventStore:
    """Thread-safe (one connection guarded by a lock) so uvicorn worker threads can share it."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def add(self, event: Event) -> int:
        return self.add_many([event])[0]

    def add_many(self, events: list[Event]) -> list[int]:
        ids = []
        with self._lock:
            for e in events:
                cur = self._conn.execute(
                    "INSERT INTO events (ts, type, host, user, ref, details) VALUES (?, ?, ?, ?, ?, ?)",
                    (float(e.ts), e.type, e.host, e.user, e.ref, json.dumps(e.details)),
                )
                ids.append(int(cur.lastrowid))
            self._conn.commit()
        return ids

    def all(self, since: float | None = None, type: str | None = None) -> list[Event]:
        sql, args = "SELECT ts, type, host, user, ref, details FROM events WHERE 1=1", []
        if since is not None:
            sql += " AND ts >= ?"
            args.append(since)
        if type is not None:
            sql += " AND type = ?"
            args.append(type)
        sql += " ORDER BY ts, id"
        with self._lock:
            rows = self._conn.execute(sql, args).fetchall()
        return [Event(ts, t, host, user, ref, json.loads(details))
                for ts, t, host, user, ref, details in rows]

    def count(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def reset(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM events")
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
