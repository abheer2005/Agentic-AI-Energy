from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class PricingAnalysis:
    status: str
    current_price: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PricingAgent:
    """
    Analyses electricity price and identifies
    whether grid usage is economically favorable.
    """

    def analyze(
        self,
        telemetry: dict[str, Any]
    ) -> PricingAnalysis:

        price = float(
            telemetry.get(
                "grid_price_inr_per_kwh",
                0.0
            )
        )

        if price < 4.5:
            status = "CHEAP"
            recommendation = (
                "Grid electricity is inexpensive. "
                "This is a favorable time for charging."
            )

        elif price < 6.0:
            status = "NORMAL"
            recommendation = (
                "Electricity price is within normal range."
            )

        elif price < 8.0:
            status = "EXPENSIVE"
            recommendation = (
                "Reduce grid consumption where possible."
            )

        else:
            status = "VERY_EXPENSIVE"
            recommendation = (
                "Minimize grid import and prioritize "
                "battery or renewable energy."
            )

        return PricingAnalysis(
            status=status,
            current_price=round(
                price,
                2
            ),
            recommendation=recommendation,
        )