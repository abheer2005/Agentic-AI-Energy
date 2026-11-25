from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.responses import (
    RedirectResponse,
)
from fastapi.staticfiles import (
    StaticFiles,
)

from api.error_handlers import (
    register_exception_handlers,
)
from api.live_state import (
    api_live_state,
)
from api.mqtt_bridge import (
    mqtt_api_bridge,
)
from api.routes import router
from api.websocket_manager import (
    websocket_manager,
)
from config.api_config import (
    API_TITLE,
    API_VERSION,
    CORS_ORIGINS,
)
from config.runtime_config import (
    DASHBOARD_DIR,
    ensure_runtime_directories,
)
from core.logging_config import (
    configure_logging,
    get_logger,
)
from core.metrics import (
    API_REQUEST_LATENCY_SECONDS,
    API_REQUESTS_TOTAL,
    WEBSOCKET_CLIENTS,
)


ensure_runtime_directories()
configure_logging()

logger = get_logger(
    __name__
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
):

    event_loop = (
        asyncio.get_running_loop()
    )

    logger.info(
        "Starting P_308 FastAPI backend"
    )

    mqtt_api_bridge.start(
        event_loop
    )

    try:
        yield

    finally:
        mqtt_api_bridge.stop()

        logger.info(
            "P_308 FastAPI backend stopped"
        )


app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=(
        "Real-time backend for the P_308 "
        "Agentic AI Energy Management Platform."
    ),
    lifespan=lifespan,
)


register_exception_handlers(
    app
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware(
    "http"
)
async def request_observability(
    request: Request,
    call_next,
):

    started = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(
            request
        )

        status_code = (
            response.status_code
        )

        return response

    finally:
        elapsed = (
            time.perf_counter()
            - started
        )

        API_REQUESTS_TOTAL.labels(
            method=request.method,
            path=request.url.path,
            status=str(
                status_code
            ),
        ).inc()

        API_REQUEST_LATENCY_SECONDS.labels(
            method=request.method,
            path=request.url.path,
        ).observe(
            elapsed
        )


app.include_router(
    router
)


if DASHBOARD_DIR.exists():

    app.mount(
        "/dashboard",
        StaticFiles(
            directory=DASHBOARD_DIR,
            html=True,
        ),
        name="dashboard",
    )


@app.get("/")
def root():

    if DASHBOARD_DIR.exists():
        return RedirectResponse(
            url="/dashboard/"
        )

    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": (
            "/api/v1/health"
        ),
        "websocket": (
            "/ws/live"
        ),
    }


@app.get(
    "/api-info"
)
def api_info() -> dict:

    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "status": "running",
        "dashboard": (
            "/dashboard/"
        ),
        "docs": "/docs",
        "health": (
            "/api/v1/health"
        ),
        "detailed_health": (
            "/api/v1/health/detailed"
        ),
        "readiness": (
            "/api/v1/ready"
        ),
        "system": (
            "/api/v1/system"
        ),
        "models": (
            "/api/v1/models"
        ),
        "metrics": (
            "/api/v1/metrics"
        ),
        "websocket": (
            "/ws/live"
        ),
    }


@app.websocket(
    "/ws/live"
)
async def live_websocket(
    websocket: WebSocket,
) -> None:

    connected = (
        await websocket_manager.connect(
            websocket
        )
    )

    WEBSOCKET_CLIENTS.set(
        websocket_manager.client_count
    )

    if not connected:
        return

    logger.info(
        "WebSocket client connected; clients=%s",
        websocket_manager.client_count,
    )

    try:

        await websocket.send_json(
            {
                "type": "snapshot",
                "payload": (
                    api_live_state.snapshot()
                ),
            }
        )

        while True:

            message = (
                await websocket.receive_text()
            )

            if (
                message.strip().lower()
                == "ping"
            ):
                await websocket.send_json(
                    {
                        "type": "pong"
                    }
                )

    except WebSocketDisconnect:
        pass

    except Exception:
        logger.exception(
            "WebSocket error"
        )

    finally:
        await websocket_manager.disconnect(
            websocket
        )

        WEBSOCKET_CLIENTS.set(
            websocket_manager.client_count
        )

        logger.info(
            "WebSocket client disconnected; clients=%s",
            websocket_manager.client_count,
        )
