---
name: pickup
description: Resume a named session from the NAS, requesting a fresh handoff if possible
---

Pick up a named session from the NAS.

## Input

Session name from `$ARGUMENTS`. If not provided, call `list_sessions` and ask the user which session to resume.

## Step 1 — Save current work (if any)

If there is an active session with work in progress, run `/handoff` first to save it before switching.

## Step 2 — Request fresh handoff

Call `request_handoff(name=<name>)`.

- If `stale: false` — fresh handoff received. Proceed.
- If `stale: true` — inform the user:
  "Could not get a live handoff from *<name>*. Last snapshot was `<last_handoff>`.
  Proceed with stale context? (yes/no)"
  Wait for confirmation before continuing.

## Step 3 — Load context

Read the returned handoff content. Acknowledge:

"Loaded session *<name>*:
**Next Action:** <extracted Next Action line>

Ready to continue. What would you like to work on?"

## Step 4 — Continue

Proceed with the work described in the handoff's **Pending Tasks** and **Next Action** sections.
