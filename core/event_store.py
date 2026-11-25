from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any


class SQLiteEventStore:
    """
    Persistent audit store for alerts and operational events.

    SQLite is used because it is:
      - built into Python
      - transactional
      - queryable by the future FastAPI/dashboard layer
      - much safer for structured event history than ad-hoc CSV files
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL UNIQUE,
                        timestamp TEXT NOT NULL,
                        reading_id INTEGER,
                        lifecycle TEXT NOT NULL,
                        overall_status TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        anomaly_count INTEGER NOT NULL,
                        summary TEXT NOT NULL,
                        ml_status TEXT,
                        ml_severity TEXT,
                        ml_decision_score REAL,
                        rule_events_json TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL UNIQUE,
                        timestamp TEXT NOT NULL,
                        reading_id INTEGER,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        source TEXT NOT NULL,
                        message TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_alerts_timestamp
                    ON alerts(timestamp)
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_alerts_severity
                    ON alerts(severity)
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_timestamp
                    ON events(timestamp)
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_events_type
                    ON events(event_type)
                    """
                )

                connection.commit()

    def save_alert(
        self,
        payload: dict[str, Any],
    ) -> None:

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO alerts (
                        event_id,
                        timestamp,
                        reading_id,
                        lifecycle,
                        overall_status,
                        severity,
                        fingerprint,
                        anomaly_count,
                        summary,
                        ml_status,
                        ml_severity,
                        ml_decision_score,
                        rule_events_json,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["event_id"],
                        payload["timestamp"],
                        payload.get("reading_id"),
                        payload["lifecycle"],
                        payload["overall_status"],
                        payload["severity"],
                        payload["fingerprint"],
                        payload["anomaly_count"],
                        payload["summary"],
                        payload.get("ml_status"),
                        payload.get("ml_severity"),
                        payload.get("ml_decision_score"),
                        json.dumps(
                            payload.get("rule_events", []),
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            payload,
                            ensure_ascii=False,
                        ),
                    ),
                )
                connection.commit()

    def save_event(
        self,
        payload: dict[str, Any],
    ) -> None:

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO events (
                        event_id,
                        timestamp,
                        reading_id,
                        event_type,
                        severity,
                        source,
                        message,
                        payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["event_id"],
                        payload["timestamp"],
                        payload.get("reading_id"),
                        payload["event_type"],
                        payload["severity"],
                        payload["source"],
                        payload["message"],
                        json.dumps(
                            payload,
                            ensure_ascii=False,
                        ),
                    ),
                )
                connection.commit()

    def latest_alerts(
        self,
        limit: int = 50,
    ) -> list[dict[str, Any]]:

        limit = max(1, min(int(limit), 500))

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM alerts
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            self._row_to_dict(row)
            for row in rows
        ]

    def latest_events(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:

        limit = max(1, min(int(limit), 1000))

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT *
                    FROM events
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            self._row_to_dict(row)
            for row in rows
        ]

    def latest_alert_state(
        self,
    ) -> dict[str, Any] | None:

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT *
                    FROM alerts
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ).fetchone()

        if row is None:
            return None

        return self._row_to_dict(row)

    def counts(self) -> dict[str, int]:
        with self._lock:
            with self._connect() as connection:
                alert_count = connection.execute(
                    "SELECT COUNT(*) FROM alerts"
                ).fetchone()[0]

                event_count = connection.execute(
                    "SELECT COUNT(*) FROM events"
                ).fetchone()[0]

        return {
            "alerts": int(alert_count),
            "events": int(event_count),
        }

    @staticmethod
    def _row_to_dict(
        row: sqlite3.Row,
    ) -> dict[str, Any]:

        result = dict(row)

        for key in (
            "rule_events_json",
            "payload_json",
        ):
            if key in result:
                try:
                    result[key] = json.loads(
                        result[key]
                    )
                except (
                    json.JSONDecodeError,
                    TypeError,
                ):
                    pass

        return result
