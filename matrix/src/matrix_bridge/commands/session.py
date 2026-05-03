from __future__ import annotations

from datetime import datetime, timezone

from matrix_bridge.commands import CommandContext
from matrix_bridge.models import Session


def _new_session_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    import random, string
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"mx-{ts}-{suffix}"


async def handle_newsession(ctx: CommandContext) -> None:
    now = datetime.now(timezone.utc)
    session = Session(
        session_id=_new_session_id(),
        matrix_room_id=ctx.room_id,
        matrix_user_id=ctx.sender,
        state="active",
        created_at=now,
        updated_at=now,
    )
    await ctx.db.create_session(session)
    await ctx.client.send_text(
        ctx.room_id,
        f"New session created: {session.session_id}\n"
        f"State: active\n"
        f"Project: none\n"
        f"Use /setproject <id> to load a project.",
    )


async def handle_session(ctx: CommandContext) -> None:
    if ctx.session_id is None:
        await ctx.client.send_text(
            ctx.room_id,
            "No active session. Use /newsession to create one.",
        )
        return

    sessions = await ctx.db.list_sessions(ctx.room_id, limit=1)
    if not sessions:
        await ctx.client.send_text(ctx.room_id, "No active session found.")
        return

    s = sessions[0]
    project = s.project_name or s.project_id or "none"
    await ctx.client.send_text(
        ctx.room_id,
        f"Session: {s.session_id}\n"
        f"State: {s.state}\n"
        f"Project: {project}\n"
        f"Created: {s.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"Last activity: {s.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
    )
