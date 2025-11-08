"""HTTP client wrapper using httpx."""

import logging
from typing import Any

import httpx

from app.core.logging import LoggerAdapter
from app.middleware.request_id import get_request_id

logger = logging.getLogger(__name__)


class HTTPClient:
    """Async HTTP client wrapper."""

    def __init__(self, base_url: str = "", timeout: float = 30.0) -> None:
        """Initialize HTTP client."""
        self.base_url = base_url
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HTTPClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform GET request."""
        return await self._request("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform POST request."""
        return await self._request("POST", url, json=json, headers=headers)

    async def put(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform PUT request."""
        return await self._request("PUT", url, json=json, headers=headers)

    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform DELETE request."""
        return await self._request("DELETE", url, headers=headers)

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Perform HTTP request with logging."""
        if not self._client:
            raise RuntimeError("HTTP client not initialized. Use 'async with' context manager.")

        # Add request ID to headers
        request_id = get_request_id()
        if headers is None:
            headers = {}
        headers["X-Request-ID"] = request_id

        adapter = LoggerAdapter(logger, {"request_id": request_id})

        adapter.debug(
            f"HTTP request: {method} {url}",
            extra={"method": method, "url": url, "params": params},
        )

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=headers,
            )

            adapter.debug(
                f"HTTP response: {method} {url} - {response.status_code}",
                extra={"method": method, "url": url, "status_code": response.status_code},
            )

            return response

        except httpx.HTTPError as e:
            adapter.error(
                f"HTTP error: {method} {url}",
                extra={"method": method, "url": url, "error": str(e)},
            )
            raise
