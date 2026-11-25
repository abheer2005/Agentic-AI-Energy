from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config.observability_config import (
    LOG_BACKUP_COUNT,
    LOG_DIR,
    LOG_FILE_NAME,
    LOG_LEVEL,
    LOG_MAX_BYTES,
)


_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED

    if _CONFIGURED:
        return

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    formatter = logging.Formatter(
        (
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        )
    )

    root = logging.getLogger()
    root.setLevel(
        getattr(
            logging,
            LOG_LEVEL,
            logging.INFO,
        )
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        formatter
    )

    file_handler = RotatingFileHandler(
        LOG_DIR / LOG_FILE_NAME,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        formatter
    )

    root.handlers.clear()
    root.addHandler(
        console_handler
    )
    root.addHandler(
        file_handler
    )

    _CONFIGURED = True


def get_logger(
    name: str,
) -> logging.Logger:

    configure_logging()
    return logging.getLogger(
        name
    )
