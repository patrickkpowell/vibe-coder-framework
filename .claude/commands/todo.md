---
description: Manage project TODO items — list, add, start, complete tasks, and record decisions
argument-hint: [list | add <desc> [after <dep>] | needs <item> after <dep> | done <item> | decide <topic> | <item to start>]
allowed-tools: Read, Write, Edit, Glob
---

Manage TODO items for the active project. The argument is: $ARGUMENTS

The projects base directory is: /Users/ppowell/Documents/vibe-coder-framework

## Step 1 — Find the active project

Use Glob to find all `project-*/CLAUDE.md` files under the base directory. If there is only one project directory, use it. If there are multiple, infer the active project from the conversation context (most recently mentioned project, or a prior `/setproject` call). If the active project is ambiguous and cannot be inferred, ask the user: "Which project? (e.g., `001`)" and stop until they respond.

Key file paths for the project (substitute the correct NNN):
- TODO: `{base}/project-NNN/TODO.md`
- Architecture decisions: `{base}/project-NNN/docs/architecture.md`
- Implementation guide: `{base}/project-NNN/docs/implementation-guide.md`

## Step 2 — Locate or initialize TODO.md

Read the TODO file if it exists.

If it does not exist, create it with this structure:

```markdown
# TODO

## In Progress

## Backlog

## Done
```

## Dependency format

Dependencies are stored inline on the item line using this suffix:

```
- [ ] Item description *(needs: Dependency description)*
```

Multiple dependencies are comma-separated:

```
- [ ] Item description *(needs: Dep A, Dep B)*
```

An item is **blocked** if any of its dependencies are not yet in the **Done** section (case-insensitive partial match against Done items). An item is **unblocked** if all its dependencies are done, or it has no dependencies.

When parsing items, always strip the `*(needs: ...)*` suffix before displaying the item description to the user.

## Decision format

Decisions written to `docs/architecture.md` use this format, appended under `## Decisions`:

```markdown
### <Topic>
- **Status:** Decided
- **Decision:** <The choice made>
- **Rationale:** <Why — constraints, tradeoffs, requirements it satisfies>
- **Date:** YYYY-MM-DD
```

After writing to `architecture.md`, update its `*Last updated:*` date to today.

Decisions written to `docs/implementation-guide.md` update the relevant existing section inline (Tech Stack Summary, Component Breakdown, Development Environment Setup, etc.) rather than appending a new block.

**How to choose the right file:**
- **architecture.md** — which tool, library, protocol, pattern, or service was chosen and why (e.g. "use tabulate for table output", "use --host-timeout to prevent hung scans")
- **implementation-guide.md** — how something is concretely implemented, component wiring, environment setup steps, or corrections to existing implementation notes

## Step 3 — Parse the argument and act

Normalize `$ARGUMENTS` by trimming whitespace and stripping a single leading `/` if present (so `/list`, `/add`, `/done` etc. work the same as `list`, `add`, `done`).

---

### If the argument is `help`

Print the following usage text exactly and stop — do not read or modify any files:

```
/todo — project task manager with decision tracking

Usage:
  /todo                              List all items (same as /todo list)
  /todo list                         List all items grouped by status
  /todo add <description>            Add item to backlog
  /todo add <desc> after <dep>       Add item with a dependency declared
  /todo needs <item> after <dep>     Add a dependency to an existing item
  /todo done <item>                  Mark an item as done (prompts for decisions)
  /todo decide <topic>               Record a decision to architecture.md or implementation-guide.md
  /todo <item>                       Start working on an item (moves to In Progress, surfaces context)
  /todo help                         Show this help

Notes:
  - <item> and <dep> are case-insensitive partial matches
  - Blocked items cannot be started until their dependencies are done
  - Starting an item surfaces relevant decisions from docs/architecture.md
  - Completing an item prompts to capture any decisions made during the work
  - TODO.md lives in the active project directory (project-NNN/TODO.md)
```

---

### If the argument is empty or `list`

Display all items grouped by section. For each item show its description and, if it has unmet dependencies, show them indented beneath it as `⚠ needs: <dep>`. Done items in the Done section show with strikethrough. Use this format:

```
**In Progress**
  1. Item being worked on

**Backlog**
  1. Unblocked item
  2. Blocked item
       ⚠ needs: Some dependency not yet done
       ⚠ needs: Another unmet dependency

**Done**
  1. ~~Completed item~~
```

If a section is empty, omit it. If all sections are empty, say "No TODO items yet. Use `/todo add <description>` to add one."

---

### If the argument starts with `add `

