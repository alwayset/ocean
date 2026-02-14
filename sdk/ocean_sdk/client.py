"""Ocean SDK client — one-line tool discovery for AI agents."""

from __future__ import annotations

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"

_default_client: OceanClient | None = None


class OceanClient:
    """Client for the Ocean tool discovery API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self._headers = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def discover(
        self,
        intent: str,
        *,
        protocol: str | None = None,
        min_reliability: float | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Find tools matching a natural language intent.

        >>> tools = client.discover("send an email to a customer")
        >>> tools[0]["name"]
        'send_email'
        """
        payload: dict = {"intent": intent, "limit": limit}
        constraints = {}
        if protocol:
            constraints["protocol"] = protocol
        if min_reliability is not None:
            constraints["min_reliability"] = min_reliability
        if constraints:
            payload["constraints"] = constraints

        resp = httpx.post(
            f"{self.base_url}/v1/discover",
            json=payload,
            headers=self._headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["results"]

    def tool_info(self, tool_id: str) -> dict:
        """Get full details for a specific tool by ID."""
        resp = httpx.get(
            f"{self.base_url}/v1/tools/{tool_id}",
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def list_tools(
        self, *, page: int = 1, page_size: int = 20, protocol: str | None = None
    ) -> dict:
        """List all indexed tools with pagination."""
        params: dict = {"page": page, "page_size": page_size}
        if protocol:
            params["protocol"] = protocol
        resp = httpx.get(
            f"{self.base_url}/v1/tools",
            params=params,
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def stats(self) -> dict:
        """Get index statistics."""
        resp = httpx.get(
            f"{self.base_url}/v1/stats",
            headers=self._headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


def _get_default_client() -> OceanClient:
    global _default_client
    if _default_client is None:
        _default_client = OceanClient()
    return _default_client


def discover(intent: str, **kwargs) -> list[dict]:
    """One-line tool discovery.

    >>> import ocean_sdk
    >>> tools = ocean_sdk.discover("send email to customer")
    >>> tools[0]["name"]
    'send_email'
    """
    return _get_default_client().discover(intent, **kwargs)


def tool_info(tool_id: str) -> dict:
    """Get tool details by ID."""
    return _get_default_client().tool_info(tool_id)


def list_tools(**kwargs) -> dict:
    """List all indexed tools."""
    return _get_default_client().list_tools(**kwargs)


def stats() -> dict:
    """Get index statistics."""
    return _get_default_client().stats()
