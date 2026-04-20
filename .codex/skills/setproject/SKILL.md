---
name: setproject
description: Load and summarize the current state of a framework project when the user asks to set project context, load project 001, summarize a project, or start a session on an existing numbered project in vibe-coder-framework.
---

# Set Project

Use this skill when the user wants to load context for an existing framework project before doing work.

## Inputs

Accept a project identifier in any of these forms:
- `001`
- `1`
- `project-001`
- `Project-001`

If the user does not provide a project id, ask for one.

## Locate the framework

Prefer the current workspace root if it contains:
- `Projects.md`
- `Project-template.md`

If needed, infer the framework root by locating those files upward from the current working directory.

## Locate the project

Normalize the id to `NNN` and use:
- `Project-NNN.md`
- `project-NNN/CLAUDE.md`
- `project-NNN/docs/architecture.md`
- `project-NNN/docs/implementation-guide.md`

Read each file that exists. If the project directory is missing, report the exact path checked and stop.

## Output format

Produce a concise structured summary with:
- Active project name/title
- What it is
- Current phase
- What's been decided
- What's pending
- Key files

End with: `Project context loaded. What would you like to work on?`

## Notes

- Infer the current phase from the project artifacts if needed.
- If `architecture.md` or `implementation-guide.md` are still stubs, say so plainly.
- Keep the summary short and operational so the next task can start immediately.
