from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from fastapi.testclient import TestClient

from api.live_state import api_live_state
from api.main import app


client = TestClient(app)


print("\n1) Root redirects to dashboard")
response = client.get(
    "/",
    follow_redirects=False,
)

assert response.status_code in {
    302,
    307,
    308,
}
assert response.headers["location"] == "/dashboard/"
print("   PASS")


print("\n2) API info endpoint")
response = client.get(
    "/api-info"
)

assert response.status_code == 200

payload = response.json()

assert payload["status"] == "running"
assert payload["dashboard"] == "/dashboard/"
assert payload["health"] == "/api/v1/health"
assert payload["websocket"] == "/ws/live"
print("   PASS")


print("\n3) Health endpoint")
response = client.get(
    "/api/v1/health"
)

assert response.status_code == 200

health = response.json()

assert "status" in health
assert "mqtt_connected" in health
assert "websocket_clients" in health
print("   PASS")


print("\n4) Missing live telemetry is handled safely")
response = client.get(
    "/api/v1/telemetry/latest"
)

assert response.status_code in {
    200,
    503,
}
print("   PASS")


print("\n5) Seed live state and validate consolidated live endpoint")
api_live_state.update(
    "telemetry",
    {
        "timestamp": "2026-09-11T05:00:00+00:00",
        "reading_id": 1001,
        "demand_kw": 52.4,
        "solar_generation_kw": 18.7,
        "battery_soc_percent": 71.5,
        "grid_price_inr_per_kwh": 7.2,
        "grid_carbon_intensity_g_per_kwh": 540.0,
        "temperature_c": 30.0,
        "humidity_percent": 60.0,
        "occupancy_percent": 72.0,
        "cloud_cover_percent": 35.0,
        "net_grid_demand_kw": 33.7,
    },
)

api_live_state.update(
    "decision",
    {
        "decision": {
            "action": "MAINTAIN_CURRENT_OPERATION",
            "priority": "NORMAL",
            "reason": "System operating within normal bounds.",
        },
        "forecast": {
            "current_demand_kw": 52.4,
            "predicted_demand_kw": 54.0,
            "demand_change_kw": 1.6,
            "forecast_horizon_minutes": 15,
            "trend": "STABLE",
            "model_mae_kw": 1.796,
            "model_rmse_kw": 2.269,
            "model_r2": 0.984,
        },
        "optimization": {
            "recommended_battery_power_kw": 0.0,
            "recommended_grid_import_kw": 33.7,
            "estimated_grid_reduction_kw": 0.0,
            "recommended_load_reduction_kw": 0.0,
            "projected_soc_percent": 71.5,
            "estimated_cost_inr_per_hour": 242.64,
            "estimated_carbon_kg_per_hour": 18.198,
            "objective_score": 0.2,
            "control_mode": "HOLD",
            "battery_constraint_active": False,
            "explanation": "Hold current operation.",
        },
        "anomaly": {
            "overall_status": "NORMAL",
            "highest_severity": "NONE",
            "rule_anomaly_count": 0,
            "ml_status": "NORMAL",
            "ml_severity": "NONE",
            "ml_decision_score": 0.09,
            "combined_alert_count": 0,
            "rule_events": [],
            "summary": "No anomalies detected.",
        },
        "operator_summary": {
            "headline": "System operating normally",
            "situation": "Energy conditions are stable.",
            "why": "No critical operational conditions are active.",
            "operator_actions": [],
            "risks": [],
            "confidence_note": "High confidence.",
            "source": "deterministic_fallback",
            "model": "qwen2.5:3b",
            "generated_at": "2026-09-11T05:00:00+00:00",
            "latency_ms": 0.0,
            "fresh": True,
            "trigger": "INITIAL",
            "fallback_used": True,
        },
    },
)

api_live_state.update(
    "control",
    {
        "timestamp": "2026-09-11T05:00:00+00:00",
        "reading_id": 1001,
        "action": "MAINTAIN_CURRENT_OPERATION",
        "control_mode": "HOLD",
        "battery_power_kw": 0.0,
        "recommended_grid_import_kw": 33.7,
    },
)

response = client.get(
    "/api/v1/live"
)

assert response.status_code == 200

live = response.json()["data"]

assert live["data"]["telemetry"]["reading_id"] == 1001
assert (
    live["data"]["decision"]["decision"]["action"]
    == "MAINTAIN_CURRENT_OPERATION"
)
assert (
    live["data"]["control"]["control_mode"]
    == "HOLD"
)

print("   PASS")


print("\n6) Latest telemetry endpoint")
response = client.get(
    "/api/v1/telemetry/latest"
)

assert response.status_code == 200
assert response.json()["data"]["reading_id"] == 1001
print("   PASS")


print("\n7) History endpoints")
response = client.get(
    "/api/v1/alerts?limit=5"
)
assert response.status_code == 200

response = client.get(
    "/api/v1/events?limit=5"
)
assert response.status_code == 200

response = client.get(
    "/api/v1/history/counts"
)
assert response.status_code == 200
print("   PASS")


print("\n8) WebSocket bootstrap + ping/pong")
with client.websocket_connect(
    "/ws/live"
) as websocket:

    message = websocket.receive_json()

    assert message["type"] == "snapshot"
    assert "payload" in message

    websocket.send_text("ping")

    pong = websocket.receive_json()

    assert pong["type"] == "pong"

print("   PASS")


print(
    "\n✅ STEP 5 FASTAPI BACKEND TESTS PASSED"
)
