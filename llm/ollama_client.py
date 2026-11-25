from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from config.llm_config import (
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
)


class LocalLLMError(RuntimeError):
    pass


class LocalLLMUnavailable(LocalLLMError):
    pass


class LocalLLMResponseError(LocalLLMError):
    pass


@dataclass
class OllamaResponse:
    content: str
    model: str


class OllamaClient:
    """
    Minimal Ollama REST client using Python stdlib only.
    No additional Python package is required.
    """

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout_seconds: float = LLM_TIMEOUT_SECONDS,
        temperature: float = LLM_TEMPERATURE,
    ) -> None:

        self.base_url = base_url.rstrip(
            "/"
        )
        self.model = model
        self.timeout_seconds = (
            timeout_seconds
        )
        self.temperature = (
            temperature
        )

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> OllamaResponse:

        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "options": {
                "temperature": (
                    self.temperature
                ),
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        system_prompt
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        user_prompt
                    ),
                },
            ],
        }

        response = self._post_json(
            "/api/chat",
            payload,
        )

        try:
            content = response[
                "message"
            ]["content"]
        except (
            KeyError,
            TypeError,
        ) as exc:
            raise LocalLLMResponseError(
                "Ollama response did not contain "
                "message.content."
            ) from exc

        if not isinstance(
            content,
            str,
        ) or not content.strip():
            raise LocalLLMResponseError(
                "Ollama returned an empty response."
            )

        return OllamaResponse(
            content=content.strip(),
            model=str(
                response.get(
                    "model",
                    self.model,
                )
            ),
        )

    def health(
        self,
    ) -> dict[str, Any]:

        response = self._get_json(
            "/api/tags"
        )

        models = []

        for item in response.get(
            "models",
            [],
        ):
            name = item.get(
                "name"
            )
            if name:
                models.append(
                    str(name)
                )

        return {
            "reachable": True,
            "configured_model": self.model,
            "installed_models": models,
            "configured_model_available": (
                self.model in models
                or any(
                    model.startswith(
                        f"{self.model}:"
                    )
                    for model in models
                )
            ),
        }

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        request = urllib.request.Request(
            url=(
                f"{self.base_url}{path}"
            ),
            data=json.dumps(
                payload
            ).encode(
                "utf-8"
            ),
            headers={
                "Content-Type": (
                    "application/json"
                ),
            },
            method="POST",
        )

        return self._execute(
            request
        )

    def _get_json(
        self,
        path: str,
    ) -> dict[str, Any]:

        request = urllib.request.Request(
            url=(
                f"{self.base_url}{path}"
            ),
            method="GET",
        )

        return self._execute(
            request
        )

    def _execute(
        self,
        request: urllib.request.Request,
    ) -> dict[str, Any]:

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read().decode(
                    "utf-8"
                )

        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode(
                    "utf-8"
                )
            except Exception:
                detail = str(
                    exc
                )

            raise LocalLLMResponseError(
                f"Ollama HTTP error "
                f"{exc.code}: {detail}"
            ) from exc

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            OSError,
        ) as exc:
            raise LocalLLMUnavailable(
                "Local Ollama service is unavailable "
                f"at {self.base_url}: {exc}"
            ) from exc

        try:
            parsed = json.loads(
                raw
            )
        except json.JSONDecodeError as exc:
            raise LocalLLMResponseError(
                "Ollama returned invalid JSON."
            ) from exc

        if not isinstance(
            parsed,
            dict,
        ):
            raise LocalLLMResponseError(
                "Unexpected Ollama response type."
            )

        return parsed
