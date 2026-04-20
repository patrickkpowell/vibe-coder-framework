---
name: kickoff
description: Run or resume an architectural kickoff for a numbered framework project when the user asks to kick off a project, make architecture decisions, revisit deferred decisions, or record project conventions and implementation guidance.
---

# Kickoff

Use this skill when the user wants to run the framework's architectural kickoff flow for an existing project.

## Inputs

Accept a project identifier in any of these forms:
- `001`
- `1`
- `project-001`
- `Project-001`

If no project id is provided, ask for one.

## Locate the framework and project

Prefer the current workspace root when it contains `Projects.md` and `Project-template.md`.

Normalize the project id to `NNN` and read, when present:
- `Project-NNN.md`
- `project-NNN/CLAUDE.md`
- `project-NNN/docs/architecture.md`

If the project directory does not exist, report the exact path checked and stop. Do not scaffold a project here.

## Phase guard

Read the `## Current Phase` value from `CLAUDE.md`.

If the phase is not Kick Off or Kickoff, warn that rerunning kickoff may overwrite active decisions and ask for explicit confirmation before continuing.

## Resume behavior

Use `architecture.md` as the source of truth for decision status.

Under `## Decisions`, treat a topic as:
- Resolved: `Decided` or `Deferred — TBD`
- Pending: `Pending` or missing

If all decisions are already resolved, summarize them and offer to reopen a specific one instead of rerunning the full flow.

If some are resolved, acknowledge what is already decided and continue only with pending topics.

## If architecture.md is still a stub

Initialize it to a parseable structure:

```markdown
# Architecture

**Status: In Progress**

*Last updated: YYYY-MM-DD*

---

## Decisions

### [Topic Name]
- **Status:** Pending
```

Derive the decision topics from the project requirements in `Project-NNN.md`. Do not use a fixed topic list.

## Conversation loop

Work through pending decisions in dependency-aware order.

For each decision:
1. Lead with 2-4 concrete options tailored to this project.
2. Allow follow-up discussion and user-proposed alternatives.
3. Confirm explicitly before writing.
4. Support deferral when the user says to skip for now.
5. Write each decision immediately after confirmation.

Use these formats:

```markdown
### [Topic Name]
- **Status:** Decided
- **Decision:** [Chosen option]
- **Rationale:** [Why it fits the project]
- **Date:** YYYY-MM-DD
```

```markdown
### [Topic Name]
- **Status:** Deferred — TBD
- **Decision:** None yet
- **Rationale:** [Why deferred]
- **Date:** YYYY-MM-DD
```

## Finalization

When all topics are non-pending:
- Mark architecture status `Complete`
- Update `Last updated`
- Add a short note at the top if any items remain deferred

Then:
- Create or overwrite `project-NNN/docs/implementation-guide.md`
- Update `project-NNN/CLAUDE.md`

## implementation-guide.md contents

Include:
- Tech Stack Summary
- Development Environment Setup
- Component Breakdown
- Key Constraints

Only include finalized decisions, not deferred ones.

## CLAUDE.md updates

- Rewrite `## Conventions` to reflect decided choices
- Update `## Current Phase` to `Infrastructure`

## Git behavior

Check the project repo status before committing.

If unexpected modified or staged files exist beyond:
- `docs/architecture.md`
- `docs/implementation-guide.md`
- `CLAUDE.md`

warn the user and ask whether to proceed.

If clean, stage and commit those files with:

`Kick Off complete: architecture decisions recorded and conventions finalized`

Do not push unless the user explicitly asks.
