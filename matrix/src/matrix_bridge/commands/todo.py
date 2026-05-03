from __future__ import annotations

import logging
import re
from pathlib import Path

from matrix_bridge.commands import CommandContext

logger = logging.getLogger(__name__)

_TODO_TEMPLATE = "# TODO\n\n## In Progress\n\n## Backlog\n\n## Done\n"
_ITEM_RE = re.compile(r"^(- \[[ x]\] )(.+?)(\s+\*\(needs: .+?\)\*)?\s*$")
_NEEDS_RE = re.compile(r"\*\(needs: (.+?)\)\*")


def _read_todo(path: Path) -> str:
    if path.exists():
        return path.read_text()
    path.write_text(_TODO_TEMPLATE)
    return _TODO_TEMPLATE


def _parse_items(content: str) -> dict[str, list[dict]]:
    sections: dict[str, list[dict]] = {"In Progress": [], "Backlog": [], "Done": []}
    current = None
    for line in content.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
        elif current in sections and line.startswith("- ["):
            m = _ITEM_RE.match(line)
            if m:
                needs_m = _NEEDS_RE.search(m.group(3) or "")
                needs = [n.strip() for n in needs_m.group(1).split(",")] if needs_m else []
                sections[current].append(
                    {"prefix": m.group(1), "desc": m.group(2), "needs": needs, "raw": line}
                )
    return sections


def _is_done(desc: str, done_items: list[dict]) -> bool:
    desc_lower = desc.lower()
    return any(desc_lower in item["desc"].lower() for item in done_items)


def _rebuild(content: str, sections: dict[str, list[dict]]) -> str:
    """Reconstruct TODO.md preserving structure, replacing item lines."""
    lines = content.splitlines(keepends=True)
    result = []
    current = None
    item_idx: dict[str, int] = {"In Progress": 0, "Backlog": 0, "Done": 0}

    for line in lines:
        stripped = line.rstrip("\n")
        if stripped.startswith("## "):
            current = stripped[3:].strip()
            result.append(line)
        elif current in sections and stripped.startswith("- ["):
            idx = item_idx.get(current, 0)
            items = sections[current]
            if idx < len(items):
                item = items[idx]
                needs_suffix = (
                    f" *(needs: {', '.join(item['needs'])})*" if item["needs"] else ""
                )
                result.append(f"{item['prefix']}{item['desc']}{needs_suffix}\n")
                item_idx[current] = idx + 1
            else:
                result.append(line)
        else:
            result.append(line)

    return "".join(result)


def _find_best(term: str, items: list[dict]) -> list[dict]:
    term_lower = term.lower()
    return [i for i in items if term_lower in i["desc"].lower()]


