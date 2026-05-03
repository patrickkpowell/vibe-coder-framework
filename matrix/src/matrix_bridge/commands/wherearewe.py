from __future__ import annotations

import re
from pathlib import Path

from matrix_bridge.commands import CommandContext
from matrix_bridge.commands.todo import _parse_items, _is_done, _read_todo

_WHERE_RE = re.compile(r"<!-- WHERE WE LEFT OFF[^:]*: (.+?) -->", re.DOTALL)
_DECISION_RE = re.compile(r"^### (.+)$", re.MULTILINE)
_DECISION_BLOCK_RE = re.compile(
    r"### (.+?)\n(.*?)(?=\n###|\Z)", re.DOTALL
)


def _extract_where_left_off(content: str, item_desc: str) -> str | None:
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if item_desc.lower()[:20] in line.lower() and line.startswith("- ["):
            # Look for WHERE WE LEFT OFF comment on next lines
            rest = "\n".join(lines[i + 1:i + 5])
            m = _WHERE_RE.search(rest)
            if m:
                return m.group(1).strip()
    return None


def _relevant_decisions(arch_content: str, keywords: list[str]) -> list[str]:
    results = []
    for m in _DECISION_BLOCK_RE.finditer(arch_content):
        topic = m.group(1).strip()
        block = m.group(2)
        topic_lower = topic.lower()
        block_lower = block.lower()
        if any(kw in topic_lower or kw in block_lower for kw in keywords):
            # Extract the Decision line
            dec_m = re.search(r"\*\*Decision:\*\* (.+)", block)
            summary = dec_m.group(1).strip() if dec_m else "(see architecture.md)"
            # Truncate long summaries
            if len(summary) > 100:
                summary = summary[:97] + "..."
            results.append(f"- {topic}: {summary}")
    return results


def _keywords_from(desc: str) -> list[str]:
    # Strip common stop words and return meaningful tokens
    stop = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "from"}
    return [w.lower() for w in re.split(r"\W+", desc) if len(w) > 3 and w.lower() not in stop]


async def handle_wherearewe(ctx: CommandContext) -> None:
    session = await ctx.db.get_active_session(ctx.room_id)
    if not session or not session.project_root_path:
        await ctx.client.send_text(
            ctx.room_id,
            "No project loaded. Use !setproject <id> first.",
        )
        return

    root = Path(session.project_root_path)
    if not root.exists():
        await ctx.client.send_text(
            ctx.room_id,
            f"Project root not found: {root}\nRun !setproject <id> to reload.",
        )
        return

    project_name = session.project_name or session.project_id or root.name
    todo_path = root / "TODO.md"
    arch_path = root / "docs" / "architecture.md"

    todo_content = _read_todo(todo_path)
    sections = _parse_items(todo_content)
    in_progress = sections["In Progress"]
    backlog = sections["Backlog"]
    done_items = sections["Done"]

    lines: list[str] = [f"**Active Project:** {project_name}"]

    if not in_progress:
        lines.append("\n**In Progress:** nothing started yet")
        lines.append("\n**Available backlog items:**")
        for i, item in enumerate(backlog, 1):
            blocked = [d for d in item["needs"] if not _is_done(d, done_items)]
            lines.append(f"  {i}. {item['desc']}")
            for dep in blocked:
                lines.append(f"       ⚠ needs: {dep}")
        lines.append("\nUse `!todo <item>` to start one.")
        await ctx.client.send_text(ctx.room_id, "\n".join(lines))
        return

    lines.append("\n**In Progress:**")
    for i, item in enumerate(in_progress, 1):
        lines.append(f"  {i}. {item['desc']}")

    arch_content = arch_path.read_text() if arch_path.exists() else ""

    for item in in_progress:
        desc = item["desc"]
        where = _extract_where_left_off(todo_content, desc)
        if len(in_progress) > 1:
            lines.append(f"\n— *{desc}* —")

        lines.append("\n**Where we left off:**")
        lines.append(where if where else "No inline session notes found.")

        if arch_content:
            keywords = _keywords_from(desc)
            decisions = _relevant_decisions(arch_content, keywords)
            if decisions:
                lines.append("\n**Relevant decisions:**")
                lines.extend(decisions)

    lines.append("\nUse `!todo done <item>` when finished, or `!todo decide <topic>` to record a decision.")
    await ctx.client.send_text(ctx.room_id, "\n".join(lines))
