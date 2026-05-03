from __future__ import annotations

from matrix_bridge.commands import CommandContext


async def handle_rooms(ctx: CommandContext) -> None:
    projects = await ctx.db.list_projects()
    if not projects:
        await ctx.client.send_text(
            ctx.room_id,
            "No bot-managed rooms configured yet.\n"
            "Projects and their rooms will appear here once configured.",
        )
        return

    lines = ["Bot-managed rooms:"]
    for p in projects:
        room = p["matrix_room_id"] or "no room assigned"
        lines.append(f"  {p['project_id']} — {p['name']} — {room} [{p['room_state']}]")
    await ctx.client.send_text(ctx.room_id, "\n".join(lines))
