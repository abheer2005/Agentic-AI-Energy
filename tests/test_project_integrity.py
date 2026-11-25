from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


print("\n1) Required project folders")

required_dirs = (
    "agents",
    "api",
    "config",
    "core",
    "dashboard",
    "data",
    "llm",
    "ml",
    "models",
    "mqtt",
    "simulator",
    "tests",
    "tools",
)

for name in required_dirs:
    assert (
        PROJECT_ROOT
        / name
    ).exists(), (
        f"Missing folder: {name}"
    )

print("   PASS")


print("\n2) Critical model/config assets")

required_files = (
    "models/demand_forecaster.joblib",
    "models/energy_anomaly_detector.joblib",
    "mqtt/mosquitto.conf",
    "dashboard/index.html",
    "dashboard/styles.css",
    "dashboard/app.js",
)

for relative in required_files:
    assert (
        PROJECT_ROOT
        / relative
    ).exists(), (
        f"Missing file: {relative}"
    )

print("   PASS")


print("\n3) Core module imports")

modules = (
    "agents.anomaly_agent",
    "agents.forecasting_agent",
    "agents.supervisor_agent",
    "agents.optimization_agent",
    "agents.unified_anomaly_agent",
    "api.main",
    "api.routes",
    "api.mqtt_bridge",
    "core.alert_manager",
    "core.energy_controller",
    "core.event_store",
    "core.logging_config",
    "core.metrics",
    "llm.operator_assistant",
    "llm.ollama_client",
)

for module_name in modules:
    importlib.import_module(
        module_name
    )

print("   PASS")


print("\n4) Safety boundary")

consumer_path = (
    PROJECT_ROOT
    / "mqtt"
    / "telemetry_consumer.py"
)

source = consumer_path.read_text(
    encoding="utf-8"
)

assert (
    "operator_summary"
    in source
)

assert (
    "control_payload"
    in source
)

# Control payload must still come from deterministic
# optimization/controller output rather than LLM text.
control_section = source[
    source.find(
        "control_payload"
    ):
]

assert (
    "optimization"
    in control_section
)

print("   PASS")


print("\n5) Final requirements file")

requirements = (
    PROJECT_ROOT
    / "requirements.txt"
)

assert requirements.exists()

content = requirements.read_text(
    encoding="utf-8"
)

for package in (
    "numpy",
    "paho-mqtt",
    "pydantic",
    "pandas",
    "scikit-learn",
    "joblib",
    "fastapi",
    "uvicorn",
    "httpx",
    "psutil",
    "prometheus-client",
):
    assert (
        package in content
    )

print("   PASS")


print(
    "\n✅ STEP 8 PROJECT INTEGRITY TESTS PASSED"
)
