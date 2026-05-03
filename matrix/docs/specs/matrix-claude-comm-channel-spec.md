# Matrix-Claude Communications Channel Specification

## 1. Purpose

Build a Matrix-based communications channel that allows the user to interact with Claude as a remote vibe-coding agent.

The channel must allow the user to:

- Send Claude prompts through Matrix
- Run Claude tasks against a selected project context
- Use custom skills and command-style routing
- Receive Claude questions, status updates, usage-limit notices, and task results through Matrix
- Resume or continue interrupted tasks after usage limits reset
- Start new Matrix-driven Claude sessions so the Matrix channel does not become one endless conversation
- Move between Matrix and Claude Desktop when needed, while preserving sane notification behavior

This specification assumes a Matrix server has already been deployed by Claude and is reachable from the automation host.

---

## 2. Design Summary

The system will deploy a bridge service that sits between Matrix and Claude tooling.

```text
User Matrix Client
      |
      v
Matrix Server
      |
      v
matrix-claude-bridge service
      |
      +--> Session Manager
      +--> Project Context Manager
      +--> Skill Runner
      +--> Claude Execution Adapter
      +--> Usage/Limit Monitor
      +--> Notification Policy Engine
      +--> Audit/Event Store
      |
      v
Claude Code / Claude Agent Runtime / Claude API Adapter
      |
      v
Project Repositories + Specs + Architecture Docs + Skills
```

The bridge is not just a chat relay. It is a stateful control plane for Claude sessions.

---

## 3. Core Requirements

### 3.1 Matrix Command Channel

The bridge must listen to one or more Matrix rooms and process user messages.

Supported room modes:

- Direct message room between the user and Claude bot
- Optional project-specific rooms
- Optional admin/control room

The Matrix bot must:

- Authenticate to the Matrix server as a dedicated bot account
- Listen only to approved rooms
- Accept commands only from approved Matrix user IDs
- Ignore messages from unapproved users
- Persist message IDs to prevent duplicate task execution
- Support encrypted rooms if the deployed Matrix stack supports E2EE bot access

### 3.2 Claude Task Execution

The bridge must support running Claude as a task-performing coding agent.

The Claude execution adapter must support at least one of these modes:

- Claude Code CLI/headless execution
- Claude Code SDK execution
- Anthropic API execution
- Local agent wrapper that uses Claude as the reasoning engine and local tools for file operations

The implementation must isolate this behind an adapter interface so the runtime can be changed later without rewriting the Matrix layer.

Example adapter interface:

```python
class ClaudeExecutionAdapter:
    def start_session(self, session): ...
    def send_prompt(self, session_id, prompt): ...
    def continue_task(self, session_id): ...
    def cancel_task(self, session_id): ...
    def get_usage_status(self): ...
    def export_session_summary(self, session_id): ...
```

### 3.3 Project Context Support

The bridge must support project-aware context loading.

A project is identified by a project ID such as:

```text
001
002
elastic-monitoring
opnsense-nginx
signal-cli
```

Each project must have a project manifest.

Example:

```yaml
project_id: "001"
name: "Elastic Monitoring CLI"
root_path: "/srv/projects/elastic-monitoring-cli"
architecture_docs:
  - "docs/architecture.md"
  - "docs/ingestion-pipeline.md"
specs:
  - "specs/elasticsearch-monitoring-cli.md"
  - "specs/dashboard-spec.md"
skills:
  - "elastic-monitoring-context"
  - "logstash-analysis"
  - "kibana-query-writer"
default_branch: "main"
allowed_tools:
  - "read_file"
  - "write_file"
  - "git_diff"
  - "run_tests"
  - "create_patch"
notification_policy: "matrix-active-only"
```

The bridge must load project context when the user sends:

```text
!setproject 001
```

The `!setproject` command must:

1. Validate the project ID
2. Load the project manifest
3. Run the configured project context skill
4. Read the project architecture and specs
5. Create or update the active Matrix-Claude session state
6. Confirm the active project back to the user

Example response:

```text
Project set to 001: Elastic Monitoring CLI.
Loaded architecture docs: 2
Loaded specs: 2
Loaded skills: elastic-monitoring-context, logstash-analysis, kibana-query-writer
Active session: mx-20260430-001-0007
```

---

## 4. Custom Skills

### 4.1 Skill Definition

A skill is a reusable instruction bundle that can prepare Claude for a project, workflow, or task type.

Skills must be stored as files under a configured skills directory.

Example layout:

```text
/srv/claude-matrix/skills/
  elastic-monitoring-context/
    skill.md
    inputs.yaml
    output_contract.yaml
  logstash-analysis/
    skill.md
  matrix-vibe-coding/
    skill.md
```

### 4.2 Skill Manifest

Each skill may include a manifest.

