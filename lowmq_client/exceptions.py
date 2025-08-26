# Exceptions for LowMQ client
from __future__ import annotations

from typing import Any, Optional


class LowMqError(Exception):
    """Base exception for LowMQ client."""


class InvalidUrlError(LowMqError):
    """Raised when provided LowMQ URL is invalid."""

    def __init__(self, url: Any, message: str | None = None):
        self.url = url
        super().__init__(message or f"Invalid LowMQ URL: {url!r}")


class ClientClosedError(LowMqError):
    """Raised when ClientSession is required but client is already closed."""


class ApiError(LowMqError):
    """Raised when server returns a non-success response."""

    def __init__(self, status: int, reason: str, body: Optional[Any] = None):
        self.status = status
        self.reason = reason
        self.body = body
        message = f"LowMQ API error: {status} {reason}"
        if body is not None:
            message += f" | body={body!r}"
        super().__init__(message)
