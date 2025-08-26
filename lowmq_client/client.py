from __future__ import annotations

from typing import Any, Dict, Optional

import aiohttp
from pydantic import AnyUrl, TypeAdapter

from .exceptions import ApiError, ClientClosedError, InvalidUrlError

_URL_ADAPTER = TypeAdapter(AnyUrl)


class LowMqClient:
    """Asynchronous client for LowMQ API.

    Usage:
        async with LowMqClient(auth_key, base_url) as client:
            await client.add_packet("queue", {"k": "v"})
    """

    def __init__(
        self,
        auth_key: str,
        lowmq_url: str | AnyUrl,
        *,
        session: Optional[aiohttp.ClientSession] = None,
        timeout: Optional[aiohttp.ClientTimeout] = None,
    ) -> None:
        self.auth_key: str = auth_key
        self.lowmq_url: str = self._validate_url(lowmq_url)
        self._external_session: Optional[aiohttp.ClientSession] = session
        self.session: Optional[aiohttp.ClientSession] = session
        self._timeout = timeout or aiohttp.ClientTimeout(total=30)

    @staticmethod
    def _validate_url(url: str | AnyUrl) -> str:
        try:
            # Validate and normalize URL using Pydantic AnyUrl
            parsed = _URL_ADAPTER.validate_python(url)
            return str(parsed)
        except Exception as exc:
            raise InvalidUrlError(url) from exc

    async def __aenter__(self) -> "LowMqClient":
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.session and self._external_session is None:
            await self.session.close()
        self.session = self._external_session

    async def set_auth_key(self, auth_key: str) -> None:
        self.auth_key = auth_key

    async def set_lowmq_url(self, lowmq_url: str | AnyUrl) -> None:
        self.lowmq_url = self._validate_url(lowmq_url)

    # --------------------- Public API ---------------------
    async def add_packet(
        self,
        queue_name: str,
        payload: Any,
        freeze_time_min: int = 5,
    ) -> Dict[str, Any]:
        """Add a message to queue. Raises ApiError on HTTP error."""
        url = f"{self.lowmq_url}/msg?freezeTimeMin={int(freeze_time_min)}"
        data: Dict[str, Any] = {"key": queue_name, "value": payload}
        async with self._request("POST", url, json=data) as resp:
            await self._raise_for_status(resp)
            return await self._safe_json(resp)

    async def get_packet(self, queue_name: str, delete: bool = False) -> Dict[str, Any]:
        """Get a message. Optionally delete it on retrieval. Raises ApiError on error."""
        url = f"{self.lowmq_url}/msg?key={queue_name}&delete={str(delete).lower()}"
        async with self._request("GET", url) as resp:
            await self._raise_for_status(resp)
            return await self._safe_json(resp)

    async def delete_packet(self, queue_name: str, packet_id: str) -> bool:
        """Delete a message by id. Returns True on 2xx, False otherwise."""
        url = f"{self.lowmq_url}/msg?key={queue_name}&_id={packet_id}"
        async with self._request("DELETE", url) as resp:
            return 200 <= resp.status < 300

    # --------------------- Internals ---------------------
    def _require_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            raise ClientClosedError(
                "Client session is not initialized. Use 'async with' or pass a session."
            )
        if getattr(self.session, "closed", False):
            raise ClientClosedError("Client session is closed.")
        return self.session

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"token {self.auth_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs: Any):
        session = self._require_session()
        headers = kwargs.pop("headers", None) or self._headers()
        return session.request(method, url, headers=headers, **kwargs)

    @staticmethod
    async def _safe_json(resp: aiohttp.ClientResponse) -> Dict[str, Any]:
        try:
            # Don't enforce content type; server might not set it
            return await resp.json(content_type=None)
        except Exception:
            text = await resp.text()
            return {"raw": text}

    @staticmethod
    async def _raise_for_status(resp: aiohttp.ClientResponse) -> None:
        if 200 <= resp.status < 300:
            return
        body: Any
        try:
            body = await resp.json(content_type=None)
        except Exception:
            body = await resp.text()
        raise ApiError(status=resp.status, reason=resp.reason or "", body=body)
