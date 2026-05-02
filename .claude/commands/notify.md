# /notify

Manage desktop-to-Matrix notifications. When enabled, Claude Code sends a
message to the vibe-coding Matrix channel when a task completes or when input
is required to continue.

**Usage:** `/notify on`, `/notify off`, `/notify status`

---

## Step 1 — Parse argument

Read `$ARGUMENTS` (case-insensitive, trim whitespace). Valid values: `on`, `off`, `status`.

If blank or unrecognized, output exactly:
```
Usage: /notify on | off | status
```
and stop.

---

## Step 2 — Execute

### `/notify on`
1. Call `set_notify_state(enabled=True)`.
2. Reply:
   > Desktop notifications **enabled**. I will send a message to vibe-coding
   > when a task completes or when I need your input to continue.

### `/notify off`
1. Call `set_notify_state(enabled=False)`.
2. Reply:
   > Desktop notifications **disabled**.

### `/notify status`
1. Call `get_notify_state()`.
2. Report the result.

---

## Step 3 — Ongoing behavior for this session

After `/notify on` is confirmed, follow this rule **for the rest of this
session** until `/notify off` is called or the session ends:

Before issuing the **final response** for any of these events:
- A discrete task is complete (tool-intensive work finishes, a file is
  delivered, a deploy completes, an investigation concludes)
- Input is **required to continue** (a question the user must answer before
  work can proceed)
- A fatal error blocks all progress

Do the following:
1. Call `get_notify_state()`.
2. If ENABLED, call `send_notification(message)` with a concise one-line
   message prefixed with the appropriate emoji:
   - `✅ <summary>` — task complete
   - `❓ <question>` — need input
   - `🚨 <error>` — blocked

**Do not** call `send_notification` for:
- Routine clarifications mid-task
- Informational messages or status updates
- Minor tool calls that are part of a larger in-flight task
