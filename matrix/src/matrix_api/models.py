from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["debug", "info", "warning", "error", "critical"]


class SendRequest(BaseModel):
    destination: str | None = None
    message: str = Field(..., min_length=1, max_length=16000)
    formatted_message: str | None = None
    severity: Severity = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SendResponse(BaseModel):
    status: str
    destination: str
    room_id: str
    event_id: str


class SendTemplateRequest(BaseModel):
    destination: str | None = None
    template: str
    values: dict[str, Any] = Field(default_factory=dict)


class DestinationsResponse(BaseModel):
    default: str
    destinations: list[str]


class HealthResponse(BaseModel):
    status: str
    homeserver: str
    bot_user_id: str
