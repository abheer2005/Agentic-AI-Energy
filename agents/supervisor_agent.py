from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class SupervisorDecision:
    action: str
    priority: str
    reason: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SupervisorAgent:
    """
    Combines outputs from multiple specialist agents
    and selects the best current energy-management action.
    """

    def decide(
        self,
        load_result,
        battery_result,
        pricing_result,
        solar_result,
        grid_result,
        forecast_result,
    ):

        # ==========================================================
        # 1. CURRENT CRITICAL LOAD
        # Highest priority: current emergency overrides forecast.
        # ==========================================================

        if load_result.status == "CRITICAL":

            if battery_result.status in {
                "HEALTHY",
                "HIGH",
                "NEAR_FULL",
            }:
                return SupervisorDecision(
                    action="DISCHARGE_BATTERY",
                    priority="CRITICAL",
                    reason=(
                        "Building load is critical and "
                        "battery energy is available."
                    ),
                    confidence=0.95,
                )

            return SupervisorDecision(
                action="SHED_NON_CRITICAL_LOAD",
                priority="CRITICAL",
                reason=(
                    "Building load is critical and battery "
                    "support is insufficient."
                ),
                confidence=0.94,
            )

        # ==========================================================
        # 2. STRONG SOLAR AVAILABILITY
        # Use available renewable energy before preparing
        # aggressive future actions.
        # ==========================================================

        if solar_result.status in {
            "HIGH",
            "EXCELLENT",
        }:

            # Strong solar + low battery:
            # use renewable surplus to recover battery reserves.
            if battery_result.status in {
                "LOW",
                "CRITICAL_LOW",
            }:
                return SupervisorDecision(
                    action="CHARGE_BATTERY_FROM_SOLAR",
                    priority="HIGH",
                    reason=(
                        "Strong solar generation is available "
                        "while battery reserves are low."
                    ),
                    confidence=0.93,
                )

            # Expensive grid + strong solar:
            # minimize costly grid import.
            if pricing_result.status in {
                "EXPENSIVE",
                "VERY_EXPENSIVE",
            }:
                return SupervisorDecision(
                    action="PRIORITIZE_SOLAR",
                    priority="HIGH",
                    reason=(
                        "Grid electricity is expensive while "
                        "strong solar generation is available."
                    ),
                    confidence=0.92,
                )

            # Normal case with strong solar.
            return SupervisorDecision(
                action="USE_SOLAR_FOR_LOAD",
                priority="MEDIUM",
                reason=(
                    "Strong renewable generation is available "
                    "and can reduce grid dependency."
                ),
                confidence=0.88,
            )

        # ==========================================================
        # 3. RAPIDLY RISING DEMAND FORECAST
        # Forecast-aware preparation before the load becomes critical.
        # ==========================================================

        if (
            forecast_result.trend == "RISING_FAST"
            and battery_result.status in {
                "HEALTHY",
                "HIGH",
                "NEAR_FULL",
            }
        ):
            return SupervisorDecision(
                action="PREPARE_BATTERY_SUPPORT",
                priority="HIGH",
                reason=(
                    "Demand is forecast to rise rapidly and "
                    "sufficient battery energy is available."
                ),
                confidence=0.93,
            )

        if (
            forecast_result.trend == "RISING_FAST"
            and battery_result.status in {
                "LOW",
                "CRITICAL_LOW",
            }
            and solar_result.status not in {
                "HIGH",
                "EXCELLENT",
            }
        ):
            return SupervisorDecision(
                action="PREPARE_LOAD_REDUCTION",
                priority="HIGH",
                reason=(
                    "Demand is forecast to rise rapidly while "
                    "battery reserves are limited and strong "
                    "solar support is unavailable."
                ),
                confidence=0.91,
            )

        # ==========================================================
        # 4. EXPENSIVE GRID ELECTRICITY
        # ==========================================================

        if pricing_result.status in {
            "EXPENSIVE",
            "VERY_EXPENSIVE",
        }:

            if battery_result.status in {
                "HEALTHY",
                "HIGH",
                "NEAR_FULL",
            }:
                return SupervisorDecision(
                    action="DISCHARGE_BATTERY",
                    priority="HIGH",
                    reason=(
                        "Grid electricity is expensive and "
                        "stored battery energy is available."
                    ),
                    confidence=0.90,
                )

        # ==========================================================
        # 5. CHEAP GRID + LOW BATTERY
        # Good opportunity to restore battery reserves.
        # ==========================================================

        if (
            pricing_result.status == "CHEAP"
            and battery_result.status in {
                "LOW",
                "CRITICAL_LOW",
            }
        ):
            return SupervisorDecision(
                action="CHARGE_BATTERY_FROM_GRID",
                priority="MEDIUM",
                reason=(
                    "Grid electricity is inexpensive and "
                    "battery charge is low."
                ),
                confidence=0.87,
            )

        # ==========================================================
        # 6. FALLING DEMAND FORECAST
        # Preserve battery when demand is expected to fall,
        # unless a better charging opportunity already matched above.
        # ==========================================================

        if (
            forecast_result.trend in {
                "FALLING",
                "FALLING_FAST",
            }
            and battery_result.status in {
                "LOW",
                "CRITICAL_LOW",
            }
        ):
            return SupervisorDecision(
                action="PRESERVE_BATTERY",
                priority="MEDIUM",
                reason=(
                    "Demand is forecast to decrease, so battery "
                    "energy should be preserved."
                ),
                confidence=0.88,
            )

        # ==========================================================
        # 7. HIGH-CARBON GRID
        # ==========================================================

        if (
            grid_result.carbon_intensity > 600
            and battery_result.status in {
                "HEALTHY",
                "HIGH",
                "NEAR_FULL",
            }
        ):
            return SupervisorDecision(
                action="REDUCE_GRID_IMPORT",
                priority="MEDIUM",
                reason=(
                    "Grid carbon intensity is high and "
                    "battery support is available."
                ),
                confidence=0.85,
            )

        # ==========================================================
        # 8. DEFAULT STABLE OPERATION
        # ==========================================================

        return SupervisorDecision(
            action="MAINTAIN_CURRENT_OPERATION",
            priority="LOW",
            reason=(
                "Energy conditions are within acceptable "
                "operating limits."
            ),
            confidence=0.82,
        )