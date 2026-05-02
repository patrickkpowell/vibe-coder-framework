# /sessions

Manage named Claude sessions on the NAS.

**Usage:** `/sessions [delete <name>]`

---

## Step 1 — Parse argument

Read `$ARGUMENTS` (trim whitespace).

- Blank → list all sessions
- `delete <name>` → delete the named session
- Anything else → show usage:
  ```
  Usage: /sessions [delete <name>]
  ```

---

## Step 2 — Execute

### `/sessions` (no argument)
Call `list_sessions()` and display the result.

### `/sessions delete <name>`
1. Call `delete_session(name=<name>, confirmed=True)`.
2. Report the result.