```yaml
skill_id: "elastic-monitoring-context"
description: "Loads Elastic Stack monitoring architecture and analysis conventions."
required_files:
  - "docs/architecture.md"
  - "specs/elasticsearch-monitoring-cli.md"
allowed_commands:
  - "read_file"
  - "grep"
  - "git_status"
  - "git_diff"
context_strategy: "summarize-and-inject"
```

### 4.3 Skill Execution

Skills may be executed explicitly:

```text
!skill logstash-analysis
```

Or implicitly through project selection:

```text
!setproject 001
```

The bridge must record which skills have been loaded into a session.

---

## 5. Command Parity

Every user-facing command must work identically on both surfaces. A feature that
exists on Matrix (`!command`) must have an equivalent Claude Desktop skill
(`/command`), and vice versa. The name, arguments, and behavior must match.

### 5.1 Parity Rule

> **Any command written for Matrix (`!`) or Desktop (`/`) must work the same
> way on the other surface, with the same name and arguments.**

Implementations use the surface-appropriate mechanism to invoke the same
underlying logic:

| Surface | Mechanism | Example |
|---|---|---|
| Matrix | Bridge command handler | `!sessions delete foo` |
| Desktop | Claude Code skill + MCP tool | `/sessions delete foo` |

When adding a new command to either surface, the matching command on the other
surface must be added in the same commit.

### 5.2 Command Surface Map

| Command | Matrix | Desktop Skill | MCP Tool(s) |
|---|---|---|---|
| List sessions | `!sessions` | `/sessions` | `list_sessions()` |
| Delete session | `!sessions delete <name>` | `/sessions delete <name>` | `delete_session(name, confirmed=True)` |
| Save handoff | `!handoff [name]` | `/handoff [name]` | `write_handoff(name, content, confirmed=True)` |
| Pick up session | `!pickup <name>` | `/pickup <name>` | `request_handoff(name)` |
| Continue session | `!continue <name>` | `/continue <name>` | `get_session(name)` |
| Summarize session | `!summarize` | `/summarize` | — |
| Notify toggle | `!notify on\|off\|status` | `/notify on\|off\|status` | `get_notify_state()` / `set_notify_state(enabled)` |
| Send notification | — | — | `send_notification(message)` |

---

## 6. Matrix Command Grammar

The Matrix bot must support the following commands.

### 6.1 Project Commands

```text
!setproject <project_id>
```

Sets the active project context for the current Matrix session.

```text
!project
```

Shows the active project.

```text
!projects
```

Lists available projects.

```text
!reloadproject
```

Reloads the active project manifest, architecture docs, specs, and project skills.

### 6.2 Session Commands

```text
!newsession [project_id] [title]
```

Creates a new Claude session. If `project_id` is provided, the project is loaded immediately.

```text
!session
```

Shows the active session ID, project, state, last activity, and current transport mode.

```text
!sessions
```

Lists recent Matrix-created sessions.

```text
!resume <session_id>
```

Makes an existing session active again.

```text
!summarize
```

Compacts the current session into a summary and stores it in the session record.

```text
!archive
```

Archives the current Matrix session so it is no longer active.

### 6.3 Task Commands

```text
!task <prompt>
```

Starts a new task in the active session.

```text
!continue
```

Continues the last blocked, paused, or usage-expired task.

```text
!cancel
```

Cancels the active task if possible.

```text
!status
```

Shows current task status.

```text
!diff
```

Returns the current git diff for the active project.

```text
!test
```

Runs the configured project test command.

### 6.4 Skill Commands

```text
!skills
```

Lists available skills.

```text
!skill <skill_id>
```

Loads or runs a skill in the active session.

```text
!skillinfo <skill_id>
```

Shows what a skill does and what files/tools it may use.

### 6.5 Usage Commands

```text
!usage
```

Shows current Claude usage status if the adapter can retrieve it.

```text
!notify usage on|off
```

Controls whether usage reset notifications are sent to Matrix for this session.

### 6.6 Transport Commands

```text
!matrixmode
```

Marks Matrix as the active transport for this session.

```text
!desktopmode
```

Marks Claude Desktop as the active transport for this session.

```text
!transport
```

Shows whether the active communication surface is Matrix, Desktop, or unknown.

---

## 7. Session Model

The bridge must maintain its own session records.

A session record must include:

