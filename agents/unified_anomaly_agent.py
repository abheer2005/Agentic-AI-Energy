from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from agents.anomaly_agent import AnomalyAgent
from agents.ml_anomaly_agent import MLAnomalyAgent


@dataclass
class UnifiedAnomalyAnalysis:
    overall_status: str
    highest_severity: str
    rule_anomaly_count: int
    ml_status: str
    ml_severity: str
    ml_decision_score: float
    combined_alert_count: int
    rule_events: list[dict[str, Any]]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UnifiedAnomalyAgent:

    SEVERITY_RANK = {
        "NONE": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    def __init__(self) -> None:

        self.rule_agent = AnomalyAgent()
        self.ml_agent = MLAnomalyAgent()

    def analyze(
        self,
        telemetry: dict[str, Any],
    ) -> UnifiedAnomalyAnalysis:

        rule_result = self.rule_agent.analyze(
            telemetry
        )

        ml_result = self.ml_agent.analyze(
            telemetry
        )

        highest_severity = max(
            [
                rule_result.highest_severity,
                ml_result.severity,
            ],
            key=lambda severity:
                self.SEVERITY_RANK[
                    severity
                ],
        )

        ml_alert_count = (
            1
            if ml_result.status == "ANOMALOUS"
            else 0
        )

        combined_alert_count = (
            rule_result.anomaly_count
            + ml_alert_count
        )

        if combined_alert_count == 0:

            overall_status = "NORMAL"

            summary = (
                "No operational or ML-based anomalies detected."
            )

        elif highest_severity == "CRITICAL":

            overall_status = "CRITICAL"

            summary = (
                "Critical abnormal system behavior detected. "
                "Immediate operational review is recommended."
            )

        elif highest_severity == "HIGH":

            overall_status = "WARNING"

            summary = (
                "High-severity abnormal energy behavior detected."
            )

        else:

            overall_status = "ATTENTION"

            summary = (
                "Unusual energy behavior detected. "
                "Continue monitoring current conditions."
            )

        return UnifiedAnomalyAnalysis(
            overall_status=overall_status,
            highest_severity=highest_severity,
            rule_anomaly_count=rule_result.anomaly_count,
            ml_status=ml_result.status,
            ml_severity=ml_result.severity,
            ml_decision_score=ml_result.decision_score,
            combined_alert_count=combined_alert_count,
            rule_events=rule_result.events,
            summary=summary,
        )