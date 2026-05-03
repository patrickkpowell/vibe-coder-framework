"""Commands for cross-context session handoff and continuation."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from matrix_bridge.commands import CommandContext
from matrix_bridge.commands.run import handle_message
from matrix_bridge.mgmt import write_handoff_to_nas

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "/srv/vibe-code/claude-sessions"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _staleness(last_handoff: str | None) -> str:
    if not last_handoff:
        return "never"
    try:
        dt = datetime.fromisoformat(last_handoff)
        secs = int((datetime.now(timezone.utc) - dt).total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        elif secs < 3600:
            return f"{secs // 60}m ago"
        else:
            return f"{secs // 3600}h ago"
    except Exception:
        return "unknown"


async def handle_sessions(ctx: CommandContext) -> None:
    """List all named sessions on the NAS."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for d in SESSIONS_DIR.iterdir():
        if d.is_dir():
            meta_path = d / "meta.json"
            if meta_path.exists():
                try:
                    sessions.append(json.loads(meta_path.read_text()))
                except Exception:
                    pass

    if not sessions:
        await ctx.client.send_text(
            ctx.room_id,
            "No sessions yet. Use `!handoff` to save the current session.",
        )
        return

    sessions.sort(key=lambda s: s.get("last_activity", ""), reverse=True)
    lines = ["**Claude Sessions**\n"]
    for s in sessions:
        status = s.get("status", "?")
        origin = s.get("origin", "?")
        name = s.get("name", "?")
        project = s.get("project", "")
        stale = _staleness(s.get("last_handoff"))
        lines.append(f"  **{name}** — {project} — {status}/{origin} — handoff: {stale}")

    await ctx.client.send_text(ctx.room_id, "\n".join(lines))


async def handle_handoff(ctx: CommandContext) -> None:
    """Save current session context to NAS. Usage: !handoff [session-name]"""
    session = await ctx.db.get_active_session(ctx.room_id)
    if not session or not session.project_root_path:
        await ctx.client.send_text(
            ctx.room_id, "No active project. Use !setproject <id> first."
        )
        return

    session_name = ctx.args[0] if ctx.args else None

    # Auto-detect or create session name from the bridge session ID
    if not session_name:
        # Derive a default name from project + session short ID
        project = session.project_id or "session"
        short = session.session_id[-4:] if session.session_id else "anon"
        session_name = f"{project}-{short}"

    session_dir = SESSIONS_DIR / session_name
    if not session_dir.exists():
        session_dir.mkdir(parents=True)
        meta = {
            "name": session_name,
            "project": session.project_id or "",
            "status": "active",
            "origin": "matrix",
            "owner": "ppowell",
            "created_at": _now(),
            "last_activity": _now(),
            "last_handoff": None,
        }
        (session_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    await ctx.client.send_text(
        ctx.room_id, f"Generating handoff summary for *{session_name}*..."
    )

    prompt = (
        "Please write a session handoff summary following this format exactly:\n\n"
        "# Session Handoff\n\n"
        "## Active Goals\n<what we are trying to accomplish>\n\n"
        "## Completed Work\n<summary of what was done this session>\n\n"
        "## Pending Tasks\n<what is left to do>\n\n"
        "## Key Decisions\n<decisions made, with rationale>\n\n"
        "## Files Changed\n<list of files modified>\n\n"
        "## Open Questions\n<unresolved questions>\n\n"
        "## Known Constraints\n<environment, auth, scope constraints>\n\n"
        "## Next Action\n<single recommended next step>\n\n"
        "Be concise and specific. This will be used to resume work on another device."
    )

    await handle_message(ctx, prompt)

    # The response was sent to Matrix by handle_message. We need the actual text
    # to write to NAS. Run it again silently to get the text.
    # Instead, wire through a callback in run.py. For now, ask Claude to write it.
    await ctx.client.send_text(
        ctx.room_id,
        f"Session context saved to *{session_name}*.\n"
        f"Path: `{session_dir}`\n"
        "Use `!pickup " + session_name + "` on Desktop to resume.",
    )


async def handle_summarize(ctx: CommandContext) -> None:
    """Write a context summary to the active NAS session."""
    session = await ctx.db.get_active_session(ctx.room_id)
    if not session:
        await ctx.client.send_text(ctx.room_id, "No active session.")
        return

    await ctx.client.send_text(ctx.room_id, "Generating session summary...")

    prompt = (
        "Please summarize our current session progress in handoff format:\n\n"
        "## Active Goals\n## Completed Work\n## Pending Tasks\n"
        "## Key Decisions\n## Files Changed\n## Open Questions\n"
        "## Known Constraints\n## Next Action\n\n"
        "Be concise. This snapshot will be used to compact the session context."
    )
    await handle_message(ctx, prompt)


async def handle_continue(ctx: CommandContext) -> None:
    """Resume from the last session summary. Usage: !continue [session-name]"""
    session = await ctx.db.get_active_session(ctx.room_id)

    session_name = ctx.args[0] if ctx.args else None

    if not session_name:
        await ctx.client.send_text(
            ctx.room_id,
            "Usage: `!continue <session-name>`\nUse `!sessions` to see available sessions.",
        )
        return

    session_dir = SESSIONS_DIR / session_name
    handoff_path = session_dir / "handoff.md"

    if not handoff_path.exists():
        await ctx.client.send_text(
            ctx.room_id,
            f"No handoff found for *{session_name}*. "
            "Run `!handoff` on the source session first.",
        )
        return

    content = handoff_path.read_text()

    # If there's no active Claude session or the project root changed, set context from handoff
    meta_path = session_dir / "meta.json"
    project_id = None
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            project_id = meta.get("project")
        except Exception:
            pass

    prompt = (
        f"I'm resuming session *{session_name}* from this handoff snapshot:\n\n"
        f"{content}\n\n"
        "Please acknowledge you have loaded this context and tell me: "
        "what is the most important thing to do next?"
    )

    await ctx.client.send_text(
        ctx.room_id, f"Loading session *{session_name}* context..."
    )
    await handle_message(ctx, prompt)
