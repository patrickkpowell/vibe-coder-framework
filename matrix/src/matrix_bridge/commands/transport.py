from __future__ import annotations

from matrix_bridge.commands import CommandContext


async def handle_desktopmode(ctx: CommandContext) -> None:
    if ctx.session_id is None:
        await ctx.client.send_text(ctx.room_id, "No active session. Use /newsession first.")
        return

    sessions = await ctx.db.list_sessions(ctx.room_id, limit=1)
    if not sessions:
        await ctx.client.send_text(ctx.room_id, "No active session found.")
        return

    session = sessions[0]
    await ctx.db.set_session_transport(session.session_id, "desktop")

    sid_line = (
        f"Claude session ID: {session.claude_session_id}"
        if session.claude_session_id
        else "No Claude session ID yet (start a task first)."
    )
    await ctx.client.send_text(
        ctx.room_id,
        f"Desktop mode enabled for session {session.session_id}.\n"
        f"Unsolicited Matrix notifications suppressed.\n"
        f"{sid_line}\n"
        f"Use /matrixmode or send a message to re-enable Matrix notifications.",
    )


async def handle_matrixmode(ctx: CommandContext) -> None:
    if ctx.session_id is None:
        await ctx.client.send_text(ctx.room_id, "No active session. Use /newsession first.")
        return

    sessions = await ctx.db.list_sessions(ctx.room_id, limit=1)
    if not sessions:
        await ctx.client.send_text(ctx.room_id, "No active session found.")
        return

    session = sessions[0]
    await ctx.db.set_session_transport(session.session_id, "matrix")

    await ctx.client.send_text(
        ctx.room_id,
        f"Matrix mode enabled for session {session.session_id}.\n"
        f"Matrix notifications are active again.",
    )
