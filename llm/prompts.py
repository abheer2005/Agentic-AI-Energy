from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """
You are the local operator-assistance LLM inside an Agentic AI energy
management platform.

ROLE:
- Synthesize outputs from deterministic/ML energy agents.
- Explain what is happening in concise operator language.
- Highlight operational risk and sensible human follow-up.
- Never override, replace, or fabricate the deterministic control decision.

HARD SAFETY / ARCHITECTURE RULES:
1. Numerical control decisions are already made by deterministic agents and
   the optimization controller.
2. You MUST NOT invent a new battery power, grid import target, SOC target,
   load-shedding percentage, or actuator command.
3. You MUST NOT claim that you executed any action.
4. Only use facts present in the supplied context.
5. Distinguish measured telemetry from forecasted values.
6. If an anomaly is absent, do not manufacture a warning.
7. If the supplied information is uncertain, say so briefly.
8. Keep operator_actions advisory and human-readable.
9. Return ONLY valid JSON. No markdown and no code fences.

Required JSON shape:
{
  "headline": "short status headline",
  "situation": "what is happening now",
  "why": "why the deterministic agents/controller chose this response",
  "operator_actions": ["0 to 3 concise advisory actions"],
  "risks": ["0 to 3 concise risks actually supported by context"],
  "confidence_note": "brief statement about evidence/model confidence"
}
""".strip()


def build_operator_prompt(
    telemetry: dict[str, Any],
    analysis: dict[str, Any],
    alert_context: dict[str, Any] | None,
) -> str:

    agents = analysis.get(
        "agents",
        {},
    )

    context = {
        "measured_telemetry": {
            "timestamp": telemetry.get(
                "timestamp"
            ),
            "reading_id": telemetry.get(
                "reading_id"
            ),
            "demand_kw": telemetry.get(
                "demand_kw"
            ),
            "solar_generation_kw": telemetry.get(
                "solar_generation_kw"
            ),
            "battery_soc_percent": telemetry.get(
                "battery_soc_percent"
            ),
            "grid_price_inr_per_kwh": telemetry.get(
                "grid_price_inr_per_kwh"
            ),
            "grid_carbon_intensity_g_per_kwh": telemetry.get(
                "grid_carbon_intensity_g_per_kwh"
            ),
            "temperature_c": telemetry.get(
                "temperature_c"
            ),
            "humidity_percent": telemetry.get(
                "humidity_percent"
            ),
            "occupancy_percent": telemetry.get(
                "occupancy_percent"
            ),
            "net_grid_demand_kw": telemetry.get(
                "net_grid_demand_kw"
            ),
        },
        "specialist_agent_outputs": {
            "load": agents.get(
                "load"
            ),
            "battery": agents.get(
                "battery"
            ),
            "pricing": agents.get(
                "pricing"
            ),
            "solar": agents.get(
                "solar"
            ),
            "grid": agents.get(
                "grid"
            ),
        },
        "demand_forecast": agents.get(
            "forecast"
        ),
        "supervisor_decision": analysis.get(
            "decision"
        ),
        "deterministic_optimization": analysis.get(
            "optimization"
        ),
        "unified_anomaly": analysis.get(
            "anomaly"
        ),
        "alert_lifecycle_event": alert_context,
    }

    return (
        "Create the operator summary from this exact system context:\n"
        + json.dumps(
            context,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
