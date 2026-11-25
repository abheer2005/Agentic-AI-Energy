from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Protocol

from pydantic import ValidationError

from config.llm_config import (
    LLM_ENABLED,
    LLM_MAX_RETRIES,
    LLM_SUMMARY_INTERVAL_SECONDS,
    OLLAMA_MODEL,
)
from llm.ollama_client import (
    LocalLLMError,
    OllamaClient,
)
from llm.prompts import (
    SYSTEM_PROMPT,
    build_operator_prompt,
)
from llm.schemas import (
    LLMOperatorContent,
    OperatorSummary,
)


class JSONChatProvider(Protocol):

    model: str

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> Any:
        ...


class OperatorAssistant:
    """
    Safe LLM orchestration layer.

    The local LLM receives already-computed telemetry/agent/controller
    outputs and turns them into an operator-facing explanation.

    It cannot alter the deterministic decision or optimization result.
    """

    def __init__(
        self,
        provider: JSONChatProvider | None = None,
        enabled: bool = LLM_ENABLED,
        summary_interval_seconds: int = (
            LLM_SUMMARY_INTERVAL_SECONDS
        ),
    ) -> None:

        self.enabled = enabled

        self.provider = (
            provider
            if provider is not None
            else OllamaClient()
        )

        self.summary_interval_seconds = max(
            5,
            int(
                summary_interval_seconds
            ),
        )

        self._last_summary: (
            OperatorSummary | None
        ) = None

        self._last_generation_monotonic: (
            float | None
        ) = None

        self._last_action: (
            str | None
        ) = None

        self._last_anomaly_signature: (
            str | None
        ) = None

    def summarize(
        self,
        telemetry: dict[str, Any],
        analysis: dict[str, Any],
        alert_payload: (
            dict[str, Any] | None
        ) = None,
    ) -> OperatorSummary:

        trigger = self._generation_trigger(
            analysis=analysis,
            alert_payload=alert_payload,
        )

        if (
            trigger is None
            and self._last_summary is not None
        ):
            return self._cached_summary()

        if trigger is None:
            trigger = "INITIAL"

        if not self.enabled:
            summary = (
                self._fallback_summary(
                    telemetry=telemetry,
                    analysis=analysis,
                    trigger=trigger,
                    reason=(
                        "Local LLM layer is disabled."
                    ),
                )
            )
            self._remember(
                summary,
                analysis,
            )
            return summary

        started = time.perf_counter()

        prompt = build_operator_prompt(
            telemetry=telemetry,
            analysis=analysis,
            alert_context=alert_payload,
        )

        last_error: (
            Exception | None
        ) = None

        attempts = max(
            1,
            LLM_MAX_RETRIES + 1,
        )

        for attempt in range(
            attempts
        ):

            try:
                user_prompt = prompt

                if attempt > 0:
                    user_prompt += (
                        "\nPrevious response was invalid. "
                        "Return ONLY JSON matching the "
                        "required schema exactly."
                    )

                provider_response = (
                    self.provider.chat_json(
                        SYSTEM_PROMPT,
                        user_prompt,
                    )
                )

                raw_content = getattr(
                    provider_response,
                    "content",
                    provider_response,
                )

                model_name = str(
                    getattr(
                        provider_response,
                        "model",
                        getattr(
                            self.provider,
                            "model",
                            OLLAMA_MODEL,
                        ),
                    )
                )

                content = (
                    self._parse_and_validate(
                        raw_content
                    )
                )

                latency_ms = (
                    time.perf_counter()
                    - started
                ) * 1000.0

                summary = OperatorSummary(
                    headline=(
                        content.headline
                    ),
                    situation=(
                        content.situation
                    ),
                    why=content.why,
                    operator_actions=(
                        content.operator_actions
                    ),
                    risks=(
                        content.risks
                    ),
                    confidence_note=(
                        content.confidence_note
                    ),
                    source="local_llm",
                    model=model_name,
                    generated_at=(
                        self._utc_now()
                    ),
                    latency_ms=round(
                        latency_ms,
                        2,
                    ),
                    fresh=True,
                    trigger=trigger,
                    fallback_used=False,
                )

                self._remember(
                    summary,
                    analysis,
                )

                return summary

            except (
                LocalLLMError,
                ValidationError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as exc:
                last_error = exc

        latency_ms = (
            time.perf_counter()
            - started
        ) * 1000.0

        summary = self._fallback_summary(
            telemetry=telemetry,
            analysis=analysis,
            trigger=trigger,
            reason=(
                f"Local LLM fallback: "
                f"{type(last_error).__name__}: "
                f"{last_error}"
            ),
            latency_ms=latency_ms,
        )

        self._remember(
            summary,
            analysis,
        )

        return summary

    # ==========================================================
    # Trigger / cache policy
    # ==========================================================

    def _generation_trigger(
        self,
        analysis: dict[str, Any],
        alert_payload: (
            dict[str, Any] | None
        ),
    ) -> str | None:

        if self._last_summary is None:
            return "INITIAL"

        if alert_payload is not None:
            lifecycle = str(
                alert_payload.get(
                    "lifecycle",
                    "ALERT",
                )
            )
            return (
                f"ALERT_{lifecycle}"
            )

        action = str(
            analysis.get(
                "decision",
                {},
            ).get(
                "action",
                "UNKNOWN",
            )
        )

        if (
            self._last_action is not None
            and action != self._last_action
        ):
            return "DECISION_CHANGE"

        anomaly_signature = (
            self._anomaly_signature(
                analysis
            )
        )

        if (
            self._last_anomaly_signature
            is not None
            and anomaly_signature
            != self._last_anomaly_signature
        ):
            return "ANOMALY_CHANGE"

        if (
            self._last_generation_monotonic
            is None
        ):
            return "INITIAL"

        elapsed = (
            time.monotonic()
            - self._last_generation_monotonic
        )

        if (
            elapsed
            >= self.summary_interval_seconds
        ):
            return "PERIODIC"

        return None

    def _remember(
        self,
        summary: OperatorSummary,
        analysis: dict[str, Any],
    ) -> None:

        self._last_summary = summary

        self._last_generation_monotonic = (
            time.monotonic()
        )

        self._last_action = str(
            analysis.get(
                "decision",
                {},
            ).get(
                "action",
                "UNKNOWN",
            )
        )

        self._last_anomaly_signature = (
            self._anomaly_signature(
                analysis
            )
        )

    def _cached_summary(
        self,
    ) -> OperatorSummary:

        assert (
            self._last_summary
            is not None
        )

        cached = (
            self._last_summary.to_dict()
        )

        cached["fresh"] = False
        cached["trigger"] = "CACHE"

        return OperatorSummary(
            **cached
        )

    # ==========================================================
    # Validation
    # ==========================================================

    @staticmethod
    def _parse_and_validate(
        raw_content: Any,
    ) -> LLMOperatorContent:

        if isinstance(
            raw_content,
            dict,
        ):
            payload = raw_content

        elif isinstance(
            raw_content,
            str,
        ):
            text = raw_content.strip()

            if text.startswith(
                "```"
            ):
                text = (
                    text.replace(
                        "```json",
                        "",
                        1,
                    )
                    .replace(
                        "```",
                        "",
                    )
                    .strip()
                )

            payload = json.loads(
                text
            )

        else:
            raise TypeError(
                "LLM response must be "
                "a JSON string or dictionary."
            )

        return (
            LLMOperatorContent.model_validate(
                payload
            )
        )

    # ==========================================================
    # Deterministic fallback
    # ==========================================================

    def _fallback_summary(
        self,
        telemetry: dict[str, Any],
        analysis: dict[str, Any],
        trigger: str,
        reason: str,
        latency_ms: float = 0.0,
    ) -> OperatorSummary:

        decision = analysis.get(
            "decision",
            {},
        )

        optimization = analysis.get(
            "optimization",
            {},
        )

        anomaly = analysis.get(
            "anomaly",
            {},
        )

        forecast = analysis.get(
            "agents",
            {},
        ).get(
            "forecast",
            {},
        )

        action = str(
            decision.get(
                "action",
                "UNKNOWN",
            )
        )

        severity = str(
            anomaly.get(
                "highest_severity",
                "NONE",
            )
        )

        headline = (
            f"{severity} energy status — "
            f"{action}"
        )

        situation = (
            f"Measured demand is "
            f"{self._number(telemetry.get('demand_kw'))} kW, "
            f"solar generation is "
            f"{self._number(telemetry.get('solar_generation_kw'))} kW, "
            f"battery SOC is "
            f"{self._number(telemetry.get('battery_soc_percent'))}%, "
            f"and current grid demand is "
            f"{self._number(telemetry.get('net_grid_demand_kw'))} kW."
        )

        predicted = forecast.get(
            "predicted_demand_kw"
        )

        trend = forecast.get(
            "trend",
            "UNKNOWN",
        )

        why = (
            f"The deterministic supervisor selected {action}. "
            f"The optimizer recommends "
            f"{self._number(optimization.get('recommended_battery_power_kw'))} "
            f"kW battery power and "
            f"{self._number(optimization.get('recommended_grid_import_kw'))} "
            f"kW grid import. "
            f"The +{forecast.get('forecast_horizon_minutes', 15)} minute "
            f"demand forecast is {self._number(predicted)} kW "
            f"with trend {trend}."
        )

        risks: list[str] = []

        if severity not in {
            "NONE",
            "LOW",
        }:
            risks.append(
                anomaly.get(
                    "summary",
                    f"{severity} anomaly condition is active.",
                )
            )

        if optimization.get(
            "battery_constraint_active"
        ):
            risks.append(
                "Battery dispatch is constrained by SOC/energy limits."
            )

        actions = []

        if severity in {
            "HIGH",
            "CRITICAL",
        }:
            actions.append(
                "Review the active anomaly details and verify the affected energy subsystem."
            )

        if action == "SHED_NON_CRITICAL_LOAD":
            actions.append(
                "Confirm that non-critical loads can be safely curtailed."
            )

        if not actions:
            actions.append(
                "Continue monitoring telemetry and the deterministic controller response."
            )

        return OperatorSummary(
            headline=headline,
            situation=situation,
            why=why,
            operator_actions=actions[
                :3
            ],
            risks=risks[:3],
            confidence_note=(
                f"{reason} This summary is deterministic "
                "and uses only current system outputs."
            ),
            source="deterministic_fallback",
            model="none",
            generated_at=(
                self._utc_now()
            ),
            latency_ms=round(
                latency_ms,
                2,
            ),
            fresh=True,
            trigger=trigger,
            fallback_used=True,
        )

    # ==========================================================
    # Helpers
    # ==========================================================

    @staticmethod
    def _anomaly_signature(
        analysis: dict[str, Any],
    ) -> str:

        anomaly = analysis.get(
            "anomaly",
            {},
        )

        event_types = sorted(
            str(
                event.get(
                    "anomaly_type",
                    "UNKNOWN",
                )
            )
            for event in anomaly.get(
                "rule_events",
                [],
            )
        )

        return json.dumps(
            {
                "status": anomaly.get(
                    "overall_status"
                ),
                "severity": anomaly.get(
                    "highest_severity"
                ),
                "ml_status": anomaly.get(
                    "ml_status"
                ),
                "events": event_types,
            },
            sort_keys=True,
        )

    @staticmethod
    def _number(
        value: Any,
    ) -> str:

        try:
            return f"{float(value):.2f}"
        except (
            TypeError,
            ValueError,
        ):
            return "unknown"

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()
