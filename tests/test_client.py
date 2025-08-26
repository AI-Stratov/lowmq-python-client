from __future__ import annotations

import unittest
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

from lowmq_client import LowMqClient
from lowmq_client.exceptions import ApiError, ClientClosedError, InvalidUrlError


class StubResponse:
    def __init__(
        self,
        status: int = 200,
        reason: str = "OK",
        json_data: Optional[Dict[str, Any]] = None,
        text_data: str = "",
    ) -> None:
        self.status = status
        self.reason = reason
        self._json_data = json_data or {}
        self._text_data = text_data

    async def __aenter__(self) -> "StubResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def json(self, content_type: Optional[str] = None) -> Dict[str, Any]:
        return self._json_data

    async def text(self) -> str:
        return self._text_data


class LowMqClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_packet_success(self) -> None:
        session = MagicMock()
        session.closed = False
        stub = StubResponse(status=200, json_data={"ok": True})
        session.request = MagicMock(return_value=stub)

        async with LowMqClient("k", "https://example.com", session=session) as client:
            res = await client.add_packet("q", {"a": 1})
        self.assertEqual(res, {"ok": True})

        session.request.assert_called()
        args, kwargs = session.request.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("/msg?freezeTimeMin=5", args[1])
        self.assertEqual(kwargs["json"], {"key": "q", "value": {"a": 1}})
        self.assertIn("Authorization", kwargs["headers"])  # token header present

    async def test_get_packet_delete_true(self) -> None:
        session = MagicMock()
        session.closed = False
        stub = StubResponse(status=200, json_data={"_id": "1", "value": 42})
        session.request = MagicMock(return_value=stub)

        async with LowMqClient("k", "https://example.com", session=session) as client:
            res = await client.get_packet("q", delete=True)
        self.assertEqual(res["_id"], "1")

        args, _ = session.request.call_args
        self.assertEqual(args[0], "GET")
        self.assertIn("delete=true", args[1])

    async def test_delete_packet_status_handling(self) -> None:
        session = MagicMock()
        session.closed = False

        # success
        session.request = MagicMock(return_value=StubResponse(status=204))
        async with LowMqClient("k", "https://example.com", session=session) as client:
            ok = await client.delete_packet("q", "id1")
        self.assertTrue(ok)

        # failure
        session.request = MagicMock(return_value=StubResponse(status=500, reason="err"))
        async with LowMqClient("k", "https://example.com", session=session) as client:
            ok2 = await client.delete_packet("q", "id2")
        self.assertFalse(ok2)

    async def test_api_error_on_non_2xx(self) -> None:
        session = MagicMock()
        session.closed = False
        session.request = MagicMock(
            return_value=StubResponse(status=400, reason="Bad", json_data={"detail": "bad"})
        )

        async with LowMqClient("k", "https://example.com", session=session) as client:
            with self.assertRaises(ApiError) as ctx:
                await client.add_packet("q", {})
        self.assertEqual(ctx.exception.status, 400)

    async def test_invalid_url(self) -> None:
        with self.assertRaises(InvalidUrlError):
            _ = LowMqClient("k", "not-a-url")

    async def test_client_closed_error(self) -> None:
        client = LowMqClient("k", "https://example.com")
        with self.assertRaises(ClientClosedError):
            await client.add_packet("q", {})


if __name__ == "__main__":
    unittest.main()
