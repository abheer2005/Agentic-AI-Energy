from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class BatteryAnalysis:
    status: str
    soc_percent: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BatteryAgent:
    """
    Analyses battery state of charge and recommends
    charging / holding / discharging strategy.
    """

    def analyze(
        self,
        telemetry: dict[str, Any]
    ) -> BatteryAnalysis:

        soc = float(
            telemetry.get(
                "battery_soc_percent",
                0.0
            )
        )

        if soc < 20:
            status = "CRITICAL_LOW"
            recommendation = (
                "Prioritize battery charging and avoid discharge."
            )

        elif soc < 40:
            status = "LOW"
            recommendation = (
                "Charge battery when electricity price "
                "or grid demand is favorable."
            )

        elif soc <= 80:
            status = "HEALTHY"
            recommendation = (
                "Battery level is healthy. "
                "Hold energy for future high-demand periods."
            )

        elif soc <= 95:
            status = "HIGH"
            recommendation = (
                "Battery has sufficient stored energy and "
                "can support the grid during expensive periods."
            )

        else:
            status = "NEAR_FULL"
            recommendation = (
                "Battery is almost full. Prefer discharge "
                "or reduce further charging."
            )

        return BatteryAnalysis(
            status=status,
            soc_percent=round(soc, 2),
            recommendation=recommendation,
        )