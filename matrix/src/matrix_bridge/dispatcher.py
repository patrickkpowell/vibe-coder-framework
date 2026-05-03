from __future__ import annotations

import logging

from matrix_bridge.commands import CommandContext
from matrix_bridge.commands.handoff import (
    handle_continue,
    handle_handoff,
    handle_sessions,
    handle_summarize,
)
from matrix_bridge.commands.help import handle_help
from matrix_bridge.commands.login import handle_login
from matrix_bridge.commands.reauth import handle_reauth
from matrix_bridge.commands.transport import handle_desktopmode, handle_matrixmode
from matrix_bridge.commands.ping import handle_ping
from matrix_bridge.commands.project import (
    handle_project,
    handle_projects,
    handle_reloadproject,
    handle_setproject,
)
from matrix_bridge.commands.rooms import handle_rooms
from matrix_bridge.commands.run import handle_message
from matrix_bridge.commands.session import handle_newsession, handle_session
from matrix_bridge.commands.todo import handle_todo
from matrix_bridge.commands.usage import handle_usage
from matrix_bridge.commands.wherearewe import handle_wherearewe
from matrix_bridge.config import BridgeConfig
from matrix_bridge.db import Database
from matrix_bridge.metrics import bridge_metrics
from matrix_common.client import MatrixClient

logger = logging.getLogger(__name__)

_HANDLERS = {
    "ping": handle_ping,
    "help": handle_help,
    "session": handle_session,
    "newsession": handle_newsession,
    "rooms": handle_rooms,
    "projects": handle_projects,
    "project": handle_project,
    "setproject": handle_setproject,
    "reloadproject": handle_reloadproject,
    "todo": handle_todo,
    "wherearewe": handle_wherearewe,
    "sessions": handle_sessions,
    "handoff": handle_handoff,
    "summarize": handle_summarize,
    "continue": handle_continue,
    "usage": handle_usage,
    "desktopmode": handle_desktopmode,
    "matrixmode": handle_matrixmode,
    "reauth": handle_reauth,
    "login": handle_login,
}


class Dispatcher:
    def __init__(self, db: Database, client: MatrixClient, config: BridgeConfig) -> None:
        self._db = db
        self._client = client
        self._config = config

    async def dispatch(
        self, room_id: str, sender: str, event_id: str, body: str
    ) -> None:
        session = await self._db.get_active_session(room_id)

        ctx = CommandContext(
            room_id=room_id,
            sender=sender,
            args=[],
            session_id=session.session_id if session else None,
            db=self._db,
            client=self._client,
            config=self._config,
        )

        bridge_metrics.messages_received_total += 1

        if not body.startswith(("/", "!")):
            try:
                await handle_message(ctx, body)
                if session:
                    await self._db.touch_session(session.session_id)
            except Exception as exc:
                logger.exception("Message handling failed: %s", exc)
                bridge_metrics.errors_total += 1
                await self._client.send_text(room_id, f"Error: {exc}")
            return

        parts = body.strip().split()
        command = parts[0].lstrip("/!").lower()
        ctx.args = parts[1:]

        handler = _HANDLERS.get(command)
        if handler is None:
            await self._client.send_text(
                room_id, f"Unknown command: !{command}\nTry !help for a list of commands."
            )
            logger.info("Unknown command %r from %s", command, sender)
            return

        try:
            await handler(ctx)
            if session:
                await self._db.touch_session(session.session_id)
        except Exception as exc:
            logger.exception("Command !%s failed: %s", command, exc)
            bridge_metrics.errors_total += 1
            await self._client.send_text(
                room_id, f"Command !{command} failed: {exc}"
            )
