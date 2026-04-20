---
name: projectinit
description: Scaffold a new numbered framework project when the user asks to create a new project, initialize a project, set up the next project directory, or generate the standard vibe-coder-framework project structure and starter files.
---

# Project Init

Use this skill when the user wants to create a new project inside the framework.

## Gather inputs

Look for:
- project name
- one-line description
- whether to initialize a git repo

Default git initialization to yes unless the user says otherwise.

If the project name is missing, ask for it. The description may be a placeholder when absent.

## Locate the framework

Prefer the current workspace root when it contains:
- `Projects.md`
- `Project-template.md`

## Numbering

Find existing `project-*` directories, select the highest `NNN`, and create the next zero-padded number. Start at `001` if none exist.

## Directory structure

Create:
- `project-NNN/src`
- `project-NNN/tests/unit`
- `project-NNN/tests/integration`
- `project-NNN/docs/specs`
- `project-NNN/infra/migrations`

Add `.gitkeep` files where needed to preserve empty directories.

## Starter files

Create or populate:
- `project-NNN/CLAUDE.md`
- `project-NNN/TODO.md`
- `project-NNN/README.md`
- `project-NNN/.env.example`
- `project-NNN/.gitignore`
- `project-NNN/pyproject.toml`
- `project-NNN/docs/architecture.md`
- `project-NNN/docs/implementation-guide.md`
- `Project-NNN.md` in the framework root, based on `Project-template.md`

Use the framework's conventions from the existing Claude command as the source of truth for the starter content.

## Content expectations

The scaffold should:
- mark the project as in Kickoff/Kick Off phase
- include base Python and uv conventions
- create a TODO file suitable for the todo skill
- create architecture and implementation docs as kickoff-ready stubs
- create a root `Project-NNN.md` from the template with the new project name and description filled in

## Git

If git initialization is enabled:
- initialize a repo in `project-NNN`
- stage the scaffolded files
- create an initial commit

Never add `.env`.

## Report

End with a concise summary:
- created project number and name
- absolute path to the project directory
- whether git was initialized
- next steps: run kickoff, add specs, set up the environment
