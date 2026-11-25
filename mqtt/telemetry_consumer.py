from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import paho.mqtt.client as mqtt
from pydantic import BaseModel, Field, ValidationError


# ==========================================================
# PROJECT PATH SETUP
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from config.alert_config import EVENT_DATABASE_NAME
from config.mqtt_config import (
    ALERT_TOPIC,
    BROKER_HOST,
    BROKER_PORT,
    CONTROL_TOPIC,
    DECISION_TOPIC,
    EVENT_TOPIC,
    OPERATOR_SUMMARY_TOPIC,
    TELEMETRY_TOPIC,
)
from core.alert_manager import AlertManager
from core.energy_controller import EnergyController
from core.event_store import SQLiteEventStore
from core.state_manager import energy_state
from llm.operator_assistant import OperatorAssistant


# ==========================================================
# STORAGE CONFIG
# ==========================================================

DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

CSV_FILE = DATA_DIR / "telemetry.csv"
DECISION_CSV_FILE = DATA_DIR / "decisions.csv"
EVENT_DB_FILE = DATA_DIR / EVENT_DATABASE_NAME


# ==========================================================
# TELEMETRY SCHEMA
# ==========================================================

class TelemetryRecord(BaseModel):

    timestamp: str
    reading_id: int = Field(
        ge=1
    )
    demand_kw: float = Field(
        ge=0
    )
    solar_generation_kw: float = Field(
        ge=0
    )
    battery_soc_percent: float = Field(
        ge=0,
        le=100,
    )
    grid_price_inr_per_kwh: float = Field(
        ge=0
    )
    grid_carbon_intensity_g_per_kwh: float = Field(
        ge=0
    )
    temperature_c: float = Field(
        ge=-20,
        le=70,
    )
    humidity_percent: float = Field(
        ge=0,
        le=100,
    )
    occupancy_percent: float = Field(
        ge=0,
        le=100,
    )
    cloud_cover_percent: float = Field(
        ge=0,
        le=100,
    )
    net_grid_demand_kw: float = Field(
        ge=0
    )


# ==========================================================
# CSV STORAGE
# ==========================================================

