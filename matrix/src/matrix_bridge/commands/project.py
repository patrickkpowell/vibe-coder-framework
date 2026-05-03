from __future__ import annotations

import json
import logging

from matrix_bridge.commands import CommandContext
from matrix_bridge.projects import ManifestError, list_manifests, load_manifest
from matrix_bridge.skills import load_skills

logger = logging.getLogger(__name__)


async def handle_projects(ctx: CommandContext) -> None:
    manifests = list_manifests(ctx.config.projects_dir)
    if not manifests:
        await ctx.client.send_text(
            ctx.room_id,
            f"No projects configured.\nAdd YAML manifests to: {ctx.config.projects_dir}",
        )
        return

    lines = ["Available projects:"]
    for m in manifests:
        room = f" — {m.matrix_room_id}" if m.matrix_room_id else ""
        lines.append(f"  {m.project_id}  {m.name}{room}")
    await ctx.client.send_text(ctx.room_id, "\n".join(lines))


async def handle_project(ctx: CommandContext) -> None:
    if not ctx.session_id:
        await ctx.client.send_text(ctx.room_id, "No active session. Use /newsession first.")
        return

    sessions = await ctx.db.list_sessions(ctx.room_id, limit=1)
    if not sessions or not sessions[0].project_id:
        await ctx.client.send_text(
            ctx.room_id, "No project loaded. Use /setproject <id>."
        )
        return

    s = sessions[0]
    await ctx.client.send_text(
        ctx.room_id,
        f"Active project: {s.project_id} — {s.project_name or 'unknown'}",
    )


async def handle_setproject(ctx: CommandContext) -> None:
    if not ctx.args:
        await ctx.client.send_text(ctx.room_id, "Usage: /setproject <project_id>")
        return

    if not ctx.session_id:
        await ctx.client.send_text(
            ctx.room_id, "No active session. Use /newsession first, then /setproject."
        )
        return

    project_id = ctx.args[0]
    try:
        manifest = load_manifest(ctx.config.projects_dir, project_id)
    except ManifestError as exc:
        await ctx.client.send_text(ctx.room_id, f"Project not found: {exc}")
        return

    skills, failed_skills = load_skills(ctx.config.skills_dir, manifest.skills)
    existing_docs = manifest.existing_docs()
    existing_specs = manifest.existing_specs()

    await ctx.db.upsert_project(manifest)
    await ctx.db.set_session_project(
        session_id=ctx.session_id,
        project_id=manifest.project_id,
        project_name=manifest.name,
        project_root_path=manifest.root_path,
        loaded_skills=[s.skill_id for s in skills],
    )

    lines = [
        f"Project set to {manifest.project_id}: {manifest.name}",
        f"Root: {manifest.root_path}",
        f"Branch: {manifest.default_branch}",
        f"Architecture docs: {len(existing_docs)}/{len(manifest.architecture_docs)} found",
        f"Specs: {len(existing_specs)}/{len(manifest.specs)} found",
        f"Skills loaded: {', '.join(s.skill_id for s in skills) or 'none'}",
    ]
    if failed_skills:
        lines.append(f"Skills not found: {', '.join(failed_skills)}")
    lines.append(f"Session: {ctx.session_id}")

    logger.info(
        "Project loaded",
        extra={"project_id": manifest.project_id, "session_id": ctx.session_id},
    )
    await ctx.client.send_text(ctx.room_id, "\n".join(lines))


async def handle_reloadproject(ctx: CommandContext) -> None:
    if not ctx.session_id:
        await ctx.client.send_text(ctx.room_id, "No active session.")
        return

    sessions = await ctx.db.list_sessions(ctx.room_id, limit=1)
    if not sessions or not sessions[0].project_id:
        await ctx.client.send_text(
            ctx.room_id, "No project loaded in this session. Use /setproject <id>."
        )
        return

    ctx.args = [sessions[0].project_id]
    await handle_setproject(ctx)