The full text after `add ` may contain an ` after ` keyword to declare a dependency at creation time.

Examples:
- `/todo add Set up MCP server` → no dependency
- `/todo add Elasticsearch connector after MCP server` → depends on MCP server

Parse by splitting on ` after ` (case-insensitive). Everything before is the description; everything after is the dependency name.

Add a new line to the **Backlog** section:
- No dependency: `- [ ] <description>`
- With dependency: `- [ ] <description> *(needs: <dependency>)*`

Confirm: "Added to backlog: *<description>*" and note any dependency declared.

---

### If the argument starts with `needs `

Syntax: `needs <item> after <dependency>`

Find the best matching item in **Backlog** or **In Progress** (case-insensitive partial match on the item description, ignoring any existing `*(needs: ...)*` suffix). Find the dependency name (everything after ` after `).

If the item already has a `*(needs: ...)*` suffix, append the new dependency to the comma-separated list. Otherwise add the suffix.

Confirm: "*<item>* now depends on: *<dependency>*"

---

### If the argument starts with `decide `

The user wants to record a decision made during the current work.

Extract the topic from everything after `decide `. Then:

1. Read `docs/architecture.md` and `docs/implementation-guide.md` if they exist.

2. Ask the user (if not already clear from context):
   - "What was decided?" (the concrete choice)
   - "What's the rationale?" (why this choice — constraints, tradeoffs)
   - "Is this an architectural choice (tool/library/service/pattern) or an implementation detail (how it's wired up, env setup, component structure)?"

3. Based on the answer, write to the appropriate file:
   - **Architectural** → append a new `### <Topic>` block under `## Decisions` in `architecture.md` using the decision format above. Update `*Last updated:*`.
   - **Implementation** → update the relevant section of `implementation-guide.md` inline.

4. Confirm: "Recorded decision: *<topic>* → `docs/<file>`"

If both files are absent, create stubs before writing.

---

### If the argument starts with `done `

Extract the search term (everything after `done `). Find the best matching item in **In Progress** first, then **Backlog**, using case-insensitive partial match against item descriptions (ignoring the `*(needs: ...)*` suffix). If multiple items match, list them and ask the user to be more specific.

Move the matched item to the **Done** section and change `- [ ]` to `- [x]`. Strip the `*(needs: ...)*` suffix when moving to Done — it is no longer relevant.

Write the updated TODO.md.

Then ask: "Were any decisions made while working on *<item>*? Describe them briefly, or say 'no' to skip."

- If the user describes decisions, treat each one as a `decide` action: determine the type, ask for rationale if not provided, and write to the appropriate doc.
- If the user says 'no' or similar, confirm: "Marked done: *<item>*" and stop.

---

### Otherwise — start working on an item

Treat `$ARGUMENTS` as a search term. Find the best matching item in **Backlog** using case-insensitive partial match against item descriptions (ignoring the `*(needs: ...)*` suffix). If multiple items match, list them and ask the user to be more specific. If no items match in Backlog, check In Progress and report if it is already started.

**Dependency check:** Before moving the item, evaluate whether it is blocked. For each dependency listed in `*(needs: ...)*`, check whether a matching item exists in the **Done** section (case-insensitive partial match). If any dependency is not done, do NOT move the item. Instead report:

```
⚠ "<item>" is blocked by unmet dependencies:
  - <dep A> (not done)
  - <dep B> (not done)

Complete these first, or use `/todo done <dep>` to mark them done.
```

If the item is unblocked (all deps done, or no deps):

1. Move it from **Backlog** to the top of the **In Progress** section (keep `- [ ]`, preserve the `*(needs: ...)*` suffix in the file).

2. Write the updated TODO.md.

3. Read `docs/architecture.md` and `docs/implementation-guide.md` if they exist.

4. Output a **Context for this task** block summarizing decisions already made that are relevant to this item. Scan for keywords from the item description (tool names, component names, protocol names) and surface matching decisions. Format:

```
**Started:** <item>

**Relevant decisions from architecture.md:**
- <Decision topic>: <one-line summary>
- ...

**Relevant notes from implementation-guide.md:**
- <one-line note>
- ...

Use `/todo decide <topic>` at any time to record decisions made during this work.
```

If neither doc exists or no relevant decisions are found, just confirm: "Started: *<item>*. Use `/todo decide <topic>` to record decisions as you go."

---

## Step 4 — Write the updated TODO.md

After any modification (add, needs, done, or start), write the updated content back to `TODO.md`. Preserve all existing items and their order within each section. Do not reformat or alter items that were not touched.

The section order is always: **In Progress**, **Backlog**, **Done**.
