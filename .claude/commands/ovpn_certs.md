---
name: handoff
description: Save current session context to NAS for pickup on another device
---

Write a session handoff snapshot to the NAS so work can be resumed on another device.

## Step 1 — Determine session name

If `$ARGUMENTS` is provided, use it as the session name.

If no argument, derive a name from the current project directory:
- Use the project directory name as a base (e.g. `project-001`)
- Append a short timestamp suffix (e.g. `project-001-0502`)

## Step 2 — Check for existing session

Call `list_sessions` to see if the session already exists.
If not, call `create_session(name=<name>, project=<project>, origin="desktop")`.

## Step 3 — Write the handoff

Generate a context snapshot in this format:

```
# Session Handoff: <name>

**Project:** <project>
**Written:** <timestamp>
**Origin:** desktop

## Active Goals
<what we are trying to accomplish>

## Completed Work
<summary of what was done this session>

## Pending Tasks
<what is left to do>

## Key Decisions
<decisions made, with rationale>

## Files Changed
<list of files modified>

## Open Questions
<unresolved questions>

## Known Constraints
<environment, auth, scope constraints>

## Next Action
<single recommended next step>
```

Call `write_handoff(name=<name>, content=<snapshot>, confirmed=True)`.

## Step 4 — Confirm

Tell the user:
"Session *<name>* saved.
Path: `/Volumes/vibe-code/claude-sessions/<name>/handoff.md`
Use `!continue <name>` in Matrix or `/pickup <name>` on Desktop to resume."