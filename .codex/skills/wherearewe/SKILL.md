---
name: wherearewe
description: Orient the current session by surfacing the active In Progress TODO item, any where-we-left-off notes, and relevant architecture decisions — so the user can resume work immediately without re-reading docs.
---

# Where Are We

Use this skill when the user wants to quickly orient themselves — "where are we?", "what are we working on?", "catch me up", or whenever they need a fast session ramp-up on the active project.

## Active project resolution

Find the active project by checking `project-*/CLAUDE.md` under the framework root.

If only one project exists, use it.

If multiple exist, infer the active project from recent conversation context (a previous `setproject` call or explicit project mention). If still ambiguous, ask: "Which project? (e.g., `001`)"

## Files to read

- `project-NNN/TODO.md` — required
- `project-NNN/docs/architecture.md` — for relevant decisions
- `project-NNN/docs/implementation-guide.md` — for relevant implementation notes

## Step 1 — Find what's In Progress

Read `TODO.md`. Extract all items under `## In Progress`.

If **In Progress is empty**, say:

```
Nothing is In Progress for Project-NNN.

Backlog items available to start:
  1. <unblocked item>
  2. <unblocked item>
     ⚠ needs: <unmet dep>

Use `/todo <item>` to start one.
```

List only unblocked backlog items first, then blocked items with their unmet dependencies shown indented.

## Step 2 — Extract where-we-left-off notes

For each In Progress item, look for an HTML comment block immediately following it in `TODO.md` with this pattern:

```
<!-- WHERE WE LEFT OFF ...: ... -->
```

Extract the full content of any such comment. These are the developer's inline session notes.

If no such comment exists for an item, note that there are no inline session notes.

## Step 3 — Surface relevant decisions

Read `architecture.md` and `implementation-guide.md`. For each In Progress item, scan for decisions and notes matching keywords from the item description (tool names, component names, device names, protocol names, feature names).

Surface only the matches — do not dump everything.

## Output format

```
**Active Project:** Project-NNN — <Project Name>

**In Progress:**
  1. <item description>

**Where we left off:**
<Extracted content from HTML comment, or "No inline session notes found.">

**Relevant decisions:**
- <Decision topic>: <one-line summary>
- ...

**Relevant implementation notes:**
- <one-line note>
- ...

**Next step:**
<One sentence: what to do first based on the where-we-left-off notes and open decisions.>
```

If there are multiple In Progress items, repeat the **Where we left off**, **Relevant decisions**, and **Relevant implementation notes** blocks for each one, labeled by item.

## Notes

- Strip `*(needs: ...)*` suffixes when displaying item descriptions.
- Keep the output tight — the goal is fast orientation, not a full project dump.
- If `architecture.md` is missing or has no relevant matches, omit that section rather than saying it's empty.
- The **Next step** line should be concrete — name the file, command, or action — not generic advice.
