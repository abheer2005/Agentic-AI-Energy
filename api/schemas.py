from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class APIEnvelope(BaseModel):
    success: bool = True
    data: Any = None


class HealthResponse(BaseModel):
    status: str
    api: str
    mqtt_connected: bool
    mqtt_last_error: str | None = None
    mqtt_last_message_at: str | None = None
    websocket_clients: int
    live_message_count: int


class HistoryQuery(BaseModel):
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
    )
