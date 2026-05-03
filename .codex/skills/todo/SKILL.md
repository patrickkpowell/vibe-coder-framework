---
name: todo
description: Manage framework project TODO items when the user asks to list tasks, add backlog items, start work, mark work done, add dependencies, or record architecture or implementation decisions for the active project.
---

# Todo

Use this skill when the user wants task management inside a framework project.

## Active project resolution

Find the active project by checking `project-*/CLAUDE.md` under the framework root.

If only one project exists, use it.

If multiple exist, infer the active project from recent conversation context such as a previous `setproject` or explicit project mention. If the active project is still ambiguous, ask the user which project to use.

## Files

Primary files:
- `project-NNN/TODO.md`
- `project-NNN/docs/architecture.md`
- `project-NNN/docs/implementation-guide.md`

If `TODO.md` does not exist, create:

```markdown
# TODO

## In Progress

## Backlog

## Done
```

## Item format

Use markdown checkboxes.

Dependencies are stored inline:

`- [ ] Item description *(needs: Dependency A, Dependency B)*`

When displaying items to the user, strip the dependency suffix from the main label and surface unmet dependencies separately.

## Supported actions

Handle these flows:
- `list` or no argument: show grouped items from In Progress, Backlog, and Done
- `add <description>`: add a backlog item
- `add <description> after <dependency>`: add a backlog item with a dependency
- `needs <item> after <dependency>`: add a dependency to an existing backlog or in-progress item
- `done <item>`: move an item to Done and ask whether any decisions should be recorded
- `decide <topic>`: record a decision in architecture or implementation docs
- `<item>`: start work on a backlog item

## Dependency logic

An item is blocked if any declared dependency does not have a matching completed item in the Done section.

Blocked items must not be moved into In Progress. Instead, explain which dependencies are still unmet.

## Start-work behavior

When starting an unblocked item:
1. Move it from Backlog to the top of In Progress.
2. Preserve existing item order elsewhere.
3. Read `architecture.md` and `implementation-guide.md` if present.
4. Return a short context block with relevant prior decisions for that task.

If no relevant decisions exist, confirm the task start and remind the user they can record decisions with this skill.

## Decision recording

If the user wants to record a decision, determine whether it belongs in:
- `architecture.md` for tool, library, service, protocol, or pattern choices
- `implementation-guide.md` for wiring, setup, component structure, or concrete implementation notes

Architecture decisions use:

```markdown
### <Topic>
- **Status:** Decided
- **Decision:** <choice>
- **Rationale:** <why>
- **Date:** YYYY-MM-DD
```

Update `Last updated` in `architecture.md` whenever you append a decision there.

For implementation decisions, update the relevant existing section inline instead of appending a new standalone block.

## Write discipline

After any modification, write the updated `TODO.md` back to disk.

Preserve:
- existing untouched items
- existing section order
- the section order `In Progress`, `Backlog`, `Done`
