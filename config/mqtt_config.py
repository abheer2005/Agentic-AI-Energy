# ============================================================
# P_308 - Agentic Energy AI
# MQTT Configuration
# ============================================================

BROKER_HOST = "127.0.0.1"
BROKER_PORT = 18883

TELEMETRY_TOPIC = "energy/building01/telemetry"
DECISION_TOPIC = "energy/building01/decisions"
CONTROL_TOPIC = "energy/building01/control"
ALERT_TOPIC = "energy/building01/alerts"
EVENT_TOPIC = "energy/building01/events"

# Step 4: operator-facing LLM summaries.
OPERATOR_SUMMARY_TOPIC = "energy/building01/operator-summary"

CLIENT_ID = "p308-energy-simulator"
