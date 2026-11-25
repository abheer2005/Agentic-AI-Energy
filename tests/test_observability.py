from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from fastapi.testclient import (
    TestClient,
)

from api.live_state import (
    api_live_state,
)
from api.main import app


client = TestClient(
    app
)


print("\n1) Detailed health endpoint")
response = client.get(
    "/api/v1/health/detailed"
)
assert response.status_code == 200
assert "status" in (
    response.json()["data"]
)
print("   PASS")


print("\n2) System metrics endpoint")
response = client.get(
    "/api/v1/system"
)
assert response.status_code == 200

system = response.json()[
    "data"
]

assert "cpu" in system
assert "memory" in system
assert "disk" in system
print("   PASS")


print("\n3) Model observability endpoint")
api_live_state.update(
    "decision",
    {
        "forecast": {
            "predicted_demand_kw": 45.5,
            "forecast_horizon_minutes": 15,
            "trend": "RISING",
            "model_mae_kw": 1.8,
            "model_rmse_kw": 2.2,
            "model_r2": 0.98,
        },
        "anomaly": {
            "overall_status": "NORMAL",
            "highest_severity": "NONE",
            "combined_alert_count": 0,
            "ml_status": "NORMAL",
            "ml_severity": "NONE",
            "ml_decision_score": 0.08,
        },
        "optimization": {
            "control_mode": "HOLD",
            "objective_score": 0.22,
            "estimated_cost_inr_per_hour": 150.0,
            "estimated_carbon_kg_per_hour": 12.0,
            "projected_soc_percent": 68.0,
            "battery_constraint_active": False,
        },
        "operator_summary": {
            "source": "local_llm",
            "model": "qwen2.5:3b",
            "latency_ms": 450.0,
            "fallback_used": False,
            "trigger": "PERIODIC",
        },
    },
)

response = client.get(
    "/api/v1/models"
)

assert response.status_code == 200

models = response.json()[
    "data"
]

assert (
    models["forecasting"]["r2"]
    == 0.98
)

assert (
    models["local_llm"]["model"]
    == "qwen2.5:3b"
)

print("   PASS")


print("\n4) Prometheus metrics endpoint")
response = client.get(
    "/api/v1/metrics"
)

assert response.status_code == 200
assert (
    "p308_api_requests_total"
    in response.text
)
print("   PASS")


print("\n5) Rotating log file configuration")
log_file = (
    PROJECT_ROOT
    / "logs"
    / "agentic_energy_ai.log"
)

assert (
    log_file.parent.exists()
)
print("   PASS")


print(
    "\n✅ STEP 7 OBSERVABILITY TESTS PASSED"
)
