from __future__ import annotations

from typing import Any

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
)


# ============================================================
# API / WEBSOCKET METRICS
# ============================================================

API_REQUESTS_TOTAL = Counter(
    "p308_api_requests_total",
    "Total HTTP requests received by the FastAPI backend.",
    ["method", "path", "status"],
)

API_REQUEST_LATENCY_SECONDS = Histogram(
    "p308_api_request_latency_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)

WEBSOCKET_CLIENTS = Gauge(
    "p308_websocket_clients",
    "Currently connected websocket clients.",
)


# ============================================================
# MQTT METRICS
# ============================================================

MQTT_MESSAGES_TOTAL = Counter(
    "p308_mqtt_messages_total",
    "MQTT messages received by API bridge.",
    ["channel"],
)

MQTT_PARSE_ERRORS_TOTAL = Counter(
    "p308_mqtt_parse_errors_total",
    "MQTT payload parse errors.",
    ["channel"],
)

MQTT_CONNECTED = Gauge(
    "p308_mqtt_connected",
    "MQTT bridge connection state: 1 connected, 0 disconnected.",
)


# ============================================================
# ENERGY SYSTEM METRICS
# ============================================================

ENERGY_DEMAND_KW = Gauge(
    "p308_energy_demand_kw",
    "Latest measured building demand in kW.",
)

SOLAR_GENERATION_KW = Gauge(
    "p308_solar_generation_kw",
    "Latest measured solar generation in kW.",
)

BATTERY_SOC_PERCENT = Gauge(
    "p308_battery_soc_percent",
    "Latest battery state of charge percentage.",
)

GRID_IMPORT_KW = Gauge(
    "p308_grid_import_kw",
    "Latest recommended grid import in kW.",
)

GRID_PRICE_INR_PER_KWH = Gauge(
    "p308_grid_price_inr_per_kwh",
    "Latest grid electricity price.",
)

GRID_CARBON_INTENSITY = Gauge(
    "p308_grid_carbon_intensity_g_per_kwh",
    "Latest grid carbon intensity.",
)

FORECAST_DEMAND_KW = Gauge(
    "p308_forecast_demand_kw",
    "Latest predicted demand.",
)

FORECAST_MODEL_MAE_KW = Gauge(
    "p308_forecast_model_mae_kw",
    "Demand forecasting model MAE.",
)

FORECAST_MODEL_RMSE_KW = Gauge(
    "p308_forecast_model_rmse_kw",
    "Demand forecasting model RMSE.",
)

FORECAST_MODEL_R2 = Gauge(
    "p308_forecast_model_r2",
    "Demand forecasting model R-squared score.",
)

ANOMALY_ALERT_COUNT = Gauge(
    "p308_anomaly_alert_count",
    "Number of currently active anomaly signals.",
)

ANOMALY_SEVERITY_RANK = Gauge(
    "p308_anomaly_severity_rank",
    "Current anomaly severity rank from 0 to 4.",
)

LLM_LATENCY_MS = Gauge(
    "p308_llm_latency_ms",
    "Latest local LLM operator-summary latency in milliseconds.",
)

LLM_FALLBACK_ACTIVE = Gauge(
    "p308_llm_fallback_active",
    "1 if latest operator summary used deterministic fallback.",
)

OPTIMIZER_OBJECTIVE_SCORE = Gauge(
    "p308_optimizer_objective_score",
    "Latest deterministic optimizer objective score.",
)

ESTIMATED_COST_INR_PER_HOUR = Gauge(
    "p308_estimated_cost_inr_per_hour",
    "Latest estimated grid energy cost rate.",
)

ESTIMATED_CARBON_KG_PER_HOUR = Gauge(
    "p308_estimated_carbon_kg_per_hour",
    "Latest estimated carbon emission rate.",
)


SEVERITY_MAP = {
    "NONE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


def _set_if_number(
    metric: Gauge,
    value: Any,
) -> None:
    try:
        metric.set(
            float(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        pass


def observe_mqtt_payload(
    channel: str,
    payload: Any,
    parse_error: bool = False,
) -> None:

    MQTT_MESSAGES_TOTAL.labels(
        channel=channel
    ).inc()

    if parse_error:
        MQTT_PARSE_ERRORS_TOTAL.labels(
            channel=channel
        ).inc()

    if not isinstance(
        payload,
        dict,
    ):
        return

    if channel == "telemetry":

        _set_if_number(
            ENERGY_DEMAND_KW,
            payload.get(
                "demand_kw"
            ),
        )

        _set_if_number(
            SOLAR_GENERATION_KW,
            payload.get(
                "solar_generation_kw"
            ),
        )

        _set_if_number(
            BATTERY_SOC_PERCENT,
            payload.get(
                "battery_soc_percent"
            ),
        )

        _set_if_number(
            GRID_PRICE_INR_PER_KWH,
            payload.get(
                "grid_price_inr_per_kwh"
            ),
        )

        _set_if_number(
            GRID_CARBON_INTENSITY,
            payload.get(
                "grid_carbon_intensity_g_per_kwh"
            ),
        )

    elif channel == "decision":

        optimization = payload.get(
            "optimization",
            {},
        )

        forecast = payload.get(
            "forecast",
            {},
        )

        anomaly = payload.get(
            "anomaly",
            {},
        )

        operator = payload.get(
            "operator_summary",
            {},
        )

        _set_if_number(
            GRID_IMPORT_KW,
            optimization.get(
                "recommended_grid_import_kw"
            ),
        )

        _set_if_number(
            OPTIMIZER_OBJECTIVE_SCORE,
            optimization.get(
                "objective_score"
            ),
        )

        _set_if_number(
            ESTIMATED_COST_INR_PER_HOUR,
            optimization.get(
                "estimated_cost_inr_per_hour"
            ),
        )

        _set_if_number(
            ESTIMATED_CARBON_KG_PER_HOUR,
            optimization.get(
                "estimated_carbon_kg_per_hour"
            ),
        )

        _set_if_number(
            FORECAST_DEMAND_KW,
            forecast.get(
                "predicted_demand_kw"
            ),
        )

        _set_if_number(
            FORECAST_MODEL_MAE_KW,
            forecast.get(
                "model_mae_kw"
            ),
        )

        _set_if_number(
            FORECAST_MODEL_RMSE_KW,
            forecast.get(
                "model_rmse_kw"
            ),
        )

        _set_if_number(
            FORECAST_MODEL_R2,
            forecast.get(
                "model_r2"
            ),
        )

        _set_if_number(
            ANOMALY_ALERT_COUNT,
            anomaly.get(
                "combined_alert_count"
            ),
        )

        severity = str(
            anomaly.get(
                "highest_severity",
                "NONE",
            )
        ).upper()

        ANOMALY_SEVERITY_RANK.set(
            SEVERITY_MAP.get(
                severity,
                0,
            )
        )

        _set_if_number(
            LLM_LATENCY_MS,
            operator.get(
                "latency_ms"
            ),
        )

        LLM_FALLBACK_ACTIVE.set(
            1
            if operator.get(
                "fallback_used"
            )
            else 0
        )

    elif channel == "operator_summary":

        _set_if_number(
            LLM_LATENCY_MS,
            payload.get(
                "latency_ms"
            ),
        )

        LLM_FALLBACK_ACTIVE.set(
            1
            if payload.get(
                "fallback_used"
            )
            else 0
        )
