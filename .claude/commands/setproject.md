---
description: Set active project context and summarize current state
argument-hint: [project-id]
allowed-tools: Read, Glob, Bash(ls:*)
---

The user wants to set the active project context to: $ARGUMENTS

The projects base directory is: /Users/ppowell/Documents/vibe-coder-framework

## Step 0 — Help check

If `$ARGUMENTS` is exactly `help`, print the following and stop:

```
/setproject — load project context into the current session

Usage:
  /setproject <project-id>    Load context for a project
  /setproject help            Show this help

Arguments:
  project-id    Accepts: 001, 1, project-001, or Project-001

What it reads:
  Project-NNN.md                        High-level project description
  project-NNN/CLAUDE.md                 Conventions, phase, hard rules
  project-NNN/docs/architecture.md      Architectural decisions
  project-NNN/docs/implementation-guide.md  Implementation guide (if present)

What it outputs:
  A structured summary — project name, current phase, key decisions,
  pending items, and the most important files to know about.

When to use:
  At the start of every session before doing any work on a project.
```

## Step 1 — Locate the project

The project argument may be provided as "Project-001", "project-001", "001", or "1". Normalize it to find the directory. The directory name format is lowercase: `project-NNN` (e.g., `project-001`).

Locate the following files (substitute the correct project number):
- `/Users/ppowell/Documents/vibe-coder-framework/Project-NNN.md` — high-level project description
- `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/CLAUDE.md` — project conventions and context
- `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/docs/architecture.md` — architectural decisions
- `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/docs/implementation-guide.md` — implementation guide (if it exists)

Read each file that exists.

## Step 2 — Summarize project context

After reading the files, output a structured summary in this format:

---
**Active Project: [Project Name / Title]**

**What it is:**
One or two sentence description from the project file.

**Current Phase:**
State which workflow phase this project is in (Initial Setup / Kick Off / Infrastructure / Development / Testing) based on what artifacts exist and their content.

**What's been decided:**
Bullet list of key decisions captured in architecture.md or implementation-guide.md. If these files are stubs or empty, say so.

**What's pending:**
Bullet list of open decisions or next steps, based on the current phase.

**Key files:**
Short list of the most important files to know about for this project.
---

## Step 3 — Confirm readiness

End with: "Project context loaded. What would you like to work on?"

If the project directory or files cannot be found, tell the user clearly which path was checked and that the project does not appear to exist yet.
