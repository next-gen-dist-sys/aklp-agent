"""Global error handler middleware."""

import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.core.logging import LoggerAdapter
from app.middleware.request_id import get_request_id

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    request_id = get_request_id()
    adapter = LoggerAdapter(logger, {"request_id": request_id})

    adapter.error(
        f"Application error: {exc.message}",
        extra={
            "error_type": exc.__class__.__name__,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_code": exc.__class__.__name__,
            "details": exc.details,
            "request_id": request_id,
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors."""
    request_id = get_request_id()
    adapter = LoggerAdapter(logger, {"request_id": request_id})

    errors = exc.errors()
    adapter.warning(
        "Validation error",
        extra={"validation_errors": errors},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "error_code": "ValidationError",
            "details": {"validation_errors": errors},
            "request_id": request_id,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    request_id = get_request_id()
    adapter = LoggerAdapter(logger, {"request_id": request_id})

    adapter.warning(
        f"HTTP error: {exc.detail}",
        extra={"status_code": exc.status_code},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": "HTTPException",
            "details": {},
            "request_id": request_id,
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions."""
    request_id = get_request_id()
    adapter = LoggerAdapter(logger, {"request_id": request_id})

    adapter.exception(
        "Unhandled exception",
        exc_info=exc,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "InternalServerError",
            "details": {},
            "request_id": request_id,
        },
    )