```yaml
session_id: "mx-20260430-001-0007"
created_at: "2026-04-30T22:00:00-05:00"
updated_at: "2026-04-30T22:14:00-05:00"
created_from: "matrix"
active_transport: "matrix"
project_id: "001"
project_name: "Elastic Monitoring CLI"
matrix_room_id: "!roomid:matrix.example.com"
matrix_user_id: "@patrick:matrix.example.com"
claude_session_ref: "provider-specific-session-id-or-null"
state: "active"
loaded_skills:
  - "elastic-monitoring-context"
  - "logstash-analysis"
current_task:
  task_id: "task-00012"
  state: "waiting_for_user"
  last_prompt: "Update the CLI spec to include shard relocation metrics."
  last_question: "Should shard metrics be per-cluster only or per-index also?"
usage:
  last_known_status: "ok"
  reset_at: null
compaction:
  last_summary_file: "/srv/claude-matrix/sessions/mx-20260430-001-0007/summary.md"
  last_summary_at: "2026-04-30T22:10:00-05:00"
```

### 7.1 Session States

Supported states:

- `active`
- `running_task`
- `waiting_for_user`
- `paused_usage_expired`
- `paused_error`
- `archived`
- `cancelled`

### 7.2 New Session Requirement

The system must not force all Matrix conversations into one long Claude session.

The user must be able to create a new session with:

```text
!newsession
```

The bridge must also support automatic new session creation based on policy:

```yaml
auto_new_session:
  enabled: true
  max_age_hours: 12
  max_messages: 100
  max_compacted_tokens_estimate: 120000
  idle_timeout_hours: 4
```

When a new session is created, the previous session must remain resumable.

---

## 8. Context Compaction

The system must support compaction so sessions can remain useful without growing indefinitely.

Compaction must produce:

- Project summary
- Active goals
- Completed work
- Pending tasks
- Open questions
- Important decisions
- Files changed
- Commands run
- Known constraints
- Next recommended action

Example summary file:

```markdown
# Session Summary: mx-20260430-001-0007

## Active Project
Elastic Monitoring CLI

## Goal
Update monitoring CLI and dashboard specs to include cluster-level shard relocation and unassigned shard metrics.

## Completed
- Added per-cluster Logstash PQ requirements
- Added Elasticsearch index/shard metric requirements
- Added dashboard panel requirements for relocating/unassigned shards

## Pending
- Add DevTools query examples
- Add JSON output schema for shard movement source/target

## Open Questions
- Should shard source/target be captured from cat shards only, cluster allocation explain, or both?

## Important Constraints
- Metrics must be summed across all pods in each Logstash stack.
- Do not report one-pod values as stack totals.
```

The `!summarize` command must create or refresh this file.

The `!newsession <project_id>` command may optionally inject the latest project/session summary into the new session.

---

## 9. Question-and-Answer Loop

Claude must be able to ask the user questions through Matrix when it needs input.

When Claude asks a question, the bridge must:

1. Mark the task state as `waiting_for_user`
2. Send the question to Matrix
3. Correlate the next user reply with the blocked task
4. Resume Claude with the answer

Example:

```text
Claude:
I need one decision before continuing:
Should the generated dashboard spec target Kibana Lens only, or should it include TSVB/ES|QL examples too?

Reply normally, or use:
!answer <text>
```

The user can answer with either:

```text
!answer Include both Lens and ES|QL examples.
```

Or, if a task is waiting for user input, with a normal Matrix message:

```text
Include both Lens and ES|QL examples.
```

The bridge must not treat unrelated Matrix chatter as an answer unless the room is a direct Claude bot room or the message explicitly uses `!answer`.

---

## 10. Notification Policy

### 9.1 Matrix-Originated Sessions

Claude may notify the user via Matrix only when the active session is Matrix-originated or Matrix-active.

Allowed Matrix notifications:

- Claude asks a question required to proceed
- Task completed
- Task failed
- Usage expired
- Usage reset or continuation is available
- Explicit `!status`, `!usage`, or `!session` response

### 9.2 Desktop-Originated Sessions

Claude must not send Matrix notifications for sessions that began on Claude Desktop unless the user explicitly links or activates that session from Matrix.

### 9.3 Matrix-to-Desktop Handoff

If a session began in Matrix but the user switches to Claude Desktop, the bridge must suppress Matrix notifications while Desktop is active.

The active transport can be set manually:

```text
!desktopmode
```

When `active_transport = desktop`, the bridge must:

- Stop sending routine Matrix updates
- Continue tracking session metadata if possible
- Send no Matrix questions unless the user returns to Matrix mode
- Allow `!matrixmode` to re-enable Matrix communication

### 9.4 Desktop-to-Matrix Return

When the user sends a message in Matrix for that session, the bridge must mark:

```yaml
active_transport: "matrix"
```

After this point, questions, status, task completion notices, and usage notices may be sent to Matrix again.

### 9.5 Notification Policy Rules

```yaml
notification_policy:
  matrix_enabled_only_when:
    - session.created_from == "matrix"
    - session.active_transport == "matrix"
  suppress_when:
    - session.active_transport == "desktop"
    - session.state == "archived"
    - user.notification_matrix_enabled == false
```

---

## 11. Claude Desktop Session Visibility