async def handle_todo(ctx: CommandContext) -> None:
    if not ctx.session_id:
        await ctx.client.send_text(ctx.room_id, "No active session. Use !newsession first.")
        return

    session = await ctx.db.get_active_session(ctx.room_id)
    if not session or not session.project_root_path:
        await ctx.client.send_text(
            ctx.room_id, "No project loaded. Use !setproject <id> first."
        )
        return

    root = Path(session.project_root_path)
    if not root.exists():
        await ctx.client.send_text(
            ctx.room_id,
            f"Project root not found: {root}\n"
            "The path may have moved. Run !setproject <id> to reload.",
        )
        return
    todo_path = root / "TODO.md"
    sub = ctx.args[0].lower() if ctx.args else "list"
    rest = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""

    # --- list ---
    if sub in ("list", ""):
        content = _read_todo(todo_path)
        sections = _parse_items(content)
        done_items = sections["Done"]
        lines = []

        for section_name in ("In Progress", "Backlog", "Done"):
            items = sections[section_name]
            if not items:
                continue
            lines.append(f"**{section_name}**")
            for i, item in enumerate(items, 1):
                if section_name == "Done":
                    lines.append(f"  {i}. ~~{item['desc']}~~")
                else:
                    lines.append(f"  {i}. {item['desc']}")
                    for dep in item["needs"]:
                        if not _is_done(dep, done_items):
                            lines.append(f"       ⚠ needs: {dep}")

        if not lines:
            await ctx.client.send_text(
                ctx.room_id, "No TODO items yet. Use `!todo add <description>` to add one."
            )
            return
        await ctx.client.send_text(ctx.room_id, "\n".join(lines))
        return

    # --- add ---
    if sub == "add":
        if not rest:
            await ctx.client.send_text(ctx.room_id, "Usage: !todo add <description>")
            return
        parts = re.split(r"\s+after\s+", rest, maxsplit=1, flags=re.IGNORECASE)
        desc = parts[0].strip()
        dep = parts[1].strip() if len(parts) > 1 else None
        suffix = f" *(needs: {dep})*" if dep else ""
        new_line = f"- [ ] {desc}{suffix}\n"

        content = _read_todo(todo_path)
        # Insert before ## Done (or at end of Backlog section)
        if "## Backlog\n" in content:
            # Find end of Backlog section
            backlog_start = content.index("## Backlog\n")
            done_start = content.find("## Done", backlog_start)
            if done_start == -1:
                content = content + new_line
            else:
                insert_pos = done_start
                # Walk back past blank lines
                while insert_pos > backlog_start and content[insert_pos - 1] == "\n":
                    insert_pos -= 1
                content = content[:insert_pos] + "\n" + new_line + content[insert_pos:]
        else:
            content += new_line
        todo_path.write_text(content)

        msg = f"Added to backlog: *{desc}*"
        if dep:
            msg += f"\nDepends on: {dep}"
        await ctx.client.send_text(ctx.room_id, msg)
        return

    # --- done ---
    if sub == "done":
        if not rest:
            await ctx.client.send_text(ctx.room_id, "Usage: !todo done <item>")
            return
        content = _read_todo(todo_path)
        sections = _parse_items(content)

        matches = _find_best(rest, sections["In Progress"]) or _find_best(rest, sections["Backlog"])
        if not matches:
            await ctx.client.send_text(ctx.room_id, f"No item matching '{rest}' found.")
            return
        if len(matches) > 1:
            names = "\n".join(f"  - {m['desc']}" for m in matches)
            await ctx.client.send_text(ctx.room_id, f"Multiple matches:\n{names}\nBe more specific.")
            return

        item = matches[0]
        # Remove from its section
        for sec in ("In Progress", "Backlog"):
            if item in sections[sec]:
                sections[sec].remove(item)
                break
        # Add to Done (no needs suffix)
        done_item = {"prefix": "- [x] ", "desc": item["desc"], "needs": [], "raw": ""}
        sections["Done"].append(done_item)

        todo_path.write_text(_rebuild(content, sections))
        await ctx.client.send_text(
            ctx.room_id,
            f"Marked done: *{item['desc']}*\n"
            "Use `!todo decide <topic>` to record any decisions made during this work.",
        )
        return

    # --- needs ---
    if sub == "needs":
        # Syntax: needs <item> after <dep>
        parts = re.split(r"\s+after\s+", rest, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) != 2:
            await ctx.client.send_text(ctx.room_id, "Usage: !todo needs <item> after <dependency>")
            return
        item_term, dep = parts[0].strip(), parts[1].strip()
        content = _read_todo(todo_path)
        sections = _parse_items(content)

        matches = _find_best(item_term, sections["In Progress"]) or _find_best(item_term, sections["Backlog"])
        if not matches:
            await ctx.client.send_text(ctx.room_id, f"No item matching '{item_term}' found.")
            return
        if len(matches) > 1:
            names = "\n".join(f"  - {m['desc']}" for m in matches)
            await ctx.client.send_text(ctx.room_id, f"Multiple matches:\n{names}\nBe more specific.")
            return

        item = matches[0]
        if dep not in item["needs"]:
            item["needs"].append(dep)
        todo_path.write_text(_rebuild(content, sections))
        await ctx.client.send_text(ctx.room_id, f"*{item['desc']}* now depends on: *{dep}*")
        return

    # --- start item (default) ---
    term = sub + (" " + rest if rest else "")
    content = _read_todo(todo_path)
    sections = _parse_items(content)

    matches = _find_best(term, sections["Backlog"])
    if not matches:
        in_prog = _find_best(term, sections["In Progress"])
        if in_prog:
            await ctx.client.send_text(
                ctx.room_id, f"*{in_prog[0]['desc']}* is already in progress."
            )
        else:
            await ctx.client.send_text(ctx.room_id, f"No backlog item matching '{term}'.")
        return
    if len(matches) > 1:
        names = "\n".join(f"  - {m['desc']}" for m in matches)
        await ctx.client.send_text(ctx.room_id, f"Multiple matches:\n{names}\nBe more specific.")
        return

    item = matches[0]
    blocked = [dep for dep in item["needs"] if not _is_done(dep, sections["Done"])]
    if blocked:
        dep_lines = "\n".join(f"  - {d} (not done)" for d in blocked)
        await ctx.client.send_text(
            ctx.room_id,
            f'⚠ "{item["desc"]}" is blocked by unmet dependencies:\n{dep_lines}\n\n'
            "Complete these first, or use `!todo done <dep>` to mark them done.",
        )
        return

    sections["Backlog"].remove(item)
    sections["In Progress"].insert(0, item)
    todo_path.write_text(_rebuild(content, sections))
    await ctx.client.send_text(
        ctx.room_id,
        f"Started: *{item['desc']}*\nUse `!todo decide <topic>` to record decisions as you go.",
    )
