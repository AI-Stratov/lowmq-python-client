from __future__ import annotations

import unittest

import lowmq_client
from lowmq_client import ApiError, ClientClosedError, InvalidUrlError, LowMqClient, LowMqError
from lowmq_client.models import Message, SendMessageRequest


class PublicApiTests(unittest.TestCase):
    def test_exports(self) -> None:
        self.assertEqual(
            sorted(lowmq_client.__all__),
            ["ApiError", "ClientClosedError", "InvalidUrlError", "LowMqClient", "LowMqError"],
        )

    def test_legacy_module(self) -> None:
        from lowmq_client.lowmq_client import LowMqClient as Legacy

        self.assertIs(Legacy, LowMqClient)

    def test_exceptions_share_a_base_class(self) -> None:
        for exc in (ApiError, ClientClosedError, InvalidUrlError):
            self.assertTrue(issubclass(exc, LowMqError))

    def test_api_error_message(self) -> None:
        self.assertEqual(str(ApiError(500, "Server Error")), "LowMQ API error: 500 Server Error")
        self.assertEqual(
            str(ApiError(400, "Bad Request", {"detail": "bad"})),
            "LowMQ API error: 400 Bad Request | body={'detail': 'bad'}",
        )

    def test_invalid_url_error_message(self) -> None:
        self.assertEqual(InvalidUrlError("x").url, "x")
        self.assertEqual(str(InvalidUrlError("x")), "Invalid LowMQ URL: 'x'")
        self.assertEqual(str(InvalidUrlError("x", "custom")), "custom")


class ModelTests(unittest.TestCase):
    def test_send_message_request(self) -> None:
        request = SendMessageRequest(key="q", value={"a": 1})
        self.assertEqual(request.model_dump(), {"key": "q", "value": {"a": 1}})

    def test_message_keeps_unknown_fields(self) -> None:
        message = Message(key="q", value=1, extra="x")
        self.assertEqual(message.key, "q")
        self.assertEqual(message.value, 1)
        self.assertEqual(message.model_extra, {"extra": "x"})


if __name__ == "__main__":
    unittest.main()
