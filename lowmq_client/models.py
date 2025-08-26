from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class SendMessageRequest(BaseModel):
    key: str
    value: Any


class Message(BaseModel):
    model_config = ConfigDict(extra="allow")

    _id: str | None = None
    key: Optional[str] = None
    value: Any | None = None