class TelemetryStorage:

    def __init__(
        self,
        file_path: Path,
    ) -> None:
        self.file_path = file_path

    def save(
        self,
        record: TelemetryRecord,
    ) -> None:

        data = record.model_dump()
        file_exists = self.file_path.exists()

        with self.file_path.open(
            mode="a",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=data.keys(),
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow(
                data
            )


class DecisionStorage:

    def __init__(
        self,
        file_path: Path,
    ) -> None:
        self.file_path = file_path

    def save(
        self,
        telemetry: TelemetryRecord,
        analysis: dict,
    ) -> None:

        decision = analysis["decision"]
        optimization = analysis[
            "optimization"
        ]
        forecast = analysis[
            "agents"
        ]["forecast"]
        anomaly = analysis[
            "anomaly"
        ]
        operator = analysis.get(
            "operator_summary",
            {},
        )

        row = {
            "timestamp": telemetry.timestamp,
            "reading_id": telemetry.reading_id,

            "action": decision["action"],
            "priority": decision["priority"],
            "reason": decision["reason"],
            "confidence": decision["confidence"],

            "current_demand_kw": forecast[
                "current_demand_kw"
            ],
            "predicted_demand_kw": forecast[
                "predicted_demand_kw"
            ],
            "demand_change_kw": forecast[
                "demand_change_kw"
            ],
            "forecast_horizon_minutes": forecast[
                "forecast_horizon_minutes"
            ],
            "forecast_for_timestamp": forecast[
                "forecast_for_timestamp"
            ],
            "forecast_trend": forecast[
                "trend"
            ],
            "model_mae_kw": forecast[
                "model_mae_kw"
            ],
            "model_rmse_kw": forecast[
                "model_rmse_kw"
            ],
            "model_r2": forecast[
                "model_r2"
            ],

            "recommended_battery_power_kw": optimization[
                "recommended_battery_power_kw"
            ],
            "recommended_grid_import_kw": optimization[
                "recommended_grid_import_kw"
            ],
            "estimated_grid_reduction_kw": optimization[
                "estimated_grid_reduction_kw"
            ],
            "control_mode": optimization[
                "control_mode"
            ],
            "optimization_explanation": optimization[
                "explanation"
            ],
            "recommended_load_reduction_kw": optimization.get(
                "recommended_load_reduction_kw",
                0.0,
            ),
            "projected_soc_percent": optimization.get(
                "projected_soc_percent"
            ),
            "estimated_cost_inr_per_hour": optimization.get(
                "estimated_cost_inr_per_hour"
            ),
            "estimated_carbon_kg_per_hour": optimization.get(
                "estimated_carbon_kg_per_hour"
            ),
            "objective_score": optimization.get(
                "objective_score"
            ),
            "planning_horizon_minutes": optimization.get(
                "planning_horizon_minutes"
            ),
            "battery_constraint_active": optimization.get(
                "battery_constraint_active"
            ),

            "anomaly_status": anomaly[
                "overall_status"
            ],
            "anomaly_severity": anomaly[
                "highest_severity"
            ],
            "anomaly_count": anomaly[
                "combined_alert_count"
            ],
            "ml_anomaly_status": anomaly[
                "ml_status"
            ],
            "ml_anomaly_severity": anomaly[
                "ml_severity"
            ],
            "ml_decision_score": anomaly[
                "ml_decision_score"
            ],

            "operator_headline": operator.get(
                "headline"
            ),
            "operator_summary_source": operator.get(
                "source"
            ),
            "operator_summary_model": operator.get(
                "model"
            ),
            "operator_summary_fresh": operator.get(
                "fresh"
            ),
            "operator_summary_trigger": operator.get(
                "trigger"
            ),
            "operator_summary_latency_ms": operator.get(
                "latency_ms"
            ),
            "operator_summary_fallback": operator.get(
                "fallback_used"
            ),
        }

        self._append_row(
            row
        )

    def _append_row(
        self,
        row: dict,
    ) -> None:

        target = self.file_path

        if target.exists():

            with target.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as file:

                existing_header = next(
                    csv.reader(
                        file
                    ),
                    [],
                )

            if existing_header != list(
                row.keys()
            ):
                target = (
                    self.file_path.parent
                    / "decisions_v3.csv"
                )

        file_exists = target.exists()

        with target.open(
            mode="a",
            newline="",
            encoding="utf-8",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=row.keys(),
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow(
                row
            )


# ==========================================================
# MQTT CONSUMER
# ==========================================================

class TelemetryConsumer:

    def __init__(
        self,
    ) -> None:

        self.storage = TelemetryStorage(
            CSV_FILE
        )

        self.decision_storage = (
            DecisionStorage(
                DECISION_CSV_FILE
            )
        )

        self.energy_controller = (
            EnergyController()
        )

        self.event_store = (
            SQLiteEventStore(
                EVENT_DB_FILE
            )
        )

        self.alert_manager = (
            AlertManager(
                event_store=(
                    self.event_store
                )
            )
        )

        # Step 4: local LLM explanation/orchestration layer.
        self.operator_assistant = (
            OperatorAssistant()
        )

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=(
                "p308-telemetry-consumer"
            ),
        )

        self.client.on_connect = (
            self.on_connect
        )
        self.client.on_message = (
            self.on_message
        )
        self.client.on_disconnect = (
            self.on_disconnect
        )

    def on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ) -> None:

        if reason_code == 0:

            print(
                f"✅ Connected to MQTT broker "
                f"{BROKER_HOST}:{BROKER_PORT}"
            )

            client.subscribe(
                TELEMETRY_TOPIC,
                qos=1,
            )

            print(
                f"📥 Subscribed to: "
                f"{TELEMETRY_TOPIC}"
            )

        else:
            print(
                f"❌ MQTT connection failed: "
                f"{reason_code}"
            )

    def on_message(
        self,
        client,
        userdata,
        message,
    ) -> None:

        try:

            payload = (
                message.payload.decode(
                    "utf-8"
                )
            )

            raw_data = json.loads(
                payload
            )

            record = TelemetryRecord(
                **raw_data
            )

            self.storage.save(
                record
            )

            telemetry_dict = (
                record.model_dump()
            )

            energy_state.update(
                telemetry_dict
            )

            # --------------------------------------------------
            # Deterministic + ML control pipeline
            # --------------------------------------------------

            analysis = (
                self.energy_controller.process(
                    telemetry_dict
                )
            )

            anomaly = analysis[
                "anomaly"
            ]

            # --------------------------------------------------
            # Alert lifecycle
            # --------------------------------------------------

            dispatch = (
                self.alert_manager.process(
                    telemetry=telemetry_dict,
                    anomaly=anomaly,
                )
            )

            # --------------------------------------------------
            # Step 4: local LLM operator explanation
            #
            # IMPORTANT:
            # The LLM sees the decision AFTER deterministic control
            # computation. It cannot modify optimization/control fields.
            # --------------------------------------------------

            operator_summary = (
                self.operator_assistant.summarize(
                    telemetry=telemetry_dict,
                    analysis=analysis,
                    alert_payload=(
                        dispatch.alert_payload
                    ),
                )
            )

            analysis[
                "operator_summary"
            ] = (
                operator_summary.to_dict()
            )

            # Persist after operator summary is attached.
            self.decision_storage.save(
                record,
                analysis,
            )

            # --------------------------------------------------
            # MQTT alert/event publishing
            # --------------------------------------------------

            if (
                dispatch.alert_payload
                is not None
            ):
                self.client.publish(
                    topic=ALERT_TOPIC,
                    payload=json.dumps(
                        dispatch.alert_payload
                    ),
                    qos=1,
                )

            for event_payload in (
                dispatch.event_payloads
            ):
                self.client.publish(
                    topic=EVENT_TOPIC,
                    payload=json.dumps(
                        event_payload
                    ),
                    qos=1,
                )

            # Publish a fresh LLM/fallback summary only when generated.
            if operator_summary.fresh:
                self.client.publish(
                    topic=(
                        OPERATOR_SUMMARY_TOPIC
                    ),
                    payload=json.dumps(
                        operator_summary.to_dict()
                    ),
                    qos=1,
                )

            # --------------------------------------------------
            # Decision channel
            # --------------------------------------------------

            decision_payload = {
                "timestamp": record.timestamp,
                "reading_id": record.reading_id,
                "decision": analysis[
                    "decision"
                ],
                "optimization": analysis[
                    "optimization"
                ],
                "forecast": analysis[
                    "agents"
                ]["forecast"],
                "anomaly": anomaly,
                "operator_summary": (
                    operator_summary.to_dict()
                ),
            }

            self.client.publish(
                topic=DECISION_TOPIC,
                payload=json.dumps(
                    decision_payload
                ),
                qos=1,
            )

            # --------------------------------------------------
            # Closed-loop actuator command
            # --------------------------------------------------

            optimization = analysis[
                "optimization"
            ]

            control_payload = {
                "timestamp": record.timestamp,
                "reading_id": record.reading_id,
                "action": analysis[
                    "decision"
                ]["action"],
                "control_mode": optimization[
                    "control_mode"
                ],
                "battery_power_kw": optimization[
                    "recommended_battery_power_kw"
                ],
                "recommended_grid_import_kw": optimization[
                    "recommended_grid_import_kw"
                ],
                "recommended_load_reduction_kw": optimization.get(
                    "recommended_load_reduction_kw",
                    0.0,
                ),
            }

            # Control MQTT payload is constructed ONLY from
            # deterministic controller/optimizer output.
            self.client.publish(
                topic=CONTROL_TOPIC,
                payload=json.dumps(
                    control_payload
                ),
                qos=1,
            )

            # --------------------------------------------------
            # Console output
            # --------------------------------------------------

            decision = analysis[
                "decision"
            ]
            forecast = analysis[
                "agents"
            ]["forecast"]

            print(
                f"\n✅ Reading #{record.reading_id} "
                f"validated | stored | analyzed"
            )

            print(
                f"🤖 Decision: "
                f"{decision['action']} | "
                f"Priority: "
                f"{decision['priority']} | "
                f"Confidence: "
                f"{decision['confidence']:.2f}"
            )

            print(
                f"   Reason: "
                f"{decision['reason']}"
            )

            print(
                f"   Demand: "
                f"{record.demand_kw:.2f} kW | "
                f"Solar: "
                f"{record.solar_generation_kw:.2f} kW | "
                f"Battery: "
                f"{record.battery_soc_percent:.2f}%"
            )

            print(
                f"   Forecast +"
                f"{forecast['forecast_horizon_minutes']}m: "
                f"{forecast['predicted_demand_kw']:.2f} kW | "
                f"Trend: "
                f"{forecast['trend']}"
            )

            print(
                f"⚙️ Optimization: "
                f"{optimization['control_mode']} | "
                f"Battery: "
                f"{optimization['recommended_battery_power_kw']:.2f} kW | "
                f"Grid: "
                f"{optimization['recommended_grid_import_kw']:.2f} kW | "
                f"Projected SOC: "
                f"{optimization.get('projected_soc_percent', 0.0):.2f}%"
            )

            print(
                f"🚨 Anomaly: "
                f"{anomaly['overall_status']} | "
                f"Severity: "
                f"{anomaly['highest_severity']} | "
                f"Signals: "
                f"{anomaly['combined_alert_count']}"
            )

            if (
                dispatch.alert_payload
                is not None
            ):

                alert = (
                    dispatch.alert_payload
                )

                print(
                    f"📣 ALERT "
                    f"{alert['lifecycle']} → "
                    f"{alert['severity']}"
                )

            elif dispatch.suppressed:
                print(
                    "🔕 Duplicate active alert "
                    "suppressed."
                )

            if operator_summary.fresh:
                print(
                    f"🧠 Operator Summary "
                    f"[{operator_summary.source} | "
                    f"{operator_summary.trigger} | "
                    f"{operator_summary.latency_ms:.0f} ms]"
                )
                print(
                    f"   "
                    f"{operator_summary.headline}"
                )
                print(
                    f"   "
                    f"{operator_summary.situation}"
                )
            else:
                print(
                    "🧠 Operator Summary: cached"
                )

            print(
                f"🎛️ Control published → "
                f"{CONTROL_TOPIC}"
            )

        except json.JSONDecodeError:
            print(
                "❌ Invalid JSON received"
            )

        except ValidationError as exc:
            print(
                "❌ Telemetry validation failed"
            )
            print(
                exc
            )

        except Exception as exc:
            print(
                f"❌ Unexpected error: "
                f"{exc}"
            )

    def on_disconnect(
        self,
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ) -> None:

        print(
            f"🔌 MQTT disconnected: "
            f"{reason_code}"
        )

    def start(
        self,
    ) -> None:

        print(
            "\n📡 P_308 Telemetry Consumer Starting..."
        )

        print(
            f"💾 Telemetry CSV: "
            f"{CSV_FILE}"
        )

        print(
            f"🧠 Decision CSV: "
            f"{DECISION_CSV_FILE}"
        )

        print(
            f"🗄️ Alert/Event DB: "
            f"{EVENT_DB_FILE}"
        )

        print(
            f"💬 Operator summary topic: "
            f"{OPERATOR_SUMMARY_TOPIC}"
        )

        self.client.connect(
            BROKER_HOST,
            BROKER_PORT,
            keepalive=60,
        )

        try:
            self.client.loop_forever()

        except KeyboardInterrupt:
            print(
                "\n🛑 Telemetry consumer stopped."
            )
            self.client.disconnect()


def main() -> None:

    consumer = (
        TelemetryConsumer()
    )

    consumer.start()


if __name__ == "__main__":
    main()
