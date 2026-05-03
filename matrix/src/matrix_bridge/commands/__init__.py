from __future__ import annotations

from dataclasses import dataclass

from matrix_bridge.db import Database
from matrix_common.client import MatrixClient


@dataclass
class CommandContext:
    room_id: str
    sender: str
    args: list[str]
    session_id: str | None
    db: Database
    client: MatrixClient
    config: object  # BridgeConfig — typed as object to avoid circular import
