from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from config.alert_config import (
    ALERT_REMINDER_SECONDS,
)
from core.event_store import SQLiteEventStore


@dataclass
class AlertDispatch:
    alert_payload: dict[str, Any] | None
    event_payloads: list[dict[str, Any]]
    suppressed: bool

    def has_alert(self) -> bool:
        return self.alert_payload is not None


class AlertManager:
    """
    Converts unified anomaly output into a durable alert lifecycle.

    Lifecycle:
        NORMAL
          ↓ anomaly appears
        OPEN
          ↓ same anomaly changes
        UPDATE
          ↓ unchanged long enough
        REMINDER
          ↓ system normal
        RESOLVED

    Identical telemetry every 2 seconds does NOT create alert spam.
    """

    def __init__(
        self,
        event_store: SQLiteEventStore,
        reminder_seconds: int = ALERT_REMINDER_SECONDS,
    ) -> None:

        self.event_store = event_store
        self.reminder_seconds = max(
            1,
            int(reminder_seconds),
        )

        self._active_fingerprint: str | None = None
        self._active_severity: str = "NONE"
        self._last_published_at: datetime | None = None

        self._restore_state()

    def process(
        self,
        telemetry: dict[str, Any],
        anomaly: dict[str, Any],
    ) -> AlertDispatch:

        timestamp = str(
            telemetry.get(
                "timestamp",
                datetime.now(
                    timezone.utc
                ).isoformat(),
            )
        )

        reading_id = telemetry.get(
            "reading_id"
        )

        now = self._parse_timestamp(
            timestamp
        )

        anomaly_count = int(
            anomaly.get(
                "combined_alert_count",
                0,
            )
        )

        is_anomalous = (
            anomaly_count > 0
            or anomaly.get(
                "overall_status",
                "NORMAL",
            ) != "NORMAL"
        )

        if not is_anomalous:
            return self._handle_normal(
                timestamp=timestamp,
                reading_id=reading_id,
            )

        fingerprint = self._fingerprint(
            anomaly
        )

        severity = str(
            anomaly.get(
                "highest_severity",
                "MEDIUM",
            )
        )

        if self._active_fingerprint is None:
            lifecycle = "OPEN"

        elif (
            fingerprint
            != self._active_fingerprint
            or severity
            != self._active_severity
        ):
            lifecycle = "UPDATE"

        elif self._should_remind(
            now
        ):
            lifecycle = "REMINDER"

        else:
            return AlertDispatch(
                alert_payload=None,
                event_payloads=[],
                suppressed=True,
            )

        alert_payload = self._build_alert_payload(
            timestamp=timestamp,
            reading_id=reading_id,
            lifecycle=lifecycle,
            anomaly=anomaly,
            fingerprint=fingerprint,
        )

        event_payloads = self._build_event_payloads(
            timestamp=timestamp,
            reading_id=reading_id,
            lifecycle=lifecycle,
            anomaly=anomaly,
            alert_event_id=alert_payload[
                "event_id"
            ],
        )

        self.event_store.save_alert(
            alert_payload
        )

        for event_payload in event_payloads:
            self.event_store.save_event(
                event_payload
            )

        self._active_fingerprint = fingerprint
        self._active_severity = severity
        self._last_published_at = now

        return AlertDispatch(
            alert_payload=alert_payload,
            event_payloads=event_payloads,
            suppressed=False,
        )

    # ==========================================================
    # Lifecycle handling
    # ==========================================================

    def _handle_normal(
        self,
        timestamp: str,
        reading_id: Any,
    ) -> AlertDispatch:

        if self._active_fingerprint is None:
            return AlertDispatch(
                alert_payload=None,
                event_payloads=[],
                suppressed=False,
            )

        previous_fingerprint = (
            self._active_fingerprint
        )
        previous_severity = (
            self._active_severity
        )

        alert_payload = {
            "event_id": self._new_id("alert"),
            "timestamp": timestamp,
            "reading_id": reading_id,
            "lifecycle": "RESOLVED",
            "overall_status": "NORMAL",
            "severity": "NONE",
            "fingerprint": previous_fingerprint,
            "anomaly_count": 0,
            "summary": (
                "Previously active anomaly condition has returned "
                "to normal operating state."
            ),
            "ml_status": "NORMAL",
            "ml_severity": "NONE",
            "ml_decision_score": None,
            "rule_events": [],
            "previous_severity": previous_severity,
        }

        event_payload = {
            "event_id": self._new_id("event"),
            "timestamp": timestamp,
            "reading_id": reading_id,
            "event_type": "ALERT_RESOLVED",
            "severity": "NONE",
            "source": "AlertManager",
            "message": (
                f"Resolved active {previous_severity} anomaly alert."
            ),
            "parent_alert_event_id": alert_payload[
                "event_id"
            ],
            "fingerprint": previous_fingerprint,
        }

        self.event_store.save_alert(
            alert_payload
        )
        self.event_store.save_event(
            event_payload
        )

        self._active_fingerprint = None
        self._active_severity = "NONE"
        self._last_published_at = (
            self._parse_timestamp(
                timestamp
            )
        )

        return AlertDispatch(
            alert_payload=alert_payload,
            event_payloads=[
                event_payload
            ],
            suppressed=False,
        )

    def _should_remind(
        self,
        now: datetime,
    ) -> bool:

        if self._last_published_at is None:
            return True

        elapsed = (
            now
            - self._last_published_at
        ).total_seconds()

        # If simulator/replay time moves backwards, do not spam.
        if elapsed < 0:
            return False

        return (
            elapsed
            >= self.reminder_seconds
        )

    # ==========================================================
    # Payload construction
    # ==========================================================

    def _build_alert_payload(
        self,
        timestamp: str,
        reading_id: Any,
        lifecycle: str,
        anomaly: dict[str, Any],
        fingerprint: str,
    ) -> dict[str, Any]:

        return {
            "event_id": self._new_id("alert"),
            "timestamp": timestamp,
            "reading_id": reading_id,
            "lifecycle": lifecycle,
            "overall_status": anomaly.get(
                "overall_status",
                "ATTENTION",
            ),
            "severity": anomaly.get(
                "highest_severity",
                "MEDIUM",
            ),
            "fingerprint": fingerprint,
            "anomaly_count": int(
                anomaly.get(
                    "combined_alert_count",
                    0,
                )
            ),
            "summary": anomaly.get(
                "summary",
                "Abnormal energy behavior detected.",
            ),
            "ml_status": anomaly.get(
                "ml_status",
            ),
            "ml_severity": anomaly.get(
                "ml_severity",
            ),
            "ml_decision_score": anomaly.get(
                "ml_decision_score",
            ),
            "rule_events": anomaly.get(
                "rule_events",
                [],
            ),
        }

    def _build_event_payloads(
        self,
        timestamp: str,
        reading_id: Any,
        lifecycle: str,
        anomaly: dict[str, Any],
        alert_event_id: str,
    ) -> list[dict[str, Any]]:

        events: list[
            dict[str, Any]
        ] = []

        events.append(
            {
                "event_id": self._new_id(
                    "event"
                ),
                "timestamp": timestamp,
                "reading_id": reading_id,
                "event_type": (
                    f"ALERT_{lifecycle}"
                ),
                "severity": anomaly.get(
                    "highest_severity",
                    "MEDIUM",
                ),
                "source": "AlertManager",
                "message": anomaly.get(
                    "summary",
                    "Energy anomaly alert.",
                ),
                "parent_alert_event_id": alert_event_id,
            }
        )

        # Detailed anomaly events are stored only on OPEN/UPDATE.
        # REMINDER stays compact and avoids duplicate history.
        if lifecycle not in {
            "OPEN",
            "UPDATE",
        }:
            return events

        for rule_event in anomaly.get(
            "rule_events",
            [],
        ):
            events.append(
                {
                    "event_id": self._new_id(
                        "event"
                    ),
                    "timestamp": timestamp,
                    "reading_id": reading_id,
                    "event_type": rule_event.get(
                        "anomaly_type",
                        "RULE_ANOMALY",
                    ),
                    "severity": rule_event.get(
                        "severity",
                        anomaly.get(
                            "highest_severity",
                            "MEDIUM",
                        ),
                    ),
                    "source": "RuleAnomalyAgent",
                    "message": rule_event.get(
                        "message",
                        "Rule-based anomaly detected.",
                    ),
                    "recommendation": rule_event.get(
                        "recommendation",
                    ),
                    "observed_value": rule_event.get(
                        "observed_value",
                    ),
                    "threshold": rule_event.get(
                        "threshold",
                    ),
                    "parent_alert_event_id": alert_event_id,
                }
            )

        if anomaly.get(
            "ml_status"
        ) == "ANOMALOUS":
            events.append(
                {
                    "event_id": self._new_id(
                        "event"
                    ),
                    "timestamp": timestamp,
                    "reading_id": reading_id,
                    "event_type": "ML_ANOMALY",
                    "severity": anomaly.get(
                        "ml_severity",
                        "MEDIUM",
                    ),
                    "source": "MLAnomalyAgent",
                    "message": (
                        "Isolation Forest detected an unusual "
                        "multivariate operating pattern."
                    ),
                    "ml_decision_score": anomaly.get(
                        "ml_decision_score",
                    ),
                    "parent_alert_event_id": alert_event_id,
                }
            )

        return events

    # ==========================================================
    # Fingerprinting / restart recovery
    # ==========================================================

    def _fingerprint(
        self,
        anomaly: dict[str, Any],
    ) -> str:

        rule_types = sorted(
            str(
                event.get(
                    "anomaly_type",
                    "UNKNOWN_RULE_ANOMALY",
                )
            )
            for event in anomaly.get(
                "rule_events",
                [],
            )
        )

        fingerprint_source = {
            "severity": anomaly.get(
                "highest_severity",
                "NONE",
            ),
            "rule_types": rule_types,
            "ml_status": anomaly.get(
                "ml_status",
                "NORMAL",
            ),
            "ml_severity": anomaly.get(
                "ml_severity",
                "NONE",
            ),
        }

        serialized = json.dumps(
            fingerprint_source,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            serialized.encode(
                "utf-8"
            )
        ).hexdigest()[:20]

    def _restore_state(
        self,
    ) -> None:

        latest = (
            self.event_store.latest_alert_state()
        )

        if latest is None:
            return

        if latest.get(
            "lifecycle"
        ) == "RESOLVED":
            return

        self._active_fingerprint = (
            latest.get(
                "fingerprint"
            )
        )

        self._active_severity = (
            latest.get(
                "severity",
                "NONE",
            )
        )

        self._last_published_at = (
            self._parse_timestamp(
                str(
                    latest.get(
                        "timestamp"
                    )
                )
            )
        )

    # ==========================================================
    # Utilities
    # ==========================================================

    @staticmethod
    def _new_id(
        prefix: str,
    ) -> str:

        return (
            f"{prefix}_"
            f"{uuid.uuid4().hex}"
        )

    @staticmethod
    def _parse_timestamp(
        value: str,
    ) -> datetime:

        try:
            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError:
            parsed = datetime.now(
                timezone.utc
            )

        # Normalize naive simulator timestamps to a common comparable
        # representation without changing their displayed value.
        if parsed.tzinfo is None:
            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed
