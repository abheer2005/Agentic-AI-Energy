from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from config.llm_config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from llm.ollama_client import (
    LocalLLMError,
    OllamaClient,
)


def main() -> None:

    print(
        "\n🧠 P_308 Local LLM Check"
    )
    print(
        f"Endpoint : {OLLAMA_BASE_URL}"
    )
    print(
        f"Model    : {OLLAMA_MODEL}"
    )

    client = OllamaClient()

    try:
        status = client.health()

    except LocalLLMError as exc:
        print(
            "\n❌ Ollama is not reachable."
        )
        print(
            f"   {exc}"
        )
        print(
            "\nThe energy-control pipeline will still "
            "work because Step 4 has a deterministic fallback."
        )
        raise SystemExit(
            1
        )

    print(
        "\n✅ Ollama service reachable"
    )

    installed = status[
        "installed_models"
    ]

    if installed:
        print(
            "Installed models:"
        )
        for model in installed:
            print(
                f"  - {model}"
            )
    else:
        print(
            "No local models found."
        )

    if status[
        "configured_model_available"
    ]:
        print(
            f"\n✅ Configured model available: "
            f"{OLLAMA_MODEL}"
        )
    else:
        print(
            f"\n⚠️ Configured model not installed: "
            f"{OLLAMA_MODEL}"
        )
        print(
            f"Run: ollama pull {OLLAMA_MODEL}"
        )


if __name__ == "__main__":
    main()
