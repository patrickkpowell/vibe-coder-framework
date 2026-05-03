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

A shared platform service for the framework, not tied to any specific project.

| Component | Purpose |
|---|---|
| `matrix/src/matrix_common/` | Shared Matrix client library (HTTP, retry, destinations) |
| `matrix/src/matrix_api/` | FastAPI REST notification service |
| `matrix/src/matrix_mcp/` | FastMCP MCP server exposing Matrix notification tools |
| `matrix/src/matrix_bridge/` | Stateful Matrix-Claude bridge — runs Claude sessions from Matrix |
| `matrix/infra/` | Docker Compose, Dockerfiles, requirements for all Matrix services |
| `matrix/docs/specs/` | Specifications for the Matrix platform components |

---

## Installing the Skills

### Claude Code

```bash
mkdir -p ~/.claude/commands
cp .claude/commands/*.md ~/.claude/commands/
```

> **Note:** Some skills contain a hardcoded base path (`/Users/ppowell/Documents/vibe-coder-framework`). Update if your path differs:
>
> ```bash
> sed -i '' 's|/Users/ppowell/Documents/vibe-coder-framework|/path/to/your/framework|g' \
>   ~/.claude/commands/*.md
> ```

### Codex

```bash
mkdir -p ~/.codex/skills
cp -R .codex/skills/kickoff ~/.codex/skills/kickoff
cp -R .codex/skills/setproject ~/.codex/skills/setproject
cp -R .codex/skills/todo ~/.codex/skills/todo
cp -R .codex/skills/projectinit ~/.codex/skills/projectinit
cp -R .codex/skills/wherearewe ~/.codex/skills/wherearewe
```

---

## Using the Skills

### In Codex

```text
Initialize a new project called Home Automation Controller
Set project 001 as the active context
Run kickoff for project 001
List TODO items for the active project
```

### In Claude Code

### `/projectinit [project-name]`

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

**When to use:** At the start of every new project, before running `/kickoff`.

---

### `/setproject [project-id]`

Loads the context for an existing project into the current Claude Code session. Run this at the start of every session before doing any work.

```
/setproject 001
```

Accepts `001`, `1`, `project-001`, or `Project-001`. Claude will read `Project-NNN.md`, `CLAUDE.md`, `docs/architecture.md`, and `docs/implementation-guide.md`, then output a structured summary of the project's current state and what's next.

**When to use:** Every time you start a new Claude Code session on a project.

---

### `/kickoff [project-id]`

Runs an architectural kick off discussion for a project. Claude leads a structured conversation to work through key technical decisions — language, databases, infrastructure, deployment, credentials, etc. — and writes all outcomes directly to `docs/architecture.md`, `docs/implementation-guide.md`, and `CLAUDE.md`.

```
/kickoff 001
```

**Features:**
- **Resume-aware** — if a previous kick off was partially completed, Claude skips already-decided items and only works through pending ones.
- **Dependency-ordered** — decisions that constrain later choices are presented first.
- **Confirm-before-write** — Claude confirms each decision before writing it to disk.
- **Deferral support** — say "skip" or "decide later" to defer a decision without blocking progress. Re-run `/kickoff NNN` to revisit deferred items.

**When to use:** At the start of a new project (Phase 2: Kick Off), or any time requirements change and architectural decisions need revisiting.

---

### `/todo [subcommand or item]`

Manages a `TODO.md` file inside the active project directory. Automatically detects the active project from conversation context.

```
/todo list                    # show all items grouped by status
/todo add <description>       # add a new item to the backlog
/todo <partial item name>     # move a backlog item to In Progress and begin work
/todo done <partial item name># mark an item as done
/todo decide <topic>          # record an architecture or implementation decision
```

**TODO file location:** `project-NNN/TODO.md`

**When to use:** Any time during development to track what needs doing, what's in flight, and what's finished. Combine with `/setproject` at session start to resume from the current state.

---

### `/spec-review [project-id] <spec>`

Analyzes a spec file against the current architecture. Identifies impacted components, required changes, and produces a transition plan when services are being replaced.

---

### `/merge [project-id]`

Lists branches ahead of main, lets you choose which to merge, merges into main, pushes to GitHub, and offers worktree/branch cleanup.

```
/merge 001        # merge branches for project-001
/merge framework  # merge branches for this framework repo
```

---

### `/handoff` and `/pickup`

Save and resume session context across devices via NAS.

---

### `/notify [on|off|status]`

Controls desktop-to-Matrix task notifications. When enabled, Claude sends a Matrix message when it completes a task or needs input.

---

## Matrix Platform

The `matrix/` directory contains platform services shared across all projects. It is not part of any `project-NNN/`.

**Services:**
- `matrix-api` — REST notification service (`POST /send` → Matrix room)
- `matrix-mcp` — MCP server for Claude/agent Matrix notifications
- `matrix-bridge` — Stateful Claude session control plane driven from Matrix rooms

**Specs:**
- `matrix/docs/specs/matrix-notification-mcp-spec.md` — Synapse + matrix-api + matrix-mcp deployment and spec
- `matrix/docs/specs/matrix-claude-comm-channel-spec.md` — Bridge command grammar, session model, usage expiry, transport modes

**Deploy:** `matrix/infra/docker-compose.yml` on agent01. Secrets SOPS-encrypted, injected at runtime.

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

The skills accept flexible input (`/kickoff 1`, `/kickoff 001`, `/kickoff project-001`, `/kickoff Project-001` all work), but they always look for files using the canonical format above. If the files on disk don't match, the skill will report the path it checked and stop.

---

## Starting a New Project

1. Run `/projectinit "Project Name"` — scaffolds the directory and creates `Project-NNN.md`.
2. Run `/kickoff NNN` to begin the architectural discussion.
3. Initialize a git repo inside `project-NNN/` and push to GitHub as its own repo (if not done by projectinit).

Each project lives in its own git repository (`project-NNN/`). The framework directory (`vibe-coder-framework`) is a separate repo that tracks the framework itself — project directories are excluded from its `.gitignore`.
