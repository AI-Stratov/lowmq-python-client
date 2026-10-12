from __future__ import annotations

import unittest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp

from lowmq_client import LowMqClient
from lowmq_client.exceptions import ApiError, ClientClosedError, InvalidUrlError


class StubResponse:
    def __init__(
        self,
        status: int = 200,
        reason: str = "OK",
        json_data: Optional[Dict[str, Any]] = None,
        text_data: str = "",
        json_error: bool = False,
    ) -> None:
        self.status = status
        self.reason = reason
        self._json_data = json_data or {}
        self._text_data = text_data
        self._json_error = json_error

    async def __aenter__(self) -> "StubResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def json(self, content_type: Optional[str] = None) -> Dict[str, Any]:
        if self._json_error:
            raise ValueError("not JSON")
        return self._json_data

    async def text(self) -> str:
        return self._text_data


def make_session(response: StubResponse) -> MagicMock:
    session = MagicMock()
    session.closed = False
    session.request = MagicMock(return_value=response)
    return session


class LowMqClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_add_packet_success(self) -> None:
        session = make_session(StubResponse(status=200, json_data={"ok": True}))

        async with LowMqClient("k", "https://example.com", session=session) as client:
            res = await client.add_packet("q", {"a": 1})
        self.assertEqual(res, {"ok": True})

        session.request.assert_called()
        args, kwargs = session.request.call_args
        self.assertEqual(args[0], "POST")
        self.assertIn("/msg?freezeTimeMin=5", args[1])
        self.assertEqual(kwargs["json"], {"key": "q", "value": {"a": 1}})
        self.assertEqual(kwargs["headers"]["Authorization"], "token k")

    async def test_add_packet_custom_freeze_time(self) -> None:
        session = make_session(StubResponse())

        async with LowMqClient("k", "https://example.com", session=session) as client:
            await client.add_packet("q", {}, freeze_time_min=10)

        args, _ = session.request.call_args
        self.assertIn("freezeTimeMin=10", args[1])

    async def test_get_packet_delete_true(self) -> None:
        session = make_session(StubResponse(status=200, json_data={"_id": "1", "value": 42}))

        async with LowMqClient("k", "https://example.com", session=session) as client:
            res = await client.get_packet("q", delete=True)
        self.assertEqual(res["_id"], "1")

        args, _ = session.request.call_args
        self.assertEqual(args[0], "GET")
        self.assertIn("key=q", args[1])
        self.assertIn("delete=true", args[1])

    async def test_get_packet_keeps_message_by_default(self) -> None:
        session = make_session(StubResponse())

        async with LowMqClient("k", "https://example.com", session=session) as client:
            await client.get_packet("q")

        args, _ = session.request.call_args
        self.assertIn("delete=false", args[1])

    async def test_non_json_body_returned_as_raw(self) -> None:
        session = make_session(StubResponse(text_data="plain text", json_error=True))

        async with LowMqClient("k", "https://example.com", session=session) as client:
            res = await client.get_packet("q")
        self.assertEqual(res, {"raw": "plain text"})

    async def test_delete_packet_status_handling(self) -> None:
        session = make_session(StubResponse(status=204))
        async with LowMqClient("k", "https://example.com", session=session) as client:
            ok = await client.delete_packet("q", "id1")
        self.assertTrue(ok)

        args, _ = session.request.call_args
        self.assertEqual(args[0], "DELETE")
        self.assertIn("key=q", args[1])
        self.assertIn("_id=id1", args[1])

        session = make_session(StubResponse(status=500, reason="err"))
        async with LowMqClient("k", "https://example.com", session=session) as client:
            ok2 = await client.delete_packet("q", "id2")
        self.assertFalse(ok2)

    async def test_api_error_on_non_2xx(self) -> None:
        session = make_session(StubResponse(status=400, reason="Bad", json_data={"detail": "bad"}))

        async with LowMqClient("k", "https://example.com", session=session) as client:
            with self.assertRaises(ApiError) as ctx:
                await client.add_packet("q", {})
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(ctx.exception.reason, "Bad")
        self.assertEqual(ctx.exception.body, {"detail": "bad"})

    async def test_api_error_with_text_body(self) -> None:
        session = make_session(
            StubResponse(status=404, reason="Not Found", text_data="no messages", json_error=True)
        )

        async with LowMqClient("k", "https://example.com", session=session) as client:
            with self.assertRaises(ApiError) as ctx:
                await client.get_packet("q")
        self.assertEqual(ctx.exception.status, 404)
        self.assertEqual(ctx.exception.body, "no messages")

    async def test_invalid_url(self) -> None:
        with self.assertRaises(InvalidUrlError):
            _ = LowMqClient("k", "not-a-url")

    async def test_setters(self) -> None:
        session = make_session(StubResponse())
        client = LowMqClient("k", "https://example.com", session=session)

        await client.set_auth_key("k2")
        await client.set_lowmq_url("https://other.example")
        await client.get_packet("q")

        args, kwargs = session.request.call_args
        self.assertTrue(args[1].startswith("https://other.example"))
        self.assertEqual(kwargs["headers"]["Authorization"], "token k2")

        with self.assertRaises(InvalidUrlError):
            await client.set_lowmq_url("not-a-url")

    async def test_client_closed_error(self) -> None:
        client = LowMqClient("k", "https://example.com")
        with self.assertRaises(ClientClosedError):
            await client.add_packet("q", {})

    async def test_closed_external_session(self) -> None:
        session = make_session(StubResponse())
        session.closed = True
        client = LowMqClient("k", "https://example.com", session=session)
        with self.assertRaises(ClientClosedError):
            await client.get_packet("q")

    async def test_external_session_is_not_closed(self) -> None:
        session = make_session(StubResponse())
        session.close = AsyncMock()

        async with LowMqClient("k", "https://example.com", session=session):
            pass

        session.close.assert_not_called()

    async def test_own_session_uses_timeout_and_is_closed(self) -> None:
        timeout = aiohttp.ClientTimeout(total=10)
        with patch("lowmq_client.client.aiohttp.ClientSession") as session_cls:
            session_cls.return_value.close = AsyncMock()
            client = LowMqClient("k", "https://example.com", timeout=timeout)
            async with client:
                pass

        session_cls.assert_called_once_with(timeout=timeout)
        session_cls.return_value.close.assert_awaited_once()
        self.assertIsNone(client.session)

    async def test_default_timeout(self) -> None:
        with patch("lowmq_client.client.aiohttp.ClientSession") as session_cls:
            session_cls.return_value.close = AsyncMock()
            async with LowMqClient("k", "https://example.com"):
                pass

        _, kwargs = session_cls.call_args
        self.assertEqual(kwargs["timeout"].total, 30)


if __name__ == "__main__":
    unittest.main()
