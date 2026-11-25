from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from llm.operator_assistant import OperatorAssistant


class FakeProvider:
    model = "fake-local-model"

    def __init__(
        self,
        valid: bool = True,
    ) -> None:
        self.valid = valid
        self.calls = 0

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> SimpleNamespace:

        self.calls += 1

        if not self.valid:
            return SimpleNamespace(
                content=(
                    "this is not valid json"
                ),
                model=self.model,
            )

        payload = {
            "headline": (
                "System operating normally"
            ),
            "situation": (
                "Demand is stable and battery "
                "reserve is healthy."
            ),
            "why": (
                "The deterministic controller "
                "selected HOLD because current "
                "conditions are within limits."
            ),
            "operator_actions": [
                "Continue monitoring."
            ],
            "risks": [],
            "confidence_note": (
                "Summary is based only on supplied "
                "telemetry and agent outputs."
            ),
        }

        return SimpleNamespace(
            content=json.dumps(
                payload
            ),
            model=self.model,
        )


def telemetry() -> dict:
    return {
        "timestamp": (
            "2026-09-11T10:00:00"
        ),
        "reading_id": 1,
        "demand_kw": 35.0,
        "solar_generation_kw": 10.0,
        "battery_soc_percent": 70.0,
        "grid_price_inr_per_kwh": 5.0,
        "grid_carbon_intensity_g_per_kwh": 500.0,
        "temperature_c": 28.0,
        "humidity_percent": 55.0,
        "occupancy_percent": 50.0,
        "net_grid_demand_kw": 25.0,
    }


def analysis(
    action: str = (
        "MAINTAIN_CURRENT_OPERATION"
    ),
) -> dict:
    return {
        "agents": {
            "load": {
                "status": "NORMAL"
            },
            "battery": {
                "status": "HEALTHY"
            },
            "pricing": {
                "status": "NORMAL"
            },
            "solar": {
                "status": "MODERATE"
            },
            "grid": {
                "dependency": (
                    "MODERATE_DEPENDENCY"
                )
            },
            "forecast": {
                "current_demand_kw": 35.0,
                "predicted_demand_kw": 36.0,
                "demand_change_kw": 1.0,
                "forecast_horizon_minutes": 15,
                "trend": "STABLE",
            },
        },
        "decision": {
            "action": action,
            "priority": "LOW",
            "reason": (
                "Conditions are within limits."
            ),
            "confidence": 0.82,
        },
        "optimization": {
            "recommended_battery_power_kw": 0.0,
            "recommended_grid_import_kw": 25.0,
            "recommended_load_reduction_kw": 0.0,
            "control_mode": "HOLD",
            "projected_soc_percent": 70.0,
            "battery_constraint_active": False,
        },
        "anomaly": {
            "overall_status": "NORMAL",
            "highest_severity": "NONE",
            "combined_alert_count": 0,
            "ml_status": "NORMAL",
            "ml_severity": "NONE",
            "rule_events": [],
            "summary": (
                "No operational or ML-based "
                "anomalies detected."
            ),
        },
    }


print("\n1) Valid local LLM response")
provider = FakeProvider(
    valid=True
)
assistant = OperatorAssistant(
    provider=provider,
    enabled=True,
    summary_interval_seconds=999,
)

first = assistant.summarize(
    telemetry(),
    analysis(),
)

assert first.source == "local_llm"
assert not first.fallback_used
assert first.fresh
assert provider.calls == 1
print("   PASS")


print("\n2) Repeated telemetry uses cache")
second = assistant.summarize(
    telemetry(),
    analysis(),
)

assert not second.fresh
assert second.trigger == "CACHE"
assert provider.calls == 1
print("   PASS")


print("\n3) Decision change triggers fresh summary")
changed = assistant.summarize(
    telemetry(),
    analysis(
        "DISCHARGE_BATTERY"
    ),
)

assert changed.fresh
assert (
    changed.trigger
    == "DECISION_CHANGE"
)
assert provider.calls == 2
print("   PASS")


print("\n4) Alert lifecycle triggers fresh summary")
alert = {
    "lifecycle": "OPEN",
    "severity": "HIGH",
}

alerted = assistant.summarize(
    telemetry(),
    analysis(),
    alert_payload=alert,
)

assert alerted.fresh
assert alerted.trigger == "ALERT_OPEN"
assert provider.calls == 3
print("   PASS")


print("\n5) Invalid/unavailable LLM cannot break control pipeline")
bad_provider = FakeProvider(
    valid=False
)

fallback_assistant = OperatorAssistant(
    provider=bad_provider,
    enabled=True,
)

fallback = fallback_assistant.summarize(
    telemetry(),
    analysis(),
)

assert fallback.fallback_used
assert (
    fallback.source
    == "deterministic_fallback"
)
assert len(
    fallback.headline
) > 0
print("   PASS")


print("\n6) Operator schema exposes no actuator override fields")
for forbidden in (
    "battery_power_kw",
    "grid_import_kw",
    "load_reduction_kw",
    "action",
    "control_mode",
):
    assert forbidden not in (
        first.to_dict()
    )

print("   PASS")

print(
    "\n✅ STEP 4 LOCAL LLM LAYER TESTS PASSED"
)
