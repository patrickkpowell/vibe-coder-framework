from __future__ import annotations

import json
import logging
import random
import string
from datetime import datetime, timezone

from matrix_bridge.claude_runner import ClaudeRunner, split_response
from matrix_bridge.commands import CommandContext
from matrix_bridge.metrics import bridge_metrics
from matrix_bridge.models import Task
from matrix_bridge.safety import check_dangerous_prompt

logger = logging.getLogger(__name__)

_runner = ClaudeRunner()


def configure_runner(api_key: str) -> None:
    """Seed or refresh the module-level runner with an Anthropic API key."""
    _runner.update_api_key(api_key)


def get_runner() -> ClaudeRunner:
    return _runner


def _new_task_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"task-{ts}-{suffix}"


async def handle_message(ctx: CommandContext, body: str) -> None:
    """Route a non-command message to Claude Code CLI."""
    if ctx.session_id is None:
        await ctx.client.send_text(
            ctx.room_id,
            "No active session. Use /newsession to create one, then /setproject <id>.",
        )
        return

    sessions = await ctx.db.list_sessions(ctx.room_id, limit=1)
    if not sessions:
        await ctx.client.send_text(ctx.room_id, "Session not found. Use /newsession.")
        return

    session = sessions[0]

    # §9.4 — any message from Matrix auto-restores matrix transport
    if session.active_transport != "matrix":
        await ctx.db.set_session_transport(session.session_id, "matrix")

    if not session.project_root_path:
        await ctx.client.send_text(
            ctx.room_id,
            "No project loaded. Use /setproject <id> first.",
        )
        return

    # Refuse dangerous prompts before touching Claude
    if match := check_dangerous_prompt(body):
        bridge_metrics.dangerous_prompts_blocked_total += 1
        await ctx.db.write_audit_event(
            "dangerous_prompt_blocked",
            session_id=session.session_id,
            room_id=ctx.room_id,
            matrix_user_id=ctx.sender,
            detail=match,
        )
        logger.warning("Dangerous prompt blocked: %r from %s", match, ctx.sender)
        await ctx.client.send_text(
            ctx.room_id,
            f"Refused: prompt contains a dangerous pattern ({match}).\n"
            f"If this was intentional, run the command manually.",
        )
        return

    allowed_tools = _get_allowed_tools(session.project_id, await ctx.db.list_projects())

    now = datetime.now(timezone.utc)
    task = Task(
        task_id=_new_task_id(),
        session_id=session.session_id,
        project_id=session.project_id,
        state="active",
        prompt=body,
        working_directory=session.project_root_path,
        created_at=now,
        updated_at=now,
    )
    await ctx.db.create_task(task)
    bridge_metrics.tasks_total += 1
    bridge_metrics.tasks_running += 1
    await ctx.db.write_audit_event(
        "task_started",
        session_id=session.session_id,
        room_id=ctx.room_id,
        matrix_user_id=ctx.sender,
        detail=task.task_id,
    )

    result = await _runner.run(
        message=body,
        cwd=session.project_root_path,
        claude_session_id=session.claude_session_id,
        allowed_tools=allowed_tools,
    )

    if result.session_id and result.session_id != session.claude_session_id:
        await ctx.db.set_claude_session_id(session.session_id, result.session_id)
        logger.info(
            "Claude session updated",
            extra={"matrix_session": session.session_id, "claude_session": result.session_id},
        )

    bridge_metrics.tasks_running -= 1

    if result.auth_error_hit:
        await ctx.db.set_task_state(task.task_id, "cancelled")
        bridge_metrics.errors_total += 1
        await ctx.client.send_text(
            ctx.room_id,
            f"Claude authentication error — Anthropic API key or OAuth session is invalid.\n"
            f"Task {task.task_id} cancelled.\n"
            f"Run !reauth to reload secrets and verify OAuth. If that fails, run !login to re-authenticate via browser.",
        )
        return

    if result.usage_limit_hit:
        await ctx.db.set_task_state(task.task_id, "paused_usage_expired")
        await ctx.db.set_session_usage_status(session.session_id, "usage_expired")
        bridge_metrics.tasks_usage_expired += 1
        logger.warning("Usage limit hit; task %s paused", task.task_id)
        await ctx.db.write_audit_event(
            "usage_expired",
            session_id=session.session_id,
            room_id=ctx.room_id,
            matrix_user_id=ctx.sender,
            detail=task.task_id,
        )
        await ctx.client.send_text(
            ctx.room_id,
            f"Claude usage limit reached.\n"
            f"Task {task.task_id} paused.\n"
            f"Send /continue after your usage resets.",
        )
        return

    await ctx.db.set_task_state(task.task_id, "done")
    await ctx.db.set_session_usage_status(session.session_id, "usage_ok")
    await ctx.db.write_audit_event(
        "task_completed",
        session_id=session.session_id,
        room_id=ctx.room_id,
        matrix_user_id=ctx.sender,
        detail=task.task_id,
    )

    for chunk in split_response(result.text):
        await ctx.client.send_text(ctx.room_id, chunk)


def _get_allowed_tools(project_id: str | None, projects: list[dict]) -> list[str] | None:
    if not project_id:
        return None
    project = next((p for p in projects if p["project_id"] == project_id), None)
    if not project:
        return None
    tools = project.get("allowed_tools")
    if isinstance(tools, str):
        try:
            tools = json.loads(tools)
        except json.JSONDecodeError:
            return None
    return tools if isinstance(tools, list) and tools else None