The desired behavior is:

- Matrix-created sessions should appear in Claude Desktop
- User should be able to continue from Claude Desktop
- User should be able to return to Matrix later

This requirement is implementation-dependent and must be validated against the selected Claude runtime.

The bridge must support two implementation paths:

### Option A — Native Claude Session Reuse

Use this only if the selected Claude runtime exposes usable session IDs that can be resumed by both the bridge and Claude Desktop.

Requirements:

- Store Claude session reference
- Resume by provider session ID
- Detect Desktop activity if available
- Keep Matrix session metadata mapped to the Claude session

### Option B — Bridge-Managed Session Mirror

Use this if Claude Desktop cannot natively share the same session with the bridge.

Requirements:

- Store all Matrix conversation state in the bridge
- Export session summaries for manual Desktop use
- Provide `!handoff desktop` command that sends a compact summary to the user
- Provide `!handoff matrix` command that reloads a Desktop-produced summary or pasted update

Example:

```text
!handoff desktop
```

Response:

```text
Desktop handoff summary generated.
Paste this into Claude Desktop to continue the session:

[summary follows]
```

This is less seamless but reliable.

The implementation must not pretend full Desktop/Matrix session synchronization exists unless it is proven in the deployed Claude runtime.

---

## 12. Usage Expiry Handling

The bridge must detect or infer Claude usage expiry.

Usage expiry states:

- `usage_ok`
- `usage_warning`
- `usage_expired`
- `usage_reset_available`
- `usage_unknown`

When usage expires during a task, the bridge must:

1. Pause the task
2. Save the task prompt, context, working directory, and partial output
3. Save a compaction summary
4. Mark the session state as `paused_usage_expired`
5. Notify Matrix only if Matrix notification policy allows it
6. Include the reset time if known

Example message:

```text
Claude usage expired while running task task-00012.
Session: mx-20260430-001-0007
Project: 001
State saved.
Reset time: 2026-05-01T02:00:00-05:00

After reset, send:
!continue
```

If reset time cannot be determined:

```text
Claude usage expired while running task task-00012.
State saved, but reset time could not be determined by the current adapter.
Send !usage later to check, or /continue when usage is available again.
```

The user must be able to continue after expiry with:

```text
!continue
```

The bridge must resume the saved task using:

- Active project context
- Last compaction summary
- Last user prompt
- Partial output or work state
- Current git diff/status

---

## 13. Task Persistence

Every task must have a task record.

Example:

```yaml
task_id: "task-00012"
session_id: "mx-20260430-001-0007"
project_id: "001"
created_at: "2026-04-30T22:12:00-05:00"
updated_at: "2026-04-30T22:20:00-05:00"
state: "paused_usage_expired"
prompt: "Update the dashboard spec to include per-cluster shard movement panels."
working_directory: "/srv/projects/elastic-monitoring-cli"
branch: "feature/dashboard-shard-metrics"
partial_output_file: "sessions/mx-20260430-001-0007/tasks/task-00012/output.md"
summary_file: "sessions/mx-20260430-001-0007/tasks/task-00012/summary.md"
last_error: "Claude usage limit reached"
continuation_prompt_file: "sessions/mx-20260430-001-0007/tasks/task-00012/continue.md"
```

---

## 14. Safety and Approval Controls

The bridge must not allow arbitrary remote code execution without guardrails.

Required controls:

- Matrix user allowlist
- Matrix room allowlist
- Project allowlist
- Tool allowlist per project
- Dangerous command denylist
- Optional approval gates before destructive actions
- Git diff review before committing
- No automatic secret exposure
- No secrets sent back to Matrix unless explicitly approved
- Rate limits per user and room

Dangerous commands should require approval or be blocked:

```text
rm -rf /
rm -rf ~
terraform apply
kubectl delete
helm uninstall
aws iam
aws secretsmanager get-secret-value
op item get
security find-generic-password
```

Approval flow example:

```text
Claude wants to run:
helm upgrade --install matrix-claude ./chart -n automation

Approve?
!approve task-00012 step-0004
!deny task-00012 step-0004
```

---

## 15. Authentication and Authorization

### 14.1 Matrix Bot Account

The bridge must use a dedicated Matrix bot account.

Example:

```yaml
matrix:
  homeserver_url: "https://matrix.example.com"
  bot_user_id: "@claude-bot:matrix.example.com"
  access_token_env: "MATRIX_BOT_ACCESS_TOKEN"
  allowed_users:
    - "@patrick:matrix.example.com"
  allowed_rooms:
    - "!project001room:matrix.example.com"
```

### 14.2 Claude Credentials

Claude credentials must be loaded from environment variables or a secret manager.

Example:

```yaml
claude:
  adapter: "claude-code-cli"
  auth_mode: "existing-cli-login"
  api_key_env: "ANTHROPIC_API_KEY"
  executable: "/usr/local/bin/claude"
```

The bridge must not log Claude API keys, Matrix access tokens, OAuth tokens, session cookies, or secret values.

---

## 16. Storage

The bridge must persist state to a local database.

Recommended minimum:

- SQLite for single-node deployment
- Postgres if the bridge will be scaled or clustered

Tables/collections:

- `sessions`
- `tasks`
- `projects`
- `skills`
- `messages`
- `approvals`
- `usage_events`
- `audit_events`

File storage:

```text
/srv/claude-matrix/
  config.yaml
  projects/
  skills/
  sessions/
    mx-20260430-001-0007/
      summary.md
      messages.jsonl
      tasks/
        task-00012/
          prompt.md
          output.md
          summary.md
          continue.md
  logs/
```

---

## 17. Configuration

Example `config.yaml`:

```yaml
server:
  name: "matrix-claude-bridge"
  bind_host: "0.0.0.0"
  bind_port: 8090

matrix:
  homeserver_url: "https://matrix.example.com"
  bot_user_id: "@claude-bot:matrix.example.com"
  access_token_env: "MATRIX_BOT_ACCESS_TOKEN"
  allowed_users:
    - "@patrick:matrix.example.com"
  allowed_rooms:
    - "!roomid:matrix.example.com"
  encrypted_rooms: false

claude:
  adapter: "claude-code-cli"
  executable: "/usr/local/bin/claude"
  default_model: "default"
  working_base_dir: "/srv/projects"
  usage_detection:
    enabled: true
    strategy: "adapter"

sessions:
  storage_path: "/srv/claude-matrix/sessions"
  auto_new_session:
    enabled: true
    max_age_hours: 12
    max_messages: 100
    idle_timeout_hours: 4
  compaction:
    enabled: true
    auto_compact_after_messages: 40
    summary_template: "/srv/claude-matrix/templates/session-summary.md"

projects:
  manifest_dir: "/srv/claude-matrix/projects"

skills:
  skill_dir: "/srv/claude-matrix/skills"

notifications:
  matrix_policy: "matrix-active-only"
  notify_on_task_complete: true
  notify_on_questions: true
  notify_on_usage_expired: true
  notify_on_usage_reset: true

security:
  require_approval_for_shell: true
  require_approval_for_git_commit: true
  require_approval_for_deploy: true
  redact_secrets: true
```

---

## 18. Docker Deployment

The bridge should be deployable as a Docker container on the same host or network as the Matrix server.

Example `docker-compose.yml`:

```yaml
services:
  matrix-claude-bridge:
    image: local/matrix-claude-bridge:latest
    container_name: matrix-claude-bridge
    restart: unless-stopped
    environment:
      MATRIX_BOT_ACCESS_TOKEN: "${MATRIX_BOT_ACCESS_TOKEN}"
      ANTHROPIC_API_KEY: "${ANTHROPIC_API_KEY}"
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - /srv/claude-matrix:/srv/claude-matrix
      - /srv/projects:/srv/projects
      - ~/.claude:/home/bridge/.claude:ro
    ports:
      - "8090:8090"
    networks:
      - matrix-net

networks:
  matrix-net:
    external: true
```

If Claude Code CLI auth is used, the container must either:

- Mount a dedicated Claude CLI auth directory read-only, or
- Run on the host using systemd instead of Docker, or
- Use the Anthropic API directly instead of the CLI login state

---

## 19. Health Checks

The bridge must expose health endpoints.

```text
GET /health
GET /ready
GET /metrics
```

`/health` should return process health.

`/ready` should verify:

- Matrix homeserver reachable
- Bot authenticated
- Storage writable
- Project manifests readable
- Claude adapter available

`/metrics` should expose Prometheus-style metrics if feasible.

Required metrics:

```text
matrix_claude_sessions_total
matrix_claude_active_sessions
matrix_claude_tasks_total
matrix_claude_tasks_running
matrix_claude_tasks_waiting_for_user
matrix_claude_tasks_usage_expired
matrix_claude_matrix_messages_received_total
matrix_claude_matrix_messages_sent_total
matrix_claude_usage_expiry_events_total
matrix_claude_errors_total
```

---

## 20. Logging

Logs must include:

- Session ID
- Task ID
- Project ID
- Matrix room ID hash or safe reference
- Command name
- State transitions
- Claude adapter errors
- Usage expiry events
- Approval decisions

Logs must not include:

- Matrix access tokens
- Claude API keys
- OAuth tokens
- Session cookies
- Private keys
- Secret values
- Full file contents unless debug mode is explicitly enabled

---

## 21. Error Handling

The bridge must handle:

