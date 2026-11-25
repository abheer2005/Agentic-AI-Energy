from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

TEST_DIR = (
    PROJECT_ROOT
    / "tests"
)


KNOWN_TESTS = (
    "test_unified_anomaly_agent.py",
    "test_optimization_agent.py",
    "test_alert_pipeline.py",
    "test_llm_layer.py",
    "test_api_backend.py",
    "test_dashboard.py",
    "test_observability.py",
    "test_project_integrity.py",
)


def main() -> None:

    print(
        "\n============================================================"
    )
    print(
        "P_308 - OFFLINE / COMPONENT TEST SUITE"
    )
    print(
        "============================================================"
    )

    passed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []

    for test_name in KNOWN_TESTS:

        path = (
            TEST_DIR / test_name
        )

        if not path.exists():

            print(
                f"\n⚠️ SKIP {test_name} "
                "(file not present)"
            )

            skipped.append(
                test_name
            )

            continue

        print(
            f"\n▶ Running {test_name}"
        )

        result = subprocess.run(
            [
                sys.executable,
                str(path),
            ],
            cwd=PROJECT_ROOT,
            text=True,
        )

        if result.returncode == 0:

            print(
                f"✅ PASS {test_name}"
            )

            passed.append(
                test_name
            )

        else:

            print(
                f"❌ FAIL {test_name}"
            )

            failed.append(
                test_name
            )

    print(
        "\n============================================================"
    )
    print(
        "TEST SUMMARY"
    )
    print(
        "============================================================"
    )

    print(
        f"Passed : {len(passed)}"
    )
    print(
        f"Failed : {len(failed)}"
    )
    print(
        f"Skipped: {len(skipped)}"
    )

    if failed:

        print(
            "\nFailed tests:"
        )

        for name in failed:
            print(
                f"  - {name}"
            )

        raise SystemExit(
            1
        )

    print(
        "\n✅ ALL AVAILABLE COMPONENT TESTS PASSED"
    )


if __name__ == "__main__":
    main()
