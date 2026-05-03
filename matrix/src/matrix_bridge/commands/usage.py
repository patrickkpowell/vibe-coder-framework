from __future__ import annotations

from matrix_bridge.commands import CommandContext


async def handle_usage(ctx: CommandContext) -> None:
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

    session = sessions[0]
    status = session.usage_status or "usage_unknown"

    task = await ctx.db.get_paused_task(session.session_id)

    lines = [f"Usage status: {status}"]
    if task:
        lines.append(f"Paused task: {task.task_id}")
        lines.append(f'Prompt: "{task.prompt[:120]}{"…" if len(task.prompt) > 120 else ""}"')
        lines.append("Send /continue when usage is available.")
    elif status == "usage_ok":
        lines.append("No paused tasks.")

    await ctx.client.send_text(ctx.room_id, "\n".join(lines))
