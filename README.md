# vibe-coder-framework

A framework for managing AI-assisted software development projects with Claude Code and Codex. Defines a repeatable workflow, directory standards, custom skills, and shared platform services for discussion-driven, phase-based project development.

---

## What's in this repo

### Framework Playbook

| File | Purpose |
|---|---|
| `Projects.md` | Master playbook — workflow phases, directory standards, agent team guidance, security checklist |
| `Project-template.md` | Template for writing a new project description file |

### Claude Code Skills (`.claude/commands/`)

| Skill | Command | Purpose |
|---|---|---|
| `listprojects.md` | `/listprojects` | List all projects with titles and descriptions |
| `setproject.md` | `/setproject [project-id]` | Load project context into the current session |
| `projectinit.md` | `/projectinit [project-name]` | Scaffold a new numbered project directory |
| `kickoff.md` | `/kickoff [project-id]` | Guide an architectural kickoff discussion and record decisions |
| `todo.md` | `/todo [subcommand]` | Manage per-project TODO items |
| `spec-review.md` | `/spec-review [project-id] <spec>` | Analyze a spec against current architecture |
| `merge.md` | `/merge [project-id]` | Merge worktree branches into main and push |
| `handoff.md` | `/handoff` | Save session context to NAS for pickup on another device |
| `pickup.md` | `/pickup` | Resume a named session from NAS |
| `sessions.md` | `/sessions` | Manage named Claude sessions on NAS |
| `notify.md` | `/notify` | Manage desktop-to-Matrix task notifications |
| `usage.md` | `/usage` | Check Claude usage state |
| `ovpn_certs.md` | `/ovpn_certs` | Create or renew OpenVPN certificates via OPNsense API |

### Codex Skills (`.codex/skills/`)

| Skill | Purpose |
|---|---|
| `kickoff/SKILL.md` | Architectural kickoff discussion |
| `setproject/SKILL.md` | Load project context into a session |
| `projectinit/SKILL.md` | Scaffold a new numbered project directory |
| `todo/SKILL.md` | Manage per-project TODO items |
| `wherearewe/SKILL.md` | Orient the session — active TODO, notes, architecture |

### Matrix Platform (`matrix/`)

A shared platform service for the framework, not tied to any specific project. Provides:

| Component | Purpose |
|---|---|
| `matrix/src/matrix_common/` | Shared Matrix client library (HTTP, retry, destinations) |
| `matrix/src/matrix_api/` | FastAPI REST notification service (`POST /send` → Matrix room) |
| `matrix/src/matrix_mcp/` | FastMCP MCP server exposing Matrix notification tools |
| `matrix/src/matrix_bridge/` | Stateful Matrix-Claude bridge — runs Claude sessions from Matrix |
| `matrix/infra/` | Docker Compose, Dockerfiles, and requirements for all Matrix services |
| `matrix/docs/specs/matrix-notification-mcp-spec.md` | Spec: Synapse + matrix-api + matrix-mcp |
| `matrix/docs/specs/matrix-claude-comm-channel-spec.md` | Spec: Matrix-Claude bridge (sessions, projects, skills) |
| `matrix/pyproject.toml` | Python project for the matrix packages |

---

## Installing the Skills

### Claude Code

The custom skills are Claude Code slash commands stored in `.claude/commands/`. To install them globally:

```bash
mkdir -p ~/.claude/commands
cp .claude/commands/*.md ~/.claude/commands/
```

> **Note:** Some skills contain a hardcoded base path (`/Users/ppowell/Documents/vibe-coder-framework`). If your framework directory is in a different location, update that path before copying:
>
> ```bash
> sed -i '' 's|/Users/ppowell/Documents/vibe-coder-framework|/path/to/your/framework|g' \
>   ~/.claude/commands/*.md
> ```

Once installed, the skills are available in any Claude Code session — no restart required.

### Codex

Codex skills are included in this repo under `.codex/skills/`:

```bash
mkdir -p ~/.codex/skills
cp -R .codex/skills/kickoff ~/.codex/skills/kickoff
cp -R .codex/skills/setproject ~/.codex/skills/setproject
cp -R .codex/skills/todo ~/.codex/skills/todo
cp -R .codex/skills/projectinit ~/.codex/skills/projectinit
cp -R .codex/skills/wherearewe ~/.codex/skills/wherearewe
```

Unlike the Claude command versions, the Codex skills are written to prefer the current workspace root instead of a hardcoded framework path.

---

## Using the Skills

### In Codex

Ask for the workflow directly in natural language, for example:

```text
Initialize a new project called Home Automation Controller
Set project 001 as the active context
Run kickoff for project 001
List TODO items for the active project
```

### In Claude Code

#### `/projectinit [project-name]`

Scaffolds a new numbered project directory with the full standard layout. Auto-detects the next available project number.

```
/projectinit "Home Automation Controller"
```

Creates:
```
project-NNN/
├── CLAUDE.md              # Project context for Claude Code sessions
├── TODO.md                # Task tracker (used by /todo)
├── README.md              # Project readme
├── .env.example           # Environment variable template
├── .gitignore             # Standard Python gitignore
├── pyproject.toml         # Python project config with hatchling
├── src/                   # Python source packages
├── tests/unit/            # Unit tests
├── tests/integration/     # Integration tests
├── docs/architecture.md   # Architecture decisions (populated by /kickoff)
├── docs/implementation-guide.md
├── docs/specs/            # Component specs (write before implementing)
└── infra/migrations/      # Database migrations
```

