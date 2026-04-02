---
description: Initialize a new numbered project directory in the vibe-coder-framework — scaffolds src/, tests/, docs/specs/, infra/migrations/, and starter files (CLAUDE.md, TODO.md, pyproject.toml, .env.example, .gitignore, docs/architecture.md, docs/implementation-guide.md). Auto-detects next project number.
argument-hint: "[project-name] [-- description]"
allowed-tools: Bash, Read, Write, Glob
---

Initialize a new project in the vibe-coder-framework. Arguments: $ARGUMENTS

The framework base directory is: /Users/ppowell/Documents/vibe-coder-framework

## Step 1 — Gather project info

Check $ARGUMENTS and the conversation context for:
- **Project name** (e.g. "Home Automation Controller")
- **One-line description** (what problem does it solve?)
- **Initialize git repo?** (default: yes, unless user says otherwise)

If the project name is not provided in $ARGUMENTS or the conversation, ask the user before proceeding. The description can be left as a placeholder if not given.

Derive a **project slug**: lowercase, hyphens for spaces, no special characters.
Example: "Home Automation Controller" → `home-automation-controller`

## Step 2 — Detect next project number

Run:
```bash
ls -d /Users/ppowell/Documents/vibe-coder-framework/project-*/ 2>/dev/null | sort
```

Find the highest existing `project-NNN` directory and increment by 1. Zero-pad to 3 digits. If no projects exist, start at `001`.

## Step 3 — Create directories

```bash
mkdir -p /Users/ppowell/Documents/vibe-coder-framework/project-NNN/src
mkdir -p /Users/ppowell/Documents/vibe-coder-framework/project-NNN/tests/unit
mkdir -p /Users/ppowell/Documents/vibe-coder-framework/project-NNN/tests/integration
mkdir -p /Users/ppowell/Documents/vibe-coder-framework/project-NNN/docs/specs
mkdir -p /Users/ppowell/Documents/vibe-coder-framework/project-NNN/infra/migrations
```

Then create `.gitkeep` files to preserve empty directories:
```bash
touch /Users/ppowell/Documents/vibe-coder-framework/project-NNN/src/.gitkeep
touch /Users/ppowell/Documents/vibe-coder-framework/project-NNN/tests/unit/.gitkeep
touch /Users/ppowell/Documents/vibe-coder-framework/project-NNN/tests/integration/.gitkeep
touch /Users/ppowell/Documents/vibe-coder-framework/project-NNN/docs/specs/.gitkeep
touch /Users/ppowell/Documents/vibe-coder-framework/project-NNN/infra/.gitkeep
touch /Users/ppowell/Documents/vibe-coder-framework/project-NNN/infra/migrations/.gitkeep
```

## Step 4 — Write starter files

Use the templates below. Replace `{NNN}`, `{PROJECT_NAME}`, `{PROJECT_SLUG}`, `{DESCRIPTION}`, and `{TODAY}` (YYYY-MM-DD).

---

### CLAUDE.md

```markdown
# Project-{NNN}: {PROJECT_NAME} — Claude Code Context

## Project Overview
{DESCRIPTION}

## Current Phase
**Kickoff** — Architecture decisions not yet finalized. Run `/kickoff` to record
decisions before writing code.

## Conventions
- Language: Python 3.12+ with uv (all deps in project virtualenv)
- (Fill in remaining conventions after kickoff)

## Hard Rules
- No credentials, API keys, or tokens in any source file — ever.
- Tools install within the project virtualenv/environment, never system-wide.

## Session Startup Checklist
1. Read this file.
2. Read `docs/architecture.md` once decisions are recorded.
3. Read the spec relevant to the current task in `docs/specs/`.
4. Confirm the current phase before writing code.
```

---

### TODO.md

```markdown
# TODO

## Backlog

## Done
```

---

### README.md

```markdown
# {PROJECT_NAME}

{DESCRIPTION}

## Getting Started

\`\`\`bash
# Create and activate virtualenv
uv venv .venv
source .venv/bin/activate

# Install in editable mode
uv pip install -e .
\`\`\`

## Development

\`\`\`bash
# Run tests
python -m pytest
\`\`\`
```

---

### .env.example

```
# Environment variables for {PROJECT_NAME}
# Copy this file to .env and fill in values. Never commit .env to git.

# (Add variables here as the project requires them)
```

---

### .gitignore

```
# Credentials and secrets
.env
*.key
*.pem
*.p12
*.pfx
credentials.*
secrets.*

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
dist/
build/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp

# Test / coverage
.pytest_cache/
.coverage
htmlcov/
```

---

### pyproject.toml

```toml
[project]
name = "{PROJECT_SLUG}"
version = "0.1.0"
description = "{DESCRIPTION}"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1",
    "python-dotenv>=1.0",
]

[project.scripts]
# {PROJECT_SLUG} = "package.module:function"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[dependency-groups]
dev = [
    "pytest>=8.0",
]
```

---

### docs/architecture.md

```markdown
# Architecture

**Status: In Progress**

*Last updated: {TODAY}*

---

## Decisions

<!-- Decisions are recorded here by /todo decide or /kickoff -->
```

---

### docs/implementation-guide.md

```markdown
# Implementation Guide — {PROJECT_NAME}

## Tech Stack Summary

| Component | Technology |
|---|---|
| Language | Python 3.12+ with uv |

## Development Environment Setup

Run `/kickoff` to record architecture decisions and fill in this section.

## Component Breakdown

(TBD)
```

---

## Step 5 — Create Project-NNN.md in the framework root

Copy the Project-template.md and fill in the project name and description:

```bash
cp /Users/ppowell/Documents/vibe-coder-framework/Project-template.md \
   /Users/ppowell/Documents/vibe-coder-framework/Project-{NNN}.md
```

Then edit `Project-{NNN}.md` to substitute the project name and description in the title and overview section.

## Step 6 — Git init (if requested)

```bash
git -C /Users/ppowell/Documents/vibe-coder-framework/project-{NNN} init
git -C /Users/ppowell/Documents/vibe-coder-framework/project-{NNN} add \
  .gitignore CLAUDE.md README.md TODO.md .env.example pyproject.toml docs/ infra/ src/ tests/
git -C /Users/ppowell/Documents/vibe-coder-framework/project-{NNN} commit \
  -m "chore: initial project scaffold"
```

Do NOT add `.env` to the commit.

## Step 7 — Report and suggest next steps

Print a concise summary:

```
✓ Created project-{NNN}: {PROJECT_NAME}
  /Users/ppowell/Documents/vibe-coder-framework/project-{NNN}/

Next steps:
  1. Run /kickoff to record architecture decisions
  2. Add specs to docs/specs/ before implementing each component
  3. cd project-{NNN} && uv venv .venv && uv pip install -e .
```

If git was initialized, add: `  Git repository initialized with initial commit.`