- Matrix server unavailable
- Claude adapter unavailable
- Claude usage limit reached
- Claude task timeout
- Project manifest missing
- Skill missing
- Git working tree dirty
- Approval timeout
- Duplicate Matrix event delivery
- Bot restart during active task

For each error, the bridge must:

1. Persist state before returning an error
2. Send a Matrix message only if notification policy allows
3. Provide a clear recovery command when possible

Example:

```text
Task paused because Claude usage expired.
State was saved.
Use !continue after usage resets.
```

---

## 22. Acceptance Criteria

### 21.1 Matrix Bot Connectivity

- Bot can log in to Matrix
- Bot can receive messages from approved room
- Bot ignores unauthorized users
- Bot sends responses back to the correct Matrix room

### 21.2 Project Context

- `!projects` lists configured projects
- `!setproject 001` loads project manifest
- Project architecture and specs are included in Claude context
- Configured project skills are loaded
- `!project` reports the active project

### 21.3 Session Control

- `!newsession` creates a new session
- `!sessions` lists prior sessions
- `!resume <session_id>` resumes a prior session
- `!summarize` creates a compaction summary
- Session state survives bridge restart

### 21.4 Task Execution

- User can send a task through Matrix
- Claude performs the task in the selected project context
- Claude can ask a question through Matrix
- User answer resumes the task
- Task output returns to Matrix
- Task state survives restart

### 21.5 Usage Expiry

- If Claude usage expires, task state is saved
- Matrix notification is sent only when allowed
- Reset time is shown if the adapter can determine it
- `!continue` resumes the paused task after usage is available

### 21.6 Notification Policy

- Matrix-originated sessions can notify Matrix
- Desktop-originated sessions do not notify Matrix unless activated from Matrix
- `!desktopmode` suppresses Matrix notifications
- `!matrixmode` re-enables Matrix notifications
- Sending a Matrix message in a Matrix-created session marks Matrix as active transport

### 21.7 Security

- Unauthorized Matrix users cannot execute commands
- Destructive actions require approval
- Secrets are redacted from logs and Matrix responses
- Project tool permissions are enforced

---

## 23. Implementation Phases

### Phase 1 — Minimal Matrix Claude Bot

- Bot login
- Room allowlist
- User allowlist
- Basic command parser
- `!ping`, `!help`, `!session`, `!newsession`
- Persistent SQLite storage

### Phase 2 — Project Context and Skills

- Project manifest support
- `!projects`
- `!setproject`
- Skill directory support
- Skill loading
- Project context injection

### Phase 3 — Claude Execution Adapter

- Claude adapter interface
- First adapter implementation
- Task execution
- Task persistence
- Question/answer loop

### Phase 4 — Compaction and Continuation

- `!summarize`
- Automatic summaries
- `!continue`
- Restart-safe task state
- Session handoff summaries

### Phase 5 — Usage Expiry Handling

- Detect usage-limit errors
- Save paused task state
- Notify Matrix when allowed
- Resume after reset
- `!usage`

### Phase 6 — Desktop/Matrix Handoff

- `!desktopmode`
- `!matrixmode`
- `!handoff desktop`
- `!handoff matrix`
- Native session reuse if supported by selected Claude runtime

### Phase 7 — Hardening

- Approval gates
- Secret redaction
- Metrics endpoint
- Audit logging
- Docker/systemd deployment
- Backup and restore process

---

## 24. Open Implementation Questions

The implementer must answer these during development:

1. Which Claude runtime will be used first: Claude Code CLI, Claude Code SDK, or Anthropic API?
2. Can the chosen runtime expose and resume sessions in a way that also appears in Claude Desktop?
3. Can usage reset time be retrieved reliably, or must it be inferred from error messages?
4. Will Matrix rooms use E2EE? If yes, can the bot support encrypted room access reliably?
5. Should project work happen directly in the real repository, or in a temporary worktree per task?
6. Should Claude be allowed to commit changes, or only produce diffs?
7. Should the bridge support multiple users later, or only the owner?
8. Should each project have its own Matrix room?
9. Should the bot use one Claude session per Matrix session, or one Claude session per task?

---

## 25. Recommended Defaults

Use these defaults unless there is a reason not to:

```yaml
runtime: "claude-code-cli-or-sdk"
session_strategy: "one-matrix-session-maps-to-one-claude-session-when-supported"
fallback_session_strategy: "bridge-managed-session-mirror"
project_context_strategy: "manifest-driven"
compaction_strategy: "manual-plus-automatic"
notification_policy: "matrix-active-only"
repository_strategy: "git-worktree-per-task"
approval_strategy: "require-approval-for-destructive-actions"
storage: "sqlite"
deployment: "docker-compose-or-systemd-on-agent01"
```

The strongest default is `git-worktree-per-task`. It prevents Claude from tangling multiple tasks in the same working tree and makes cancellation/review safer.

