# /usage

Check Claude usage state. Surfaces whether the current session is paused due to a
usage-limit expiry and what the paused task was.

**Usage:** `/usage`

---

## Step 1 — List sessions

Call `list_sessions()` to get all sessions and their usage state.

## Step 2 — Report

Scan the session list for any session with `usage_state: paused_usage_expired` in its
metadata.

- If any paused sessions exist, report each one:
  ```
  ⚠️ Session <name> is paused — Claude usage limit reached.
  Project: <project>
  Last handoff: <staleness>
  Send `!continue <name>` in Matrix or `/pickup <name>` on Desktop to resume after reset.
  ```

- If no paused sessions: report `✅ No sessions paused for usage expiry.`

## Step 3 — Check active session

Also call `get_session(<most-recent-active-session>)` if one exists and read the
handoff content's ## Status section. If it shows "PAUSED — Claude usage limit reached",
surface that prominently.
