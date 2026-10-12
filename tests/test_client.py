from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

import aiohttp
from aiohttp import web
from aiohttp.test_utils import TestServer

from lowmq_client import LowMqClient
from lowmq_client.exceptions import ApiError, ClientClosedError, InvalidUrlError


@dataclass
class Reply:
    status: int = 200
    body: str = "{}"
    content_type: str = "application/json"


@dataclass
class Received:
    method: str
    path: str
    query: dict[str, str]
    headers: dict[str, str]
    body: str


class FakeLowMq:
    """In-process HTTP server that records requests and returns a preset reply."""

    def __init__(self) -> None:
        self.reply = Reply()
        self.requests: list[Received] = []
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self._handle)
        self.server = TestServer(app)

    async def _handle(self, request: web.Request) -> web.Response:
        self.requests.append(
            Received(
                method=request.method,
                path=request.path,
                query=dict(request.query),
                headers=dict(request.headers),
                body=await request.text(),
            )
        )
        return web.Response(
            status=self.reply.status,
            text=self.reply.body,
            content_type=self.reply.content_type,
        )

    @property
    def url(self) -> str:
        return str(self.server.make_url("/"))

    @property
    def last(self) -> Received:
        return self.requests[-1]


class LowMqClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.lowmq = FakeLowMq()
        await self.lowmq.server.start_server()
        self.addAsyncCleanup(self.lowmq.server.close)

    def client(self, **kwargs: Any) -> LowMqClient:
        return LowMqClient("secret", self.lowmq.url, **kwargs)

    async def test_add_packet(self) -> None:
        self.lowmq.reply = Reply(body='{"_id": "1"}')

        async with self.client() as client:
            result = await client.add_packet("payments", {"amount": 100})

        self.assertEqual(result, {"_id": "1"})
        request = self.lowmq.last
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, "/msg")
        self.assertEqual(request.query, {"freezeTimeMin": "5"})
        self.assertEqual(request.headers["Authorization"], "token secret")
        self.assertEqual(request.headers["Content-Type"], "application/json")
        self.assertEqual(request.body, '{"key": "payments", "value": {"amount": 100}}')

    async def test_add_packet_freeze_time(self) -> None:
        async with self.client() as client:
            await client.add_packet("q", {}, freeze_time_min=10)

        self.assertEqual(self.lowmq.last.query, {"freezeTimeMin": "10"})

    async def test_get_packet(self) -> None:
        self.lowmq.reply = Reply(body='{"_id": "1", "key": "q", "value": 42}')

        async with self.client() as client:
            result = await client.get_packet("q")

        self.assertEqual(result, {"_id": "1", "key": "q", "value": 42})
        self.assertEqual(self.lowmq.last.method, "GET")
        self.assertEqual(self.lowmq.last.path, "/msg")
        self.assertEqual(self.lowmq.last.query, {"key": "q", "delete": "false"})

    async def test_get_packet_delete(self) -> None:
        async with self.client() as client:
            await client.get_packet("q", delete=True)

        self.assertEqual(self.lowmq.last.query, {"key": "q", "delete": "true"})

    async def test_query_values_are_encoded(self) -> None:
        async with self.client() as client:
            await client.get_packet("a&b c?d#e")
            await client.delete_packet("a&b", "id/1?x")

        self.assertEqual(self.lowmq.requests[0].query, {"key": "a&b c?d#e", "delete": "false"})
        self.assertEqual(self.lowmq.requests[1].query, {"key": "a&b", "_id": "id/1?x"})

    async def test_base_url_with_path(self) -> None:
        for base in ("api", "api/"):
            async with LowMqClient("secret", self.lowmq.url + base) as client:
                await client.get_packet("q")
            self.assertEqual(self.lowmq.last.path, "/api/msg")

    async def test_non_json_body_returned_as_raw(self) -> None:
        self.lowmq.reply = Reply(body="plain text", content_type="text/plain")

        async with self.client() as client:
            result = await client.get_packet("q")

        self.assertEqual(result, {"raw": "plain text"})

    async def test_empty_body_returned_as_raw(self) -> None:
        self.lowmq.reply = Reply(body="", content_type="text/plain")

        async with self.client() as client:
            result = await client.add_packet("q", {})

        self.assertEqual(result, {"raw": ""})

    async def test_delete_packet(self) -> None:
        self.lowmq.reply = Reply(status=204, body="")

        async with self.client() as client:
            deleted = await client.delete_packet("q", "id1")

        self.assertTrue(deleted)
        self.assertEqual(self.lowmq.last.method, "DELETE")
        self.assertEqual(self.lowmq.last.path, "/msg")
        self.assertEqual(self.lowmq.last.query, {"key": "q", "_id": "id1"})

    async def test_delete_packet_failure_returns_false(self) -> None:
        self.lowmq.reply = Reply(status=500)

        async with self.client() as client:
            self.assertFalse(await client.delete_packet("q", "id1"))

    async def test_api_error_with_json_body(self) -> None:
        self.lowmq.reply = Reply(status=400, body='{"detail": "bad"}')

        async with self.client() as client:
            with self.assertRaises(ApiError) as ctx:
                await client.add_packet("q", {})

        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(ctx.exception.reason, "Bad Request")
        self.assertEqual(ctx.exception.body, {"detail": "bad"})

    async def test_api_error_with_text_body(self) -> None:
        self.lowmq.reply = Reply(status=404, body="no messages", content_type="text/plain")

        async with self.client() as client:
            with self.assertRaises(ApiError) as ctx:
                await client.get_packet("q")

        self.assertEqual(ctx.exception.status, 404)
        self.assertEqual(ctx.exception.body, "no messages")

    async def test_api_error_with_empty_body(self) -> None:
        self.lowmq.reply = Reply(status=503, body="", content_type="text/plain")

        async with self.client() as client:
            with self.assertRaises(ApiError) as ctx:
                await client.get_packet("q")

        self.assertIsNone(ctx.exception.body)

    async def test_setters(self) -> None:
        async with LowMqClient("old", "https://unused.example") as client:
            await client.set_auth_key("new")
            await client.set_lowmq_url(self.lowmq.url)
            await client.get_packet("q")

            with self.assertRaises(InvalidUrlError):
                await client.set_lowmq_url("not-a-url")

        self.assertEqual(self.lowmq.last.headers["Authorization"], "token new")

    async def test_own_session_is_closed_on_exit(self) -> None:
        timeout = aiohttp.ClientTimeout(total=10)
        client = self.client(timeout=timeout)

        async with client:
            session = client.session
            assert session is not None
            self.assertIs(session.timeout, timeout)

        self.assertTrue(session.closed)
        self.assertIsNone(client.session)

    async def test_default_timeout(self) -> None:
        async with self.client() as client:
            assert client.session is not None
            self.assertEqual(client.session.timeout.total, 30)

    async def test_external_session_is_not_closed(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with self.client(session=session) as client:
                await client.get_packet("q")
            self.assertFalse(session.closed)
            self.assertIs(client.session, session)

    async def test_request_without_session(self) -> None:
        with self.assertRaises(ClientClosedError):
            await self.client().add_packet("q", {})

    async def test_request_with_closed_session(self) -> None:
        session = aiohttp.ClientSession()
        await session.close()

        with self.assertRaises(ClientClosedError):
            await self.client(session=session).get_packet("q")


class UrlValidationTests(unittest.TestCase):
    def test_valid_urls(self) -> None:
        self.assertEqual(
            LowMqClient("k", "https://lowmq.example").lowmq_url, "https://lowmq.example/"
        )
        self.assertEqual(
            LowMqClient("k", "http://localhost:8788/api").lowmq_url, "http://localhost:8788/api"
        )

    def test_invalid_urls(self) -> None:
        for url in ("not-a-url", "ftp://lowmq.example", ""):
            with self.subTest(url=url), self.assertRaises(InvalidUrlError):
                LowMqClient("k", url)


if __name__ == "__main__":
    unittest.main()
