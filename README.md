# vibe-coder-framework

A framework for managing AI-assisted software development projects with Claude Code. Defines a repeatable workflow, directory standards, and custom Claude Code skills for discussion-driven, phase-based project development.

---

## What's in this repo

| File / Directory | Purpose |
|---|---|
| `Projects.md` | Master playbook — workflow phases, directory standards, agent team guidance, security checklist |
| `Project-template.md` | Template for writing a new project description file |
| `.claude/commands/kickoff.md` | Custom skill: `/kickoff` — architectural kick off discussion |
| `.claude/commands/setproject.md` | Custom skill: `/setproject` — load project context into a session |

---

## Installing the Skills

The two custom skills (`/kickoff` and `/setproject`) are Claude Code slash commands. They live in `.claude/commands/` in this repo. To install them, copy them into your global Claude Code commands directory:

```bash
mkdir -p ~/.claude/commands
cp .claude/commands/kickoff.md ~/.claude/commands/kickoff.md
cp .claude/commands/setproject.md ~/.claude/commands/setproject.md
```

> **Note:** The skills contain a hardcoded base path (`/Users/ppowell/Documents/vibe-coder-framework`). If your framework directory is in a different location, update that path in each file before copying:
>
> ```bash
> sed -i '' 's|/Users/ppowell/Documents/vibe-coder-framework|/path/to/your/framework|g' \
>   ~/.claude/commands/kickoff.md \
>   ~/.claude/commands/setproject.md
> ```

Once installed, the skills are available in any Claude Code session — no restart required.

---

## Using the Skills

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

## Project Workflow Overview

```
Phase 1: Initial Setup       → Create directory structure, init git repo, write Project-NNN.md
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

1. Copy `Project-template.md` to `Project-NNN.md` (e.g., `Project-002.md`) and fill it in.
2. Create `project-NNN/` with the standard directory structure (see `Projects.md`).
3. Initialize a git repo inside `project-NNN/` and push it to GitHub as its own repo.
4. Run `/kickoff NNN` to begin the architectural discussion.

Each project lives in its own git repository (`project-NNN/`). The framework directory (`vibe-coder-framework`) is a separate repo that tracks the framework itself — project directories are excluded from its `.gitignore`.
