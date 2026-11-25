from __future__ import annotations

import importlib
import socket
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from config.api_config import (
    API_HOST,
    API_PORT,
)
from config.llm_config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from config.mqtt_config import (
    BROKER_HOST,
    BROKER_PORT,
)
from config.runtime_config import (
    ANOMALY_MODEL_FILE,
    DASHBOARD_DIR,
    FORECAST_MODEL_FILE,
    MQTT_CONFIG_FILE,
    PROJECT_ROOT,
    ensure_runtime_directories,
)


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


REQUIRED_IMPORTS = (
    "numpy",
    "pandas",
    "sklearn",
    "joblib",
    "paho.mqtt.client",
    "pydantic",
    "fastapi",
    "uvicorn",
    "httpx",
    "psutil",
    "prometheus_client",
)


def check_dependencies() -> list[CheckResult]:

    results: list[CheckResult] = []

    for module_name in REQUIRED_IMPORTS:
        try:
            importlib.import_module(
                module_name
            )
            results.append(
                CheckResult(
                    name=f"dependency:{module_name}",
                    status="PASS",
                    detail="Import successful.",
                )
            )
        except Exception as exc:
            results.append(
                CheckResult(
                    name=f"dependency:{module_name}",
                    status="FAIL",
                    detail=(
                        f"{type(exc).__name__}: {exc}"
                    ),
                )
            )

    return results


def check_required_files() -> list[CheckResult]:

    checks = {
        "forecast-model": FORECAST_MODEL_FILE,
        "anomaly-model": ANOMALY_MODEL_FILE,
        "mqtt-config": MQTT_CONFIG_FILE,
        "dashboard-index": (
            DASHBOARD_DIR / "index.html"
        ),
        "dashboard-css": (
            DASHBOARD_DIR / "styles.css"
        ),
        "dashboard-js": (
            DASHBOARD_DIR / "app.js"
        ),
    }

    results: list[CheckResult] = []

    for name, path in checks.items():

        exists = path.exists()

        results.append(
            CheckResult(
                name=name,
                status=(
                    "PASS"
                    if exists
                    else "FAIL"
                ),
                detail=str(
                    path
                ),
            )
        )

    return results


def check_python_packages() -> list[CheckResult]:

    package_dirs = (
        "agents",
        "api",
        "config",
        "core",
        "llm",
        "ml",
        "mqtt",
        "simulator",
        "tests",
        "tools",
    )

    results: list[CheckResult] = []

    for name in package_dirs:

        path = (
            PROJECT_ROOT / name
        )

        results.append(
            CheckResult(
                name=f"folder:{name}",
                status=(
                    "PASS"
                    if path.exists()
                    else "FAIL"
                ),
                detail=str(
                    path
                ),
            )
        )

    return results


def tcp_reachable(
    host: str,
    port: int,
    timeout: float = 0.8,
) -> bool:

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout,
        ):
            return True

    except OSError:
        return False


def check_external_services() -> list[CheckResult]:

    ollama_host = "127.0.0.1"

    try:
        without_scheme = (
            OLLAMA_BASE_URL
            .replace(
                "http://",
                "",
            )
            .replace(
                "https://",
                "",
            )
        )

        host_part = without_scheme.split(
            "/"
        )[0]

        if ":" in host_part:
            ollama_host, ollama_port_str = (
                host_part.rsplit(
                    ":",
                    1,
                )
            )
            ollama_port = int(
                ollama_port_str
            )
        else:
            ollama_host = host_part
            ollama_port = 11434

    except Exception:
        ollama_host = "127.0.0.1"
        ollama_port = 11434

    service_specs = (
        (
            "mqtt-broker",
            BROKER_HOST,
            BROKER_PORT,
            False,
        ),
        (
            f"ollama:{OLLAMA_MODEL}",
            ollama_host,
            ollama_port,
            False,
        ),
        (
            "fastapi",
            API_HOST,
            API_PORT,
            False,
        ),
    )

    results: list[CheckResult] = []

    for (
        name,
        host,
        port,
        required,
    ) in service_specs:

        reachable = tcp_reachable(
            host,
            port,
        )

        results.append(
            CheckResult(
                name=f"service:{name}",
                status=(
                    "PASS"
                    if reachable
                    else "WARN"
                ),
                detail=(
                    f"{host}:{port} "
                    + (
                        "reachable"
                        if reachable
                        else (
                            "not running right now; "
                            "this is allowed during "
                            "offline preflight."
                        )
                    )
                ),
            )
        )

    return results


def run_preflight(
    include_services: bool = True,
) -> list[CheckResult]:

    ensure_runtime_directories()

    results: list[CheckResult] = []

    results.extend(
        check_dependencies()
    )

    results.extend(
        check_required_files()
    )

    results.extend(
        check_python_packages()
    )

    if include_services:
        results.extend(
            check_external_services()
        )

    return results


def has_failures(
    results: Iterable[CheckResult],
) -> bool:

    return any(
        item.status == "FAIL"
        for item in results
    )