---

## 26. Example User Flow

```text
User:
!newsession 001 monitoring dashboard spec

Claude Bot:
Created session mx-20260430-001-0007.
Project set to 001: Elastic Monitoring CLI.
Loaded project context and skills.

User:
Update the dashboard spec to include shard movement panels and Logstash PQ status per stack.

Claude Bot:
I can do that. One decision needed:
Should shard movement include only RELOCATING/UNASSIGNED shards, or also INITIALIZING/STARTED counts for baseline?

User:
Include all states, but make RELOCATING and UNASSIGNED the alerting focus.

Claude Bot:
Task complete.
Files changed:
- specs/dashboard.md

Summary:
- Added per-cluster shard state panels
- Added source/target relocation fields
- Added Logstash PQ per-stack panels
- Added alerting thresholds for unassigned and relocating shards

Use !diff to review changes.
```

---

## 27. Example Usage Expiry Flow

```text
Claude Bot:
Claude usage expired while running task task-00012.
Session: mx-20260430-001-0007
Project: 001
State saved.
Reset time: 2026-05-01T02:00:00-05:00

After reset, send:
!continue
```

Later:

```text
User:
!continue

Claude Bot:
Continuing task-00012 using saved context and latest project summary.
```

---

## 28. Example Desktop Handoff Flow

```text
User:
!desktopmode

Claude Bot:
Desktop mode enabled for session mx-20260430-001-0007.
Matrix notifications are suppressed until you return with /matrixmode or send another Matrix task.
```

If native desktop sync is unavailable:

```text
User:
!handoff desktop

Claude Bot:
Desktop handoff summary generated. Paste the following into Claude Desktop to continue this session.
```

When returning:

```text
User:
!matrixmode

Claude Bot:
Matrix mode enabled for session mx-20260430-001-0007.
Matrix notifications are active again.
```

---

## 29. Non-Goals

This project does not need to implement:

- A general-purpose Matrix client
- A replacement for Claude Desktop
- Multi-tenant SaaS behavior
- Public bot access
- Unrestricted shell access from Matrix
- Automatic deployment to production without approval
- Guaranteed native Claude Desktop session synchronization unless the selected Claude runtime supports it

---

## 31. Final Implementation Note

Treat Matrix as the remote control plane and the bridge as the source of truth for session routing, notification policy, project context, task persistence, and continuation.

Do not depend on Claude Desktop for core state management unless native session sharing is proven. The reliable implementation is bridge-managed state with optional Desktop handoff.

---

## 33. Room Lifecycle Management

### 31.1 Room Naming Convention

All bot-managed rooms must use a consistent naming convention so they are identifiable and manageable from any Matrix client.

```
kmn-<project_id>
```

Examples:

```
kmn-001
kmn-002
kmn-opnsense
kmn-elastic-monitoring
```

The bot sets this as the room alias on creation. Human-readable room names should also follow this pattern.

### 31.2 Room Management Commands

```text
!rooms
```

Lists all bot-managed rooms with project mapping, room state, and last activity.

```text
!archiveroom <project_id>
```

Marks the project as inactive in the bridge database and sends a Matrix tombstone event to redirect members. The room history is preserved on the server. Session and task state in the bridge is retained and remains resumable.

```text
!purgeroom <project_id>
```

Hard-deletes the room and all history from the Synapse server via the admin API. Requires explicit confirmation:

```text
!confirm purge <project_id>
```

This does not delete bridge session or task state — only the Matrix room and its server-side history are removed.

```text
!recreateroom <project_id>
```

Creates a new Matrix room for the project, updates the project manifest with the new room ID, and posts a summary of the last active session. Used after accidental deletion or following a purge where the project needs to remain active.

### 31.3 Room State Tracking

The bridge must track room state in the project record:

```yaml
room_state: "active"   # room exists and is in use
              "archived" # tombstoned, project inactive
              "lost"     # room gone, bridge state intact
              "purged"   # admin-purged, no server-side history
```

### 31.4 Room Loss Detection and Recovery

The bridge must detect when a room becomes unavailable:

- Event delivery fails with a room-not-found error
- A tombstone event is received for a bot-managed room
- The bot is kicked or banned from the room

When room loss is detected the bridge must:

1. Mark the project `room_state: lost`
2. Retain all session, task, and message state on disk
3. Log the loss event to the audit store
4. Not attempt further delivery to that room

The user recovers by running `!recreateroom <project_id>` from any active room or the admin room.

### 31.5 Message Persistence as Safety Net

All Matrix messages sent and received by the bridge must be logged to:

```
/srv/claude-matrix/sessions/<session_id>/messages.jsonl
```

This means room loss does not result in history loss. The bridge is the authoritative record of all conversation state — the Matrix room is a delivery channel only.

