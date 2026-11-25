from __future__ import annotations

import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from api.live_state import (
    api_live_state,
)
from api.mqtt_bridge import (
    mqtt_api_bridge,
)
from api.websocket_manager import (
    websocket_manager,
)
from config.observability_config import (
    LOG_DIR,
    LOG_FILE_NAME,
    MQTT_STALE_AFTER_SECONDS,
    TELEMETRY_STALE_AFTER_SECONDS,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]


def _age_seconds(
    iso_value: str | None,
) -> float | None:

    if not iso_value:
        return None

    try:
        timestamp = datetime.fromisoformat(
            iso_value.replace(
                "Z",
                "+00:00",
            )
        )

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(
                tzinfo=timezone.utc
            )

        return max(
            0.0,
            (
                datetime.now(
                    timezone.utc
                )
                - timestamp
            ).total_seconds(),
        )

    except ValueError:
        return None


def health_snapshot() -> dict[str, Any]:

    snapshot = (
        api_live_state.snapshot()
    )

    telemetry_updated = (
        snapshot["updated_at"].get(
            "telemetry"
        )
    )

    telemetry_age = (
        _age_seconds(
            telemetry_updated
        )
    )

    mqtt_age = (
        _age_seconds(
            mqtt_api_bridge.last_message_at
        )
    )

    telemetry_fresh = (
        telemetry_age is not None
        and telemetry_age
        <= TELEMETRY_STALE_AFTER_SECONDS
    )

    mqtt_recent = (
        mqtt_age is not None
        and mqtt_age
        <= MQTT_STALE_AFTER_SECONDS
    )

    if (
        mqtt_api_bridge.connected
        and telemetry_fresh
    ):
        overall = "healthy"

    elif mqtt_api_bridge.connected:
        overall = "degraded"

    else:
        overall = "unhealthy"

    process = psutil.Process()

    return {
        "status": overall,
        "checks": {
            "api": {
                "ok": True,
            },
            "mqtt": {
                "ok": (
                    mqtt_api_bridge.connected
                ),
                "connected": (
                    mqtt_api_bridge.connected
                ),
                "recent_message": mqtt_recent,
                "last_message_at": (
                    mqtt_api_bridge.last_message_at
                ),
                "last_error": (
                    mqtt_api_bridge.last_error
                ),
            },
            "telemetry": {
                "ok": telemetry_fresh,
                "last_update": (
                    telemetry_updated
                ),
                "age_seconds": (
                    round(
                        telemetry_age,
                        2,
                    )
                    if telemetry_age
                    is not None
                    else None
                ),
            },
            "websocket": {
                "clients": (
                    websocket_manager.client_count
                ),
            },
        },
        "process": {
            "pid": process.pid,
            "cpu_percent": (
                process.cpu_percent(
                    interval=None
                )
            ),
            "memory_mb": round(
                process.memory_info().rss
                / 1024
                / 1024,
                2,
            ),
            "threads": (
                process.num_threads()
            ),
        },
    }


def system_snapshot() -> dict[str, Any]:

    disk = psutil.disk_usage(
        str(
            PROJECT_ROOT.drive
            or PROJECT_ROOT
        )
    )

    memory = psutil.virtual_memory()

    return {
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "cpu": {
            "system_percent": (
                psutil.cpu_percent(
                    interval=None
                )
            ),
            "logical_cores": (
                psutil.cpu_count(
                    logical=True
                )
            ),
        },
        "memory": {
            "total_gb": round(
                memory.total
                / 1024**3,
                2,
            ),
            "used_gb": round(
                memory.used
                / 1024**3,
                2,
            ),
            "percent": (
                memory.percent
            ),
        },
        "disk": {
            "total_gb": round(
                disk.total
                / 1024**3,
                2,
            ),
            "used_gb": round(
                disk.used
                / 1024**3,
                2,
            ),
            "free_gb": round(
                disk.free
                / 1024**3,
                2,
            ),
            "percent": (
                disk.percent
            ),
        },
        "logs": {
            "directory": str(
                LOG_DIR
            ),
            "active_log_file": str(
                LOG_DIR
                / LOG_FILE_NAME
            ),
        },
    }


def model_snapshot() -> dict[str, Any]:

    decision = (
        api_live_state.get(
            "decision"
        )
        or {}
    )

    forecast = decision.get(
        "forecast",
        {},
    )

    anomaly = decision.get(
        "anomaly",
        {},
    )

    optimization = decision.get(
        "optimization",
        {},
    )

    operator = (
        api_live_state.get(
            "operator_summary"
        )
        or decision.get(
            "operator_summary",
            {},
        )
        or {}
    )

    return {
        "forecasting": {
            "predicted_demand_kw": (
                forecast.get(
                    "predicted_demand_kw"
                )
            ),
            "horizon_minutes": (
                forecast.get(
                    "forecast_horizon_minutes"
                )
            ),
            "trend": (
                forecast.get(
                    "trend"
                )
            ),
            "mae_kw": (
                forecast.get(
                    "model_mae_kw"
                )
            ),
            "rmse_kw": (
                forecast.get(
                    "model_rmse_kw"
                )
            ),
            "r2": (
                forecast.get(
                    "model_r2"
                )
            ),
        },
        "anomaly_detection": {
            "overall_status": (
                anomaly.get(
                    "overall_status"
                )
            ),
            "severity": (
                anomaly.get(
                    "highest_severity"
                )
            ),
            "combined_alert_count": (
                anomaly.get(
                    "combined_alert_count"
                )
            ),
            "ml_status": (
                anomaly.get(
                    "ml_status"
                )
            ),
            "ml_severity": (
                anomaly.get(
                    "ml_severity"
                )
            ),
            "ml_decision_score": (
                anomaly.get(
                    "ml_decision_score"
                )
            ),
        },
        "optimizer": {
            "control_mode": (
                optimization.get(
                    "control_mode"
                )
            ),
            "objective_score": (
                optimization.get(
                    "objective_score"
                )
            ),
            "estimated_cost_inr_per_hour": (
                optimization.get(
                    "estimated_cost_inr_per_hour"
                )
            ),
            "estimated_carbon_kg_per_hour": (
                optimization.get(
                    "estimated_carbon_kg_per_hour"
                )
            ),
            "projected_soc_percent": (
                optimization.get(
                    "projected_soc_percent"
                )
            ),
            "battery_constraint_active": (
                optimization.get(
                    "battery_constraint_active"
                )
            ),
        },
        "local_llm": {
            "source": (
                operator.get(
                    "source"
                )
            ),
            "model": (
                operator.get(
                    "model"
                )
            ),
            "latency_ms": (
                operator.get(
                    "latency_ms"
                )
            ),
            "fallback_used": (
                operator.get(
                    "fallback_used"
                )
            ),
            "trigger": (
                operator.get(
                    "trigger"
                )
            ),
        },
    }
