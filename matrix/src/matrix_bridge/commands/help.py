from __future__ import annotations

from matrix_bridge.commands import CommandContext

_HELP = """\
matrix-claude-bridge commands:

Session
  !newsession          Create a new session
  !session             Show active session details

Projects
  !projects            List available projects
  !setproject <id>     Load a project into the active session
  !project             Show the active project
  !reloadproject       Reload the active project manifest from disk
  !rooms               List bot-managed rooms and project mapping

Tasks
  !todo list                    List all TODO items
  !todo add <desc>              Add item to backlog
  !todo add <desc> after <dep>  Add item with dependency
  !todo done <item>             Mark an item done
  !todo needs <item> after <dep> Add dependency to existing item
  !todo <item>                  Start working on an item

Handoff / Continuity
  !sessions                     List named sessions on NAS
  !handoff [name]               Save current context snapshot to NAS
  !summarize                    Write a session summary (for compaction)
  !continue <name>              Resume from a named session's last snapshot

Usage
  !usage               Show usage status and any paused task

Transport
  !desktopmode         Switch to Desktop; suppress unsolicited Matrix notifications
  !matrixmode          Return to Matrix; re-enable Matrix notifications

Utility
  !wherearewe          Orient session: active item, where we left off, decisions
  !ping                Check bot is alive
  !reauth              Reload SOPS secrets and hot-swap Matrix token + Claude API key
  !help                Show this message

Note: both ! and / prefixes are accepted.\
"""


async def handle_help(ctx: CommandContext) -> None:
    await ctx.client.send_text(ctx.room_id, _HELP)
