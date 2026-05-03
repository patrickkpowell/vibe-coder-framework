from __future__ import annotations

import asyncio
import logging
import os
import signal

from matrix_bridge.claude_runner import ClaudeRunner
from matrix_bridge.commands.run import configure_runner
from matrix_bridge.config import get_config
from matrix_bridge.db import Database
from matrix_bridge.dispatcher import Dispatcher
from matrix_bridge.logging_config import configure_logging
from matrix_bridge.mgmt import MgmtServer, write_handoff_to_nas
from matrix_bridge.secrets import load_secrets
from matrix_bridge.server import HealthServer
from matrix_bridge.sync import SyncLoop
from matrix_common.client import MatrixClient

configure_logging("matrix-bridge")
logger = logging.getLogger(__name__)

_BRIDGE_MGMT_PORT = int(os.getenv("BRIDGE_MGMT_PORT", "18321"))
_HANDOFF_PROMPT = (
    "Please write a session handoff summary in this exact format:\n\n"
    "# Session Handoff\n\n"
    "## Active Goals\n<what we are trying to accomplish>\n\n"
    "## Completed Work\n<summary of what was done this session>\n\n"
    "## Pending Tasks\n<what is left to do>\n\n"
    "## Key Decisions\n<decisions made, with rationale>\n\n"
    "## Files Changed\n<list of files modified>\n\n"
    "## Open Questions\n<unresolved questions>\n\n"
    "## Known Constraints\n<environment, auth, scope constraints>\n\n"
    "## Next Action\n<single recommended next step>\n\n"
    "Be concise and specific."
)


async def _run() -> None:
    settings = get_config()
    secrets = load_secrets()

    if secrets.anthropic_api_key:
        configure_runner(secrets.anthropic_api_key)
        logger.info("Claude runner initialised with API key from secrets")
    else:
        logger.info("Claude runner using OAuth session (~/.claude)")

    logger.info("Connecting to database")
    db = await Database.connect(settings.database_url)

    client = MatrixClient(
        homeserver_url=settings.matrix_homeserver_url,
        access_token=settings.matrix_bot_access_token,
    )

    whoami = await client.whoami()
    logger.info("Bot authenticated as %s", whoami.get("user_id"))

    if not await client.check_homeserver():
        raise RuntimeError("Matrix homeserver is not reachable")

    runner = ClaudeRunner()

    async def _handoff_handler(session_name: str, nonce: str) -> None:
        """Find the most recent active Claude session and generate a handoff."""
        try:
            sessions = await db.list_sessions_all(limit=5)
            active = next(
                (s for s in sessions if s.state == "active" and s.claude_session_id and s.project_root_path),
                None,
            )
            if not active:
                logger.warning("No active claude session found for handoff %s", session_name)
                return

            result = await runner.run(
                message=_HANDOFF_PROMPT,
                cwd=active.project_root_path,
                claude_session_id=active.claude_session_id,
            )
            await write_handoff_to_nas(session_name, result.text, nonce)
            logger.info("Handoff written for session %s", session_name)
        except Exception as exc:
            logger.exception("Handoff handler failed for %s: %s", session_name, exc)

    mgmt = MgmtServer(port=_BRIDGE_MGMT_PORT, handoff_handler=_handoff_handler)
    await mgmt.start()

    dispatcher = Dispatcher(db=db, client=client, config=settings)
    loop = SyncLoop(
        settings=settings,
        db=db,
        dispatcher=dispatcher,
        handoff_handler=_handoff_handler,
    )

    health_server = HealthServer(
        db=db,
        matrix_client=client,
        host="0.0.0.0",
        port=settings.metrics_port,
    )
    await health_server.start()

    stop_event = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_event_loop().add_signal_handler(sig, _handle_signal)

    sync_task = asyncio.create_task(loop.run())

    logger.info(
        "matrix-claude-bridge running",
        extra={
            "homeserver": settings.matrix_homeserver_url,
            "allowed_rooms": len(settings.allowed_rooms),
            "allowed_users": len(settings.allowed_users),
        },
    )

    await stop_event.wait()
    logger.info("Stopping sync loop")
    await loop.stop()
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass

    await mgmt.stop()
    await health_server.stop()
    await db.close()
    logger.info("matrix-claude-bridge stopped")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
