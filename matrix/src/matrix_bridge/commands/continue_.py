from __future__ import annotations

import logging

from matrix_bridge.claude_runner import ClaudeRunner, split_response
from matrix_bridge.commands import CommandContext

logger = logging.getLogger(__name__)

_runner = ClaudeRunner()


async def handle_continue(ctx: CommandContext) -> None:
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
    task = await ctx.db.get_paused_task(session.session_id)

    if task is None:
        await ctx.client.send_text(
            ctx.room_id,
            "No paused task to continue.\n"
            "Use /usage to check status or send a new message.",
        )
        return

    await ctx.client.send_text(
        ctx.room_id,
        f"Continuing task {task.task_id}…",
    )

    from matrix_bridge.commands.run import _get_allowed_tools

    allowed_tools = _get_allowed_tools(session.project_id, await ctx.db.list_projects())

    result = await _runner.run(
        message=task.prompt,
        cwd=task.working_directory,
        claude_session_id=session.claude_session_id,
        allowed_tools=allowed_tools,
    )

    if result.session_id and result.session_id != session.claude_session_id:
        await ctx.db.set_claude_session_id(session.session_id, result.session_id)

    if result.usage_limit_hit:
        await ctx.db.set_session_usage_status(session.session_id, "usage_expired")
        logger.warning("Usage limit hit again on /continue for task %s", task.task_id)
        await ctx.client.send_text(
            ctx.room_id,
            f"Claude usage limit is still active.\n"
            f"Task {task.task_id} remains paused.\n"
            f"Send /continue again after your usage resets.",
        )
        return

    await ctx.db.set_task_state(task.task_id, "done")
    await ctx.db.set_session_usage_status(session.session_id, "usage_ok")
    await ctx.db.touch_session(session.session_id)

    for chunk in split_response(result.text):
        await ctx.client.send_text(ctx.room_id, chunk)
