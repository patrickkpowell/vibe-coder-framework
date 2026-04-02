---
description: Manage project TODO items — list, add, start, and complete tasks
argument-hint: [list | add <description> | done <item> | <item to start>]
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

## Step 3 — Parse the argument and act

Normalize `$ARGUMENTS` by trimming whitespace.

---

### If the argument is empty or `list`

Display all items grouped by section. Show item numbers within each section (1-based). Use this format:

```
**In Progress**
  1. Item being worked on

**Backlog**
  1. First item
  2. Second item

**Done**
  1. ~~Completed item~~
```

If a section is empty, omit it. If all sections are empty, say "No TODO items yet. Use `/todo add <description>` to add one."

---

### If the argument starts with `add `

Extract the description (everything after `add `). Add a new line to the **Backlog** section:

```
- [ ] <description>
```

Confirm: "Added to backlog: *<description>*"

---

### If the argument starts with `done `

Extract the search term (everything after `done `). Find the best matching item in **In Progress** first, then **Backlog**, using case-insensitive partial match. If multiple items match, list them and ask the user to be more specific.

Move the matched item to the **Done** section and change `- [ ]` to `- [x]`.

Confirm: "Marked done: *<item>*"

---

### Otherwise — start working on an item

Treat `$ARGUMENTS` as a search term. Find the best matching item in **Backlog** using case-insensitive partial match. If multiple items match, list them and ask the user to be more specific. If no items match in Backlog, check In Progress and report if it is already started.

Move the matched item from **Backlog** to the top of the **In Progress** section (keep `- [ ]`).

Confirm: "Started: *<item>*. It has been moved to In Progress."

---

## Step 4 — Write the updated TODO.md

After any modification (add, done, or start), write the updated content back to `TODO.md`. Preserve all existing items and their order within each section. Do not reformat or alter items that were not touched.

The section order is always: **In Progress**, **Backlog**, **Done**.
