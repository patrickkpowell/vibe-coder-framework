from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["debug", "info", "warning", "error", "critical"]


class SendMessageResult(BaseModel):
    status: str
    destination: str
    event_id: str


class SendTemplateResult(BaseModel):
    status: str
    destination: str
    event_id: str


class DestinationsResult(BaseModel):
    default: str
    destinations: list[str]


class CreateRoomResult(BaseModel):
    status: str
    room_id: str
    name: str


class InviteUserResult(BaseModel):
    status: str
    destination: str
    user_id: str
