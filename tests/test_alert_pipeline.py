from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from core.alert_manager import AlertManager
from core.event_store import SQLiteEventStore


def make_analysis(
    *,
    overall_status: str = "NORMAL",
    highest_severity: str = "NONE",
    rule_events: list[dict] | None = None,
    ml_status: str = "NORMAL",
    ml_severity: str = "NONE",
    ml_decision_score: float = 0.10,
) -> dict:
    rule_events = rule_events or []

    return {
        "overall_status": overall_status,
        "highest_severity": highest_severity,
        "rule_anomaly_count": len(rule_events),
        "ml_status": ml_status,
        "ml_severity": ml_severity,
        "ml_decision_score": ml_decision_score,
        "combined_alert_count": (
            len(rule_events)
            + (1 if ml_status == "ANOMALOUS" else 0)
        ),
        "rule_events": rule_events,
        "summary": (
            "No operational or ML-based anomalies detected."
            if overall_status == "NORMAL"
            else "Critical abnormal system behavior detected."
        ),
    }


def critical_event(
    anomaly_type: str = "CRITICAL_DEMAND",
) -> dict:
    return {
        "anomaly_type": anomaly_type,
        "severity": "CRITICAL",
        "message": f"{anomaly_type} detected.",
        "observed_value": 100.0,
        "threshold": 90.0,
        "recommendation": "Immediate operational review.",
    }


def make_telemetry(
    base: datetime,
    seconds: int,
    reading_id: int,
) -> dict:
    """
    Minimal telemetry shape needed by AlertManager.process().
    """
    return {
        "timestamp": (
            base + timedelta(seconds=seconds)
        ).isoformat(),
        "reading_id": reading_id,
        "demand_kw": 50.0,
        "solar_generation_kw": 10.0,
        "battery_soc_percent": 70.0,
        "grid_price_inr_per_kwh": 7.0,
        "grid_carbon_intensity_g_per_kwh": 500.0,
        "temperature_c": 30.0,
        "humidity_percent": 60.0,
        "occupancy_percent": 70.0,
        "cloud_cover_percent": 30.0,
        "net_grid_demand_kw": 40.0,
    }


# Windows may retain a SQLite file handle briefly after all assertions.
# ignore_cleanup_errors prevents a successful logic test from failing
# only because TemporaryDirectory cleanup races with Windows file locking.
with tempfile.TemporaryDirectory(
    ignore_cleanup_errors=True
) as temp_dir:

    db_path = Path(temp_dir) / "test_energy_events.db"

    store = SQLiteEventStore(
        db_path
    )

    manager = AlertManager(
        event_store=store,
        reminder_seconds=60,
    )

    base = datetime.now(
        timezone.utc
    )

    normal = make_analysis()

    critical = make_analysis(
        overall_status="CRITICAL",
        highest_severity="CRITICAL",
        rule_events=[
            critical_event(
                "CRITICAL_DEMAND"
            )
        ],
        ml_status="ANOMALOUS",
        ml_severity="CRITICAL",
        ml_decision_score=-0.14,
    )

    changed = make_analysis(
        overall_status="CRITICAL",
        highest_severity="CRITICAL",
        rule_events=[
            critical_event(
                "CRITICAL_DEMAND"
            ),
            critical_event(
                "CRITICAL_BATTERY"
            ),
        ],
        ml_status="ANOMALOUS",
        ml_severity="CRITICAL",
        ml_decision_score=-0.16,
    )

    print("\n1) NORMAL → no alert")
    result = manager.process(
        telemetry=make_telemetry(
            base,
            0,
            1,
        ),
        anomaly=normal,
    )
    assert result.alert_payload is None
    assert result.suppressed is False
    print("   PASS")

    print("\n2) CRITICAL appears → OPEN")
    result = manager.process(
        telemetry=make_telemetry(
            base,
            1,
            2,
        ),
        anomaly=critical,
    )
    assert result.alert_payload is not None
    assert (
        result.alert_payload["lifecycle"]
        == "OPEN"
    )
    print("   PASS")

    print("\n3) Same critical state → suppressed")
    result = manager.process(
        telemetry=make_telemetry(
            base,
            10,
            3,
        ),
        anomaly=critical,
    )
    assert result.alert_payload is None
    assert result.suppressed is True
    print("   PASS")

    print("\n4) Same alert after cooldown → REMINDER")
    result = manager.process(
        telemetry=make_telemetry(
            base,
            70,
            4,
        ),
        anomaly=critical,
    )
    assert result.alert_payload is not None
    assert (
        result.alert_payload["lifecycle"]
        == "REMINDER"
    )
    print("   PASS")

    print("\n5) Anomaly pattern changes → UPDATE")
    result = manager.process(
        telemetry=make_telemetry(
            base,
            75,
            5,
        ),
        anomaly=changed,
    )
    assert result.alert_payload is not None
    assert (
        result.alert_payload["lifecycle"]
        == "UPDATE"
    )
    print("   PASS")

    print("\n6) System normalizes → RESOLVED")
    result = manager.process(
        telemetry=make_telemetry(
            base,
            80,
            6,
        ),
        anomaly=normal,
    )
    assert result.alert_payload is not None
    assert (
        result.alert_payload["lifecycle"]
        == "RESOLVED"
    )
    print("   PASS")

    print("\n7) SQLite audit history")
    counts = store.counts()

    assert counts["alerts"] == 4
    assert counts["events"] >= 7

    print(
        f"   Alerts stored: "
        f"{counts['alerts']}"
    )
    print(
        f"   Events stored: "
        f"{counts['events']}"
    )
    print("   PASS")

    print(
        "\n✅ STEP 3 ALERT/EVENT PIPELINE TESTS PASSED"
    )