### 31.6 Synapse Admin Credentials

Room purge requires Synapse admin API access. The bridge must support a separate admin credential:

```yaml
matrix:
  synapse_admin_url: "https://matrix.example.com/_synapse/admin"
  synapse_admin_token_env: "SYNAPSE_ADMIN_TOKEN"
```

The admin token must not be logged or sent to any Matrix room. Purge operations must be recorded in the audit store with timestamp and operator user ID.

---

## 33. Infrastructure Decisions

### 32.1 Storage Backend

Use the existing **Postgres 17** instance (`postgresql` container) rather than SQLite.

- The bridge gets its own schema: `matrix_bridge`
- Connection string uses the existing `DATABASE_URL` pattern from the project `.env`
- No new database instance is required

### 32.2 Container Networking

The bridge container uses `network_mode: host`, consistent with `kmn-web`.

This gives direct access to all required services:

| Service | Address |
|---|---|
| Postgres 17 | `127.0.0.1:5432` |
| Synapse | `127.0.0.1:8008` |
| matrix-api | `127.0.0.1:8083` |

No Docker network configuration changes are required.

### 32.3 Relationship to Existing Matrix Services

The bridge is additive — it does not replace any existing service:

- `matrix-api` remains the outbound notification sender for other services
- `matrix-mcp` remains the MCP interface for Matrix tooling
- `matrix-synapse` and `matrix-postgres` are unchanged
- The bridge is a new container: `matrix-claude-bridge`

### 32.4 MCP Server Deployment

The `kmn-mcp` server currently runs on the Mac and connects to Postgres on agent01, likely via SSH tunnel. This works and is not changed by the bridge.

A future decision to containerize `kmn-mcp` on agent01 has been logged in TODO.md. That decision is independent of the bridge and would require Claude Desktop to connect to the MCP server via remote SSE/HTTP rather than local stdio. It is not in scope for this implementation.

---

## 31. Implementation Decisions

These decisions were made during design review and must be treated as locked unless explicitly reopened.

### 30.1 Claude Execution Adapter

Use the **Claude Code CLI** adapter as the first implementation target.

- Authentication uses the existing Claude CLI login state — no separate Anthropic API key required.
- The bridge mounts `~/.claude` from the agent01 host read-only into the container.
- The CLI executable path is configurable via `config.yaml`.
- The adapter interface from Section 3.2 must still be implemented so this can be swapped later.

### 30.2 Matrix Room Structure

Deploy **one Matrix room per project**.

- Each project manifest includes its assigned Matrix room ID.
- The bot listens only to rooms listed in the project manifests plus any configured admin room.
- There is no single catch-all room.

### 30.3 Auto-Session Policy

Override the defaults in Section 6.2 with:

```yaml
auto_new_session:
  enabled: true
  max_age_hours: 24
  max_messages: 200
  idle_timeout_hours: 4
```

The `!newsession` command remains available for explicit session rotation at any time.

### 30.4 Approval Gates

Approval is required only when a commit or destructive action touches sensitive paths.

Sensitive path patterns:

```yaml
approval_required_paths:
  - "infra/"
  - "infra/migrations/"
  - "secrets/"
  - ".env"
  - "*.sops.yaml"
  - "docker-compose*.yml"
  - "Dockerfile*"
  - "*.tf"
  - "*.tfvars"
```

Commits that touch only `src/`, `tests/`, `docs/`, or `specs/` do not require approval.

### 30.5 Worktree Strategy

Use the **existing checked-out worktree** for each project rather than creating a new worktree per task.

- The bridge reads the active worktree path from the project manifest.
- The worktree must already exist and be checked out before a task is started.
- The bridge does not create or destroy worktrees.
- This matches the existing project-001 convention where worktrees are managed manually under `.claude/worktrees/`.

### 30.6 Desktop Handoff — Pull Model

The Mac pulls session files from agent01. Agent01 does not push to the Mac.

Implementation priority:

1. **Primary — Claude Code skill**: A `!sync-session <session_id>` skill in `~/.claude/commands/` runs the rsync from the Mac. The bot sends the session ID to Matrix when `!handoff desktop` completes.

2. **Fallback — bot-sent command**: If the skill is not available or the rsync fails, the bot sends a ready-to-run rsync command to Matrix:

```
rsync -az patrick@agent01:~/.claude/projects/<session>/ ~/.claude/projects/<session>/
```

The bot must validate that the rsync succeeded (or report failure) before marking the session as `active_transport: desktop`.

**Known risks to validate before Phase 6:**

- Session JSONL files may have agent01 project paths embedded. If Mac project paths differ, Desktop may show the session but file references will not resolve.
- Claude Desktop may require a restart to discover newly synced session files.
- If either risk is confirmed, fall back to summary-paste as the primary handoff mechanism.
