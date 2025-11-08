"""Logging configuration."""

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging."""
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Configure formatter
    formatter: logging.Formatter
    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)


class LoggerAdapter(logging.LoggerAdapter[logging.Logger]):
    """Logger adapter to add request_id to log records."""

    def process(
        self, msg: str, kwargs: MutableMapping[str, Any]
    ) -> tuple[str, MutableMapping[str, Any]]:
        """Process log message with additional context."""
        extra = kwargs.get("extra", {})
        if isinstance(extra, dict):
            extra["request_id"] = self.extra.get("request_id", "N/A") if self.extra else "N/A"
            kwargs["extra"] = extra
        return msg, kwargs
