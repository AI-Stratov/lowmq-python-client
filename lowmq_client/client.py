from __future__ import annotations

import json
from types import TracebackType
from typing import Any

import aiohttp
from pydantic import AnyUrl, HttpUrl, TypeAdapter, ValidationError

from .exceptions import ApiError, ClientClosedError, InvalidUrlError

_URL_ADAPTER: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)
_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30)


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
        session: aiohttp.ClientSession | None = None,
        timeout: aiohttp.ClientTimeout | None = None,
    ) -> None:
        self.auth_key: str = auth_key
        self.lowmq_url: str = self._validate_url(lowmq_url)
        self._external_session = session
        self.session: aiohttp.ClientSession | None = session
        self._timeout = timeout or _DEFAULT_TIMEOUT

    @staticmethod
    def _validate_url(url: str | AnyUrl) -> str:
        try:
            return str(_URL_ADAPTER.validate_python(str(url)))
        except ValidationError as exc:
            raise InvalidUrlError(url) from exc

    async def __aenter__(self) -> LowMqClient:
        if self.session is None:
            self.session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.session is not None and self._external_session is None:
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
    ) -> dict[str, Any]:
        """Add a message to a queue. Raises ApiError on a non-2xx response."""
        status, reason, text = await self._call(
            "POST",
            params={"freezeTimeMin": int(freeze_time_min)},
            body={"key": queue_name, "value": payload},
        )
        return _result(status, reason, text)

    async def get_packet(self, queue_name: str, delete: bool = False) -> dict[str, Any]:
        """Get a message, optionally deleting it. Raises ApiError on a non-2xx response."""
        status, reason, text = await self._call(
            "GET",
            params={"key": queue_name, "delete": "true" if delete else "false"},
        )
        return _result(status, reason, text)

    async def delete_packet(self, queue_name: str, packet_id: str) -> bool:
        """Delete a message by id. Returns True on 2xx, False otherwise."""
        status, _, _ = await self._call("DELETE", params={"key": queue_name, "_id": packet_id})
        return _is_success(status)

    # --------------------- Internals ---------------------
    def _require_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            raise ClientClosedError(
                "Client session is not initialized. Use 'async with' or pass a session."
            )
        if self.session.closed:
            raise ClientClosedError("Client session is closed.")
        return self.session

    async def _call(
        self,
        method: str,
        params: dict[str, str | int],
        body: dict[str, Any] | None = None,
    ) -> tuple[int, str, str]:
        """Send a request to the /msg endpoint and return status, reason and body text."""
        session = self._require_session()
        async with session.request(
            method,
            f"{self.lowmq_url.rstrip('/')}/msg",
            params=params,
            json=body,
            headers={"Authorization": f"token {self.auth_key}"},
        ) as resp:
            text = await resp.text(errors="replace")
            return resp.status, resp.reason or "", text


def _is_success(status: int) -> bool:
    return 200 <= status < 300


def _result(status: int, reason: str, text: str) -> dict[str, Any]:
    """Return the parsed body of a 2xx response, or raise ApiError."""
    if not _is_success(status):
        try:
            error_body: Any = json.loads(text)
        except ValueError:
            error_body = text or None
        raise ApiError(status=status, reason=reason, body=error_body)
    try:
        result: dict[str, Any] = json.loads(text)
    except ValueError:
        return {"raw": text}
    return result
