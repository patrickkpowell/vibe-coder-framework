---
description: Manage project TODO items — list, add, start, and complete tasks
argument-hint: [list | add <description> [after <dep>] | needs <item> after <dep> | done <item> | <item to start>]
allowed-tools: Read, Write, Edit, Glob
---

Manage TODO items for the active project. The argument is: $ARGUMENTS

The projects base directory is: /Users/ppowell/Documents/vibe-coder-framework

## Step 1 — Find the active project

Use Glob to find all `project-*/CLAUDE.md` files under the base directory. If there is only one project directory, use it. If there are multiple, infer the active project from the conversation context (most recently mentioned project, or a prior `/setproject` call). If the active project is ambiguous and cannot be inferred, ask the user: "Which project? (e.g., `001`)" and stop until they respond.

The TODO file path is: `{base}/project-NNN/TODO.md`

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

## Step 3 — Parse the argument and act

Normalize `$ARGUMENTS` by trimming whitespace.

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

### If the argument starts with `done `

Extract the search term (everything after `done `). Find the best matching item in **In Progress** first, then **Backlog**, using case-insensitive partial match against item descriptions (ignoring the `*(needs: ...)*` suffix). If multiple items match, list them and ask the user to be more specific.

Move the matched item to the **Done** section and change `- [ ]` to `- [x]`. Strip the `*(needs: ...)*` suffix when moving to Done — it is no longer relevant.

Confirm: "Marked done: *<item>*"

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

If the item is unblocked (all deps done, or no deps), move it from **Backlog** to the top of the **In Progress** section (keep `- [ ]`, preserve the `*(needs: ...)*` suffix in the file even though it is now satisfied).

Confirm: "Started: *<item>*. It has been moved to In Progress."

---

## Step 4 — Write the updated TODO.md

After any modification (add, needs, done, or start), write the updated content back to `TODO.md`. Preserve all existing items and their order within each section. Do not reformat or alter items that were not touched.

The section order is always: **In Progress**, **Backlog**, **Done**.
