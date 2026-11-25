from __future__ import annotations

from typing import Any

from agents.load_agent import LoadAgent
from agents.battery_agent import BatteryAgent
from agents.pricing_agent import PricingAgent
from agents.solar_agent import SolarAgent
from agents.grid_agent import GridAgent
from agents.forecasting_agent import ForecastingAgent
from agents.supervisor_agent import SupervisorAgent
from agents.optimization_agent import OptimizationAgent
from agents.unified_anomaly_agent import UnifiedAnomalyAgent


class EnergyController:
    """
    Central orchestration layer for the energy-management system.

    Flow:
        Telemetry
            ↓
        Specialist Agents
            ↓
        Forecasting Agent
            ↓
        Supervisor Agent
            ↓
        Optimization Agent
            ↓
        Unified Anomaly Intelligence
    """

    def __init__(self) -> None:

        self.load_agent = LoadAgent()
        self.battery_agent = BatteryAgent()
        self.pricing_agent = PricingAgent()
        self.solar_agent = SolarAgent()
        self.grid_agent = GridAgent()

        self.forecasting_agent = ForecastingAgent()

        self.supervisor = SupervisorAgent()

        self.optimization_agent = OptimizationAgent()
        self.anomaly_agent = UnifiedAnomalyAgent()

    def process(
        self,
        telemetry: dict[str, Any],
    ) -> dict[str, Any]:

        # ======================================================
        # 1. Specialist agents
        # ======================================================

        load_result = self.load_agent.analyze(
            telemetry
        )

        battery_result = self.battery_agent.analyze(
            telemetry
        )

        pricing_result = self.pricing_agent.analyze(
            telemetry
        )

        solar_result = self.solar_agent.analyze(
            telemetry
        )

        grid_result = self.grid_agent.analyze(
            telemetry
        )

        # ======================================================
        # 2. ML demand forecasting
        # ======================================================

        forecast_result = (
            self.forecasting_agent.analyze(
                telemetry
            )
        )

        # ======================================================
        # 3. High-level supervisor decision
        # ======================================================

        decision = self.supervisor.decide(
            load_result=load_result,
            battery_result=battery_result,
            pricing_result=pricing_result,
            solar_result=solar_result,
            grid_result=grid_result,
            forecast_result=forecast_result,
        )

        # ======================================================
        # 4. Numerical optimization
        # ======================================================

        optimization = (
            self.optimization_agent.optimize(
                telemetry=telemetry,
                supervisor_decision=decision,
                forecast_result=forecast_result,
            )
        )

        # ======================================================
        # 5. Unified anomaly intelligence
        # ======================================================

        anomaly = self.anomaly_agent.analyze(
            telemetry
        )

        # ======================================================
        # 6. Combined system output
        # ======================================================

        return {

            "reading_id": telemetry.get(
                "reading_id"
            ),

            "agents": {

                "load": (
                    load_result.to_dict()
                ),

                "battery": (
                    battery_result.to_dict()
                ),

                "pricing": (
                    pricing_result.to_dict()
                ),

                "solar": (
                    solar_result.to_dict()
                ),

                "grid": (
                    grid_result.to_dict()
                ),

                "forecast": (
                    forecast_result.to_dict()
                ),
            },

            "decision": (
                decision.to_dict()
            ),

            "optimization": (
                optimization.to_dict()
            ),

            "anomaly": (
                anomaly.to_dict()
            ),
        }