Also creates `Project-NNN.md` in the framework root from the template, and optionally initializes a git repository with an initial commit.

---

#### `/setproject [project-id]`

Loads the context for an existing project into the current Claude Code session.

```
/setproject 001
```

Accepts `001`, `1`, `project-001`, or `Project-001`. Reads `Project-NNN.md`, `CLAUDE.md`, `docs/architecture.md`, and `docs/implementation-guide.md`, then outputs a structured summary.

**When to use:** At the start of every session before doing any work on a project.

---

#### `/kickoff [project-id]`

Leads a structured architectural discussion and writes all decisions to `docs/architecture.md`, `docs/implementation-guide.md`, and `CLAUDE.md`.

```
/kickoff 001
```

- **Resume-aware** — skips already-decided items
- **Dependency-ordered** — presents decisions in dependency order
- **Confirm-before-write** — confirms each decision before writing
- **Deferral support** — `skip` to defer; re-run later to revisit

---

#### `/todo [subcommand]`

Manages a `TODO.md` file inside the active project directory.

```
/todo list                    # show all items grouped by status
/todo add <description>       # add a new item to the backlog
/todo <partial item name>     # move a backlog item to In Progress and begin work
/todo done <partial item name># mark an item as done
/todo decide <topic>          # record an architecture or implementation decision
```

---

#### `/spec-review [project-id] <spec>`

Analyzes a spec file against the current architecture. Identifies impacted components, required changes, and produces a transition plan when services are being replaced.

---

#### `/merge [project-id]`

Lists all local branches with commits ahead of main, lets you choose which to merge, merges into main, pushes to GitHub, and offers worktree/branch cleanup.

```
/merge 001        # merge branches for project-001
/merge framework  # merge branches for this framework repo
```

---

#### `/handoff` and `/pickup`

Save and resume session context across devices via NAS.

```
/handoff              # save current session to NAS
/pickup               # resume latest session from NAS
```

---

#### `/notify [on|off|status]`

Controls desktop-to-Matrix task notifications. When enabled, Claude sends a Matrix message when it completes a task or needs input, allowing you to walk away from long-running tasks and be notified remotely.

---

## Matrix Platform

The `matrix/` directory contains a complete platform service that is shared across all projects — it is not part of any specific `project-NNN/`. It provides:

1. **`matrix-api`** — REST notification service. n8n, scripts, and other automation send `POST /send` with a destination name and message; the service delivers to the configured Matrix room.

2. **`matrix-mcp`** — MCP server. Claude and agent tooling call `send_matrix_message` and other tools; the server delivers to Matrix.

3. **`matrix-bridge`** — Stateful control plane for running Claude Code sessions from Matrix. Supports `!setproject`, `!task`, `!newsession`, `!continue`, `!desktopmode`, and many other commands. Project-aware, session-persistent, and skill-aware.

### Deploying the Matrix Platform

See [`matrix/docs/specs/matrix-notification-mcp-spec.md`](matrix/docs/specs/matrix-notification-mcp-spec.md) for the full deployment guide including Docker Compose, Synapse setup, bot account creation, and acceptance criteria.

See [`matrix/docs/specs/matrix-claude-comm-channel-spec.md`](matrix/docs/specs/matrix-claude-comm-channel-spec.md) for the bridge specification — command grammar, session model, compaction, usage expiry handling, and transport modes.

The services deploy on `agent01` via Docker Compose in `matrix/infra/`. Secrets are SOPS-encrypted and injected at runtime — never committed as plaintext.

---

## Project Workflow Overview

```
Phase 1: Initial Setup       → /projectinit — scaffold directory, init git repo
Phase 2: Kick Off            → /kickoff NNN — discuss and record all architecture decisions
Phase 3: Infrastructure      → Deploy databases, services, docker-compose
Phase 4: Development         → Write code on feature branches, human review before merge
Phase 5: Unit Testing        → Tests pass, dead code reported
Phase 6: Integration Testing → End-to-end flows verified against real infrastructure
```

See `Projects.md` for the full playbook including entry/exit criteria for each phase, branching strategy, agent team guidance, and the security checklist.

---

## Naming Conventions

The skills construct file paths from a project number, so the files on disk **must** follow these exact formats:

| Artifact | Format | Example |
|---|---|---|
| Project description file | `Project-NNN.md` | `Project-001.md` |
| Project directory | `project-NNN/` | `project-001/` |

Rules:
- `NNN` is a **zero-padded, three-digit number** — `001`, `042`, `100`.
- The description file uses a **capital P** (`Project-001.md`).
- The directory uses **all lowercase** (`project-001/`).
- Both must use the **same number**.

---

## Starting a New Project

1. Run `/projectinit "Project Name"` — scaffolds the directory and creates `Project-NNN.md`.
2. Run `/kickoff NNN` to begin the architectural discussion.
3. Initialize a git repo inside `project-NNN/` and push to GitHub as its own repo (if not done by projectinit).

Each project lives in its own git repository (`project-NNN/`). The framework directory (`vibe-coder-framework`) is a separate repo that tracks the framework itself — project directories are excluded from its `.gitignore`.
