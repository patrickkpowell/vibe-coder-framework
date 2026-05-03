from __future__ import annotations

from matrix_bridge.commands import CommandContext


async def handle_ping(ctx: CommandContext) -> None:
    await ctx.client.send_text(ctx.room_id, "pong")
