from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_FILE = (
    PROJECT_ROOT
    / "models"
    / "energy_anomaly_detector.joblib"
)


@dataclass
class MLAnomalyAnalysis:
    status: str
    anomaly_score: float
    decision_score: float
    severity: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MLAnomalyAgent:
    """
    Detects unusual multivariate energy behavior using a trained
    Isolation Forest model.

    Important:
        This agent detects unusual combinations of values.

        It does NOT replace deterministic safety rules.
    """

    def __init__(self) -> None:

        if not MODEL_FILE.exists():

            raise FileNotFoundError(
                f"Anomaly model not found: {MODEL_FILE}"
            )

        bundle = joblib.load(
            MODEL_FILE
        )

        self.model = bundle[
            "model"
        ]

        self.features = bundle[
            "features"
        ]

        self.training_rows = bundle.get(
            "training_rows"
        )

        self.training_anomaly_rate = bundle.get(
            "training_anomaly_rate_percent"
        )

    # ======================================================
    # MAIN ANALYSIS
    # ======================================================

    def analyze(
        self,
        telemetry: dict[str, Any],
    ) -> MLAnomalyAnalysis:

        feature_values = {}

        for feature in self.features:

            if feature not in telemetry:

                raise KeyError(
                    f"Telemetry missing required feature: "
                    f"{feature}"
                )

            feature_values[
                feature
            ] = float(
                telemetry[
                    feature
                ]
            )

        feature_frame = pd.DataFrame(
            [
                feature_values
            ],
            columns=self.features,
        )

        # --------------------------------------------------
        # Isolation Forest prediction
        #
        # +1 = normal
        # -1 = anomaly
        # --------------------------------------------------

        prediction = int(
            self.model.predict(
                feature_frame
            )[0]
        )

        # --------------------------------------------------
        # decision_function:
        #
        # positive → more normal
        # negative → more anomalous
        # --------------------------------------------------

        decision_score = float(
            self.model.decision_function(
                feature_frame
            )[0]
        )

        # --------------------------------------------------
        # score_samples:
        #
        # Lower values generally indicate more unusual points.
        # --------------------------------------------------

        raw_anomaly_score = float(
            self.model.score_samples(
                feature_frame
            )[0]
        )

        # Easier-to-read representation:
        # more positive = more anomalous
        anomaly_score = (
            -raw_anomaly_score
        )

        # ==================================================
        # NORMAL
        # ==================================================

        if prediction == 1:

            return MLAnomalyAnalysis(
                status="NORMAL",
                anomaly_score=round(
                    anomaly_score,
                    4,
                ),
                decision_score=round(
                    decision_score,
                    4,
                ),
                severity="NONE",
                recommendation=(
                    "Current multivariate energy behavior "
                    "is consistent with learned historical patterns."
                ),
            )

        # ==================================================
        # ANOMALOUS
        # ==================================================

        severity = (
            self._classify_severity(
                decision_score
            )
        )

        if severity == "CRITICAL":

            recommendation = (
                "Highly unusual system behavior detected. "
                "Immediately inspect operating conditions and "
                "cross-check rule-based safety alerts."
            )

        elif severity == "HIGH":

            recommendation = (
                "Strong multivariate anomaly detected. "
                "Review demand, solar, battery, pricing and "
                "grid behavior together."
            )

        else:

            recommendation = (
                "Unusual energy behavior detected. "
                "Continue monitoring and correlate with "
                "rule-based alerts."
            )

        return MLAnomalyAnalysis(
            status="ANOMALOUS",
            anomaly_score=round(
                anomaly_score,
                4,
            ),
            decision_score=round(
                decision_score,
                4,
            ),
            severity=severity,
            recommendation=recommendation,
        )

    # ======================================================
    # SEVERITY
    # ======================================================

    @staticmethod
    def _classify_severity(
        decision_score: float,
    ) -> str:

        if decision_score <= -0.08:
            return "CRITICAL"

        if decision_score <= -0.03:
            return "HIGH"

        return "MEDIUM"