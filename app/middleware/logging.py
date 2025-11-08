"""Request/response logging middleware."""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import LoggerAdapter
from app.middleware.request_id import get_request_id

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with logging."""
        request_id = get_request_id()
        adapter = LoggerAdapter(logger, {"request_id": request_id})

        # Log request
        adapter.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            },
        )

        # Process request and measure time
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = time.time() - start_time

        # Log response
        adapter.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": f"{process_time:.3f}s",
            },
        )

        # Add process time header
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response
