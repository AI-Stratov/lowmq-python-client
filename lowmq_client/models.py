from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SendMessageRequest(BaseModel):
    key: str
    value: Any


class Message(BaseModel):
    model_config = ConfigDict(extra="allow")

    _id: str | None = None
    key: str | None = None
    value: Any = None
