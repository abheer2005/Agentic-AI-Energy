from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel, Field


class LLMOperatorContent(BaseModel):
    """
    Strict structured content produced by the local LLM.
    The schema intentionally contains NO actuator/control fields.
    """

    headline: str = Field(
        min_length=3,
        max_length=140,
    )

    situation: str = Field(
        min_length=3,
        max_length=700,
    )

    why: str = Field(
        min_length=3,
        max_length=700,
    )

    operator_actions: list[str] = Field(
        default_factory=list,
        max_length=3,
    )

    risks: list[str] = Field(
        default_factory=list,
        max_length=3,
    )

    confidence_note: str = Field(
        min_length=3,
        max_length=300,
    )


@dataclass
class OperatorSummary:
    headline: str
    situation: str
    why: str
    operator_actions: list[str]
    risks: list[str]
    confidence_note: str

    source: str
    model: str
    generated_at: str
    latency_ms: float
    fresh: bool
    trigger: str
    fallback_used: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
