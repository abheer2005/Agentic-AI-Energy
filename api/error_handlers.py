from __future__ import annotations

import uuid

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.exceptions import (
    RequestValidationError,
)
from fastapi.responses import (
    JSONResponse,
)

from core.logging_config import (
    get_logger,
)


logger = get_logger(
    __name__
)


def register_exception_handlers(
    app: FastAPI,
) -> None:

    @app.exception_handler(
        RequestValidationError
    )
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ):

        request_id = uuid.uuid4().hex[
            :12
        ]

        logger.warning(
            "Request validation error request_id=%s method=%s path=%s errors=%s",
            request_id,
            request.method,
            request.url.path,
            exc.errors(),
        )

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "type": (
                        "request_validation_error"
                    ),
                    "message": (
                        "Request validation failed."
                    ),
                    "request_id": (
                        request_id
                    ),
                    "details": (
                        exc.errors()
                    ),
                },
            },
        )

    @app.exception_handler(
        Exception
    )
    async def unhandled_error_handler(
        request: Request,
        exc: Exception,
    ):

        request_id = uuid.uuid4().hex[
            :12
        ]

        logger.exception(
            "Unhandled API exception request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "type": (
                        "internal_server_error"
                    ),
                    "message": (
                        "Unexpected server error."
                    ),
                    "request_id": (
                        request_id
                    ),
                },
            },
        )
