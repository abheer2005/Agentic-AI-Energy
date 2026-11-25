from __future__ import annotations

from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Response,
)
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)

from api.live_state import (
    api_live_state,
)
from api.mqtt_bridge import (
    mqtt_api_bridge,
)
from api.observability_service import (
    health_snapshot,
    model_snapshot,
    system_snapshot,
)
from api.schemas import (
    APIEnvelope,
    HealthResponse,
)
from api.websocket_manager import (
    websocket_manager,
)
from config.alert_config import (
    EVENT_DATABASE_NAME,
)
from config.api_config import (
    API_VERSION,
)
from config.observability_config import (
    PROMETHEUS_ENABLED,
)
from core.event_store import (
    SQLiteEventStore,
)


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

EVENT_DB_FILE = (
    PROJECT_ROOT
    / "data"
    / EVENT_DATABASE_NAME
)

event_store = SQLiteEventStore(
    EVENT_DB_FILE
)

router = APIRouter(
    prefix="/api/v1",
)


def _required_live(
    channel: str,
):

    value = api_live_state.get(
        channel
    )

    if value is None:
        raise HTTPException(
            status_code=503,
            detail=(
                f"No live {channel} data has "
                "been received from MQTT yet."
            ),
        )

    return value


@router.get(
    "/health",
    response_model=HealthResponse,
)
def health() -> HealthResponse:

    snapshot = (
        api_live_state.snapshot()
    )

    return HealthResponse(
        status="ok",
        api=API_VERSION,
        mqtt_connected=(
            mqtt_api_bridge.connected
        ),
        mqtt_last_error=(
            mqtt_api_bridge.last_error
        ),
        mqtt_last_message_at=(
            mqtt_api_bridge.last_message_at
        ),
        websocket_clients=(
            websocket_manager.client_count
        ),
        live_message_count=(
            snapshot[
                "message_count"
            ]
        ),
    )


@router.get(
    "/health/detailed",
    response_model=APIEnvelope,
)
def detailed_health() -> APIEnvelope:

    return APIEnvelope(
        data=health_snapshot()
    )


@router.get(
    "/ready",
)
def readiness() -> dict:

    health = (
        health_snapshot()
    )

    ready = (
        health["status"]
        in {
            "healthy",
            "degraded",
        }
    )

    if not ready:
        raise HTTPException(
            status_code=503,
            detail=health,
        )

    return {
        "ready": True,
        "status": (
            health["status"]
        ),
    }


@router.get(
    "/system",
    response_model=APIEnvelope,
)
def system_metrics() -> APIEnvelope:

    return APIEnvelope(
        data=system_snapshot()
    )


@router.get(
    "/models",
    response_model=APIEnvelope,
)
def model_metrics() -> APIEnvelope:

    return APIEnvelope(
        data=model_snapshot()
    )


@router.get(
    "/metrics",
)
def prometheus_metrics():

    if not PROMETHEUS_ENABLED:
        raise HTTPException(
            status_code=404,
            detail=(
                "Prometheus metrics disabled"
            ),
        )

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get(
    "/live",
    response_model=APIEnvelope,
)
def live_snapshot() -> APIEnvelope:

    return APIEnvelope(
        data=(
            api_live_state.snapshot()
        )
    )


@router.get(
    "/telemetry/latest",
    response_model=APIEnvelope,
)
def latest_telemetry() -> APIEnvelope:

    return APIEnvelope(
        data=_required_live(
            "telemetry"
        )
    )


@router.get(
    "/decision/latest",
    response_model=APIEnvelope,
)
def latest_decision() -> APIEnvelope:

    return APIEnvelope(
        data=_required_live(
            "decision"
        )
    )


@router.get(
    "/control/latest",
    response_model=APIEnvelope,
)
def latest_control() -> APIEnvelope:

    return APIEnvelope(
        data=_required_live(
            "control"
        )
    )


@router.get(
    "/operator-summary/latest",
    response_model=APIEnvelope,
)
def latest_operator_summary() -> APIEnvelope:

    return APIEnvelope(
        data=_required_live(
            "operator_summary"
        )
    )


@router.get(
    "/alert/latest",
    response_model=APIEnvelope,
)
def latest_alert() -> APIEnvelope:

    live_alert = (
        api_live_state.get(
            "alert"
        )
    )

    if live_alert is not None:
        return APIEnvelope(
            data=live_alert
        )

    stored = (
        event_store.latest_alerts(
            limit=1
        )
    )

    return APIEnvelope(
        data=(
            stored[0]
            if stored
            else None
        )
    )


@router.get(
    "/alerts",
    response_model=APIEnvelope,
)
def alert_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
) -> APIEnvelope:

    return APIEnvelope(
        data=(
            event_store.latest_alerts(
                limit=limit
            )
        )
    )


@router.get(
    "/events",
    response_model=APIEnvelope,
)
def event_history(
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> APIEnvelope:

    return APIEnvelope(
        data=(
            event_store.latest_events(
                limit=limit
            )
        )
    )


@router.get(
    "/history/counts",
    response_model=APIEnvelope,
)
def history_counts() -> APIEnvelope:

    return APIEnvelope(
        data=event_store.counts()
    )
