from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ------------------------------------------------------------------
# Runtime configuration
# ------------------------------------------------------------------

MQTT_HOST = os.getenv("P308_MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("P308_MQTT_PORT", "18883"))

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434

API_HOST = os.getenv("P308_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("P308_API_PORT", "8007"))

API_BASE_URL = f"http://{API_HOST}:{API_PORT}"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_json(path: str, timeout: float = 5.0):
    url = f"{API_BASE_URL}{path}"

    try:
        with urlopen(url, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)

            print(f"✅ GET {url} -> {response.status}")
            return data

    except HTTPError as exc:
        print(f"❌ GET {url} -> HTTP Error {exc.code}: {exc.reason}")

    except URLError as exc:
        print(f"❌ GET {url} -> {exc.reason}")

    except Exception as exc:
        print(f"❌ GET {url} -> {exc}")

    return None


def extract_live_data(response: dict | None) -> dict:
    if not isinstance(response, dict):
        return {}

    data = response.get("data", {})

    # API response may be:
    # {"success": true, "data": {...}}
    # or {"success": true, "data": {"data": {...}}}
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        return data["data"]

    if isinstance(data, dict):
        return data

    return {}


# ------------------------------------------------------------------
# Main smoke check
# ------------------------------------------------------------------

def main() -> int:
    print()
    print("=" * 60)
    print("P_308 - LIVE END-TO-END SMOKE CHECK")
    print("=" * 60)
    print()

    failures = 0

    # --------------------------------------------------------------
    # Service connectivity
    # --------------------------------------------------------------

    if tcp_check(MQTT_HOST, MQTT_PORT):
        print(f"✅ MQTT broker        {MQTT_HOST}:{MQTT_PORT}")
    else:
        print(f"❌ MQTT broker        {MQTT_HOST}:{MQTT_PORT}")
        failures += 1

    if tcp_check(OLLAMA_HOST, OLLAMA_PORT):
        print(f"✅ Ollama             {OLLAMA_HOST}:{OLLAMA_PORT}")
    else:
        print(f"⚠️ Ollama             {OLLAMA_HOST}:{OLLAMA_PORT}")
        print("   Local LLM unavailable; deterministic fallback may be used.")

    if tcp_check(API_HOST, API_PORT):
        print(f"✅ FastAPI            {API_HOST}:{API_PORT}")
    else:
        print(f"❌ FastAPI            {API_HOST}:{API_PORT}")
        failures += 1

    print()

    # --------------------------------------------------------------
    # API endpoint verification
    # --------------------------------------------------------------

    health = get_json("/api/v1/health")
    detailed_health = get_json("/api/v1/health/detailed")
    live_response = get_json("/api/v1/live")
    models = get_json("/api/v1/models")
    history_counts = get_json("/api/v1/history/counts")

    required_responses = [
        health,
        detailed_health,
        live_response,
        models,
        history_counts,
    ]

    for response in required_responses:
        if response is None:
            failures += 1

    # --------------------------------------------------------------
    # Live pipeline verification
    # --------------------------------------------------------------

    live_data = extract_live_data(live_response)

    required_channels = [
        "telemetry",
        "decision",
        "control",
    ]

    empty_channels = [
        channel
        for channel in required_channels
        if not live_data.get(channel)
    ]

    print()

    if empty_channels:
        print(
            "⚠️ API is alive but these live channels are still empty: "
            + ", ".join(empty_channels)
        )
        print("   Make sure simulator + telemetry consumer are also running.")

        failures += 1
    else:
        print("✅ Live telemetry available")
        print("✅ Live AI decision available")
        print("✅ Live control command available")

    # --------------------------------------------------------------
    # Optional channels
    # --------------------------------------------------------------

    if live_data.get("operator_summary"):
        print("✅ Local LLM/operator summary available")
    else:
        print("⚠️ Operator summary not available yet")

    if live_data.get("alert"):
        print("✅ Alert state available")
    else:
        print("ℹ️ No active alert currently")

    # --------------------------------------------------------------
    # Final result
    # --------------------------------------------------------------

    print()
    print("=" * 60)

    if failures == 0:
        print("✅ LIVE END-TO-END SMOKE CHECK PASSED")
        print("=" * 60)
        return 0

    print(f"❌ LIVE SMOKE CHECK FAILED ({failures} issue(s))")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())