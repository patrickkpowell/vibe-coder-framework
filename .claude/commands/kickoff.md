---
description: Guide an architectural kick off discussion for a project and record decisions
argument-hint: [project-id]
allowed-tools: Read, Write, Edit, Glob, Bash(git -C *:*)
---

The user wants to run a kick off discussion for project: $ARGUMENTS

The projects base directory is: /Users/ppowell/Documents/vibe-coder-framework

## Step 0 — Help check

If `$ARGUMENTS` is exactly `help`, print the following and stop:

```
/kickoff — architectural kick off discussion

Usage:
  /kickoff <project-id>    Run (or resume) the kick off for a project
  /kickoff help            Show this help

Arguments:
  project-id    Accepts: 001, 1, project-001, or Project-001

What it does:
  Leads a structured conversation to work through key architectural
  decisions and writes outcomes to docs/architecture.md,
  docs/implementation-guide.md, and CLAUDE.md.

Features:
  Resume-aware    Skips already-decided items; only works pending ones
  Ordered         Decisions that constrain later choices come first
  Confirm-first   Confirms each decision before writing to disk
  Deferral        Say "skip" to defer; re-run /kickoff to revisit

When to use:
  At the start of a new project (Kick Off phase), or when
  requirements change and decisions need revisiting.
```

## Step 1 — Locate the project

If `$ARGUMENTS` is empty, ask: "Which project would you like to kick off? (e.g., `001`)" and stop until the user responds.

Normalize the argument the same way `setproject` does — accept `001`, `1`, `project-001`, or `Project-001`. The directory name format is lowercase: `project-NNN`.

Read all of the following files that exist:
- `/Users/ppowell/Documents/vibe-coder-framework/Project-NNN.md` — high-level project requirements
- `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/CLAUDE.md` — conventions, hard rules, current phase
- `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/docs/architecture.md` — current decision state

If the project directory does not exist, report the exact path checked (e.g., `/Users/ppowell/Documents/vibe-coder-framework/project-042`) and stop. Do not create project files — that belongs to the Initial Setup phase.

## Step 2 — Phase guard

Read the `## Current Phase` line from `CLAUDE.md`. If it is NOT `Kick Off`, say:

> "This project is currently in the **[X]** phase. Running kickoff again may overwrite decisions already in use. Do you want to continue anyway?"

Wait for explicit confirmation before proceeding. If the user declines, stop.

## Step 3 — Resume detection

Scan `architecture.md` for `### ` headings under a `## Decisions` section. For each heading, read its `**Status:**` line. Classify each as:
- **Resolved**: status is `Decided` or `Deferred — TBD`
- **Pending**: status is `Pending` or the heading does not exist yet

If **all decisions are resolved**, report that and list them. Offer to re-open a specific decision for revision. Do not run the full conversation flow.

If **some decisions are resolved**, open with: "We've already decided [X, Y]. Today we need to work through: [A, B, C]." Then proceed only with pending items.

## Step 4 — Initialize architecture.md structure (if needed)

If `architecture.md` is a stub (no `## Decisions` section), rewrite it to the structured format before starting any conversation. Derive the decision topics from `Project-NNN.md` — read the requirements and identify the architectural choices this specific project needs to make. Different projects have different concerns; do not use a hardcoded topic list.

Use this format for the file header and each topic stub:

```
# Architecture

**Status: In Progress**

*Last updated: YYYY-MM-DD*

---

## Decisions

### [Topic Name]
- **Status:** Pending
```

This ensures the file is parseable for resume even if the session ends after the first decision.

## Step 5 — Decision conversation loop

Work through pending decisions in a **dependency-aware order**: decisions that constrain later choices come first (e.g., language before library selection, deployment model before infrastructure choices, data storage before query/analysis tooling). The right order depends on the project — use your judgment based on the requirements.

For each pending decision:

1. **Lead with substance.** Present 2–4 concrete options with tradeoffs framed around *this project's* specific requirements, constraints, and hard rules (read from `Project-NNN.md` and `CLAUDE.md`). Do not ask an open-ended question cold — bring knowledge to the conversation. Tailor the options to what actually matters for this project.

2. **Allow back-and-forth.** The user may ask follow-up questions, request elaboration on a specific option, or propose a choice not in the list. Engage fully — this is a real architectural discussion, not a form to fill out.

3. **Confirm before writing.** When the conversation reaches a natural conclusion, confirm explicitly: "So we're going with **[X]** — shall I record that?" Only write the decision after receiving an affirmative response.

4. **Support deferral.** If the user says "skip", "decide later", or similar, record it as `Deferred — TBD` with a short note capturing why it was deferred. Deferral does not block proceeding to the next topic.

5. **Write immediately after confirmation.** Do not batch decisions — write each one to `architecture.md` as soon as it is confirmed. Use this format:

```
### [Topic Name]
- **Status:** Decided
- **Decision:** [The chosen option]
- **Rationale:** [Why this fits the project's requirements and constraints]
- **Date:** YYYY-MM-DD
```

For deferred decisions:

```
### [Topic Name]
- **Status:** Deferred — TBD
- **Decision:** None yet
- **Rationale:** [Why deferred — e.g., "Awaiting deployment model decision"]
- **Date:** YYYY-MM-DD
```

## Step 6 — Finalize architecture.md

Once all decisions have a non-`Pending` status:
- Update the `**Status:**` header from `In Progress` to `Complete`
- Update the `*Last updated:*` date to today

If any decisions are `Deferred — TBD`, add a brief note at the top of the file listing them so they are visible at a glance. Example:

```
> **Note:** The following decisions are deferred: Database / Log Store, Analysis Tooling.
> Run `/kickoff NNN` again to revisit them without re-doing the others.
```

## Step 7 — Write implementation-guide.md

Create or overwrite `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/docs/implementation-guide.md` with:

- **Tech Stack Summary** — one line per `Decided` item (skip deferred)
- **Development Environment Setup** — steps to set up the dev environment based on decided tooling
- **Component Breakdown** — map the project's functional areas (from `Project-NNN.md`) to the decided tech choices
- **Key Constraints** — the hard rules from `CLAUDE.md` that will shape implementation

This file is read by `setproject` and should be written clearly enough to orient any future session.

## Step 8 — Update CLAUDE.md

Edit `CLAUDE.md`:
1. Rewrite the `## Conventions` section with finalized choices. Only include `Decided` items — do not list deferred items as if they were resolved.
2. Update `## Current Phase` from `Kick Off` to `Infrastructure`.

## Step 9 — Git commit

Run `git -C /Users/ppowell/Documents/vibe-coder-framework/project-NNN status` to see what files are modified. If unexpected staged or modified files exist beyond the three expected ones (`docs/architecture.md`, `docs/implementation-guide.md`, `CLAUDE.md`), warn the user and ask whether to proceed before committing.

If clean, stage and commit:

```
git -C /Users/ppowell/Documents/vibe-coder-framework/project-NNN add docs/architecture.md docs/implementation-guide.md CLAUDE.md
git -C /Users/ppowell/Documents/vibe-coder-framework/project-NNN commit -m "Kick Off complete: architecture decisions recorded and conventions finalized"
```

Show the commit output to the user. Do not push — that is an explicit action.

After committing, tell the user: "Kick off complete. Run `/setproject NNN` to load the updated project context."

If any decisions were deferred, remind them: "Run `/kickoff NNN` again to revisit deferred decisions — already-decided items will be skipped."
