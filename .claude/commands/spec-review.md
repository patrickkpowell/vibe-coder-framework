---
description: Analyze a spec file against the current architecture, identify impacts and required changes, and produce a transition plan if services or infrastructure are being replaced
argument-hint: [project-id] <spec-name-or-path>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git -C *:*), Bash(ls *)
---

The user wants to review a spec against the current architecture: $ARGUMENTS

The projects base directory is: /Users/ppowell/Documents/vibe-coder-framework

## Step 0 — Help check

If `$ARGUMENTS` is exactly `help`, print the following and stop:

```
/spec-review — analyze a spec against the current architecture

Usage:
  /spec-review <spec-name>              Review a spec for the active project
  /spec-review <project-id> <spec>      Review a spec for a specific project
  /spec-review <project-id>             List available specs for a project
  /spec-review help                     Show this help

Arguments:
  project-id    Accepts: 001, 1, project-001, or Project-001
  spec          Spec file name, partial name, or path. Examples:
                  signal-relay-server
                  docs/specs/proxmox.md
                  proxmox

What it does:
  1. Reads the spec file
  2. Surveys the current implementation (architecture, source code, deployed services)
  3. Identifies gaps and required changes
  4. Produces an impact analysis table
  5. Writes a transition plan if services or infrastructure are being replaced

Output sections:
  Summary            What the spec introduces in 2-3 sentences
  Current State      What already exists that is relevant
  Impact Analysis    Table of all areas affected and change type
  Dependencies       New packages, services, or infrastructure required
  Risk Assessment    What could break, what needs careful migration
  Transition Plan    Step-by-step plan (only if something is being replaced)
  Implementation     Ordered task list for implementing the spec
```

---

## Step 1 — Parse arguments and locate the project

Parse `$ARGUMENTS`:

- If two tokens where the first looks like a project ID (`001`, `1`, `project-001`, `Project-001`): set `PROJECT_ID` = first token, `SPEC_ARG` = second token.
- If one token that looks like a project ID: set `PROJECT_ID` = that token, `SPEC_ARG` = empty.
- If one token that does not look like a project ID: try to detect the project from the current working directory. If the cwd is inside a `project-NNN/` directory, use that project. Otherwise ask: "Which project are you working on?" and stop until the user responds.
- If no arguments: ask "Which project and spec would you like to review? e.g. `/spec-review 001 signal-relay-server`" and stop.

Normalize `PROJECT_ID` to the zero-padded three-digit format (`001`, `042`, etc.). The project directory is `project-NNN/` (lowercase).

Verify the project directory exists at `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/`. If it does not, report the path checked and stop.

---

## Step 2 — Locate the spec file

The spec directory is: `/Users/ppowell/Documents/vibe-coder-framework/project-NNN/docs/specs/`

If `SPEC_ARG` is empty:
- List all `.md` files in the spec directory.
- Print the list and ask: "Which spec would you like to review?" Stop until the user responds.

If `SPEC_ARG` is provided:
- Try in order:
  1. Exact path if it looks like a full or relative path (contains `/` or ends in `.md`)
  2. `docs/specs/<SPEC_ARG>.md`
  3. `docs/specs/<SPEC_ARG>` (exact filename)
  4. Fuzzy: any `.md` file in `docs/specs/` whose name contains `SPEC_ARG` (case-insensitive)
- If no match: list available specs and stop with: "Spec '`SPEC_ARG`' not found. Available specs are listed above."
- If multiple fuzzy matches: list them and ask the user to be more specific.

Read the spec file.

---

## Step 3 — Read the current architecture context

Read all of the following that exist:

- `project-NNN/CLAUDE.md` — project conventions, hard rules, current phase
- `project-NNN/docs/architecture.md` — architectural decisions and current tech stack
- `project-NNN/docs/implementation-guide.md` — implementation guidance

List all spec files in `project-NNN/docs/specs/`. For each spec file other than the one being reviewed, read its first 50 lines to understand what it covers. Read any specs that appear to overlap with or be referenced by the target spec.

---

## Step 4 — Survey the current implementation

Based on what the target spec describes, identify which source modules are relevant. The source tree is at `project-NNN/src/`.

For each relevant module (e.g., `src/opnsense/`, `src/n8n/`, `src/scanner/`, `src/auth/`):
- List the files in the module
- Read the `__init__.py`, `models.py`, `client.py`, and `mcp_tools.py` (or equivalents) to understand what is already implemented

Also check:
- `project-NNN/infra/` — deployed infrastructure (docker-compose files, service configs)
- `project-NNN/pyproject.toml` — current dependencies

Use Grep to search for symbols, class names, or service names from the spec that may already exist in the codebase. For example, if the spec introduces a `SignalClient`, grep for it. This confirms what is already implemented vs. what is net-new.

---

## Step 5 — Produce the analysis

Output the following sections in order. Use markdown headings.

### A. Summary

2–3 sentences describing what this spec introduces: the component, its purpose, and how it fits into the broader system.

---

### B. Current State

Describe what currently exists that is relevant to this spec:

- **Implemented:** Source modules, deployed services, existing specs that cover overlapping ground
- **Partial:** Things started but not complete (code stubs, placeholder configs, deferred decisions)
- **Absent:** What the spec requires that does not exist at all yet

If the spec is for something entirely new with no overlap, say so explicitly.

---

### C. Impact Analysis

Produce a table covering every area the spec touches:

| Area | Current State | Required State | Change Type | Effort |
|---|---|---|---|---|

**Change Type** values:
- **New** — does not exist; must be built from scratch
- **Extend** — exists but needs new features or fields added
- **Modify** — existing code/config changes significantly
- **Replace** — existing component is being swapped out for something new
- **Deprecate** — existing component becomes unused after this spec is implemented
- **No Change** — referenced but unaffected

**Effort** values: `Low` / `Medium` / `High`

Cover these areas where applicable: source packages, CLI commands, MCP tools, data models, database schema, infrastructure (Docker, services), secrets/credentials, configuration/env vars, external service accounts, tests, documentation.

---

### D. Dependencies

List everything new this spec requires that is not already present:

**Python packages** (not already in `pyproject.toml`):
- `package-name` — reason needed

**Infrastructure / services**:
- Service name, where it runs, how it is deployed

**External accounts / API credentials**:
- What needs to be provisioned before implementation can start

**SOPS secrets**:
- New keys that need to be added to `secrets.encrypted.yaml`

If nothing new is required, say so.

---

### E. Risk Assessment

Identify specific risks for this implementation:

- **Breaking changes** — anything that changes an existing interface that callers depend on
- **Data migration** — schema changes, data transformation, or re-indexing required
- **Service downtime** — any period where an existing service must be stopped to deploy the change
- **Integration surface** — other components (n8n, MCP server, CLI) that will need updates to work with this change
- **Credential/secret rotation** — any existing credentials that need to change
- **Rollback complexity** — how hard it is to undo if something goes wrong

Rate each risk: **Low** / **Medium** / **High**

If there are no significant risks, say so.

---

### F. Transition Plan

**Only write this section if the Impact Analysis contains any `Replace` or `Deprecate` rows, or if the Risk Assessment contains Medium or High risks.**

If none of the above apply, write: `No transition plan required — this spec introduces only new components with no impact on existing services.`

If a transition plan is needed, structure it as follows:

#### Phase 1 — Prerequisites
Everything that must be done *before* any code is written or deployed:
- Provision accounts, API tokens, or infrastructure
- Add secrets to SOPS
- Any decisions that must be made first

**Verify:** How to confirm Phase 1 is complete before moving on.

#### Phase 2 — Build and deploy new component
Implement the spec alongside the existing system without removing anything:
- Ordered implementation tasks (which source files first, which last)
- Infrastructure to deploy
- Configuration to add

**Verify:** Smoke tests or checks to confirm the new component works in isolation.

#### Phase 3 — Integration and cutover
Wire the new component into the rest of the system:
- Update callers (n8n workflows, MCP server registrations, CLI commands)
- Migrate any data if required
- Cutover traffic or usage from old to new

**Verify:** End-to-end test sequence to confirm full integration.

#### Phase 4 — Decommission (if applicable)
Remove or disable the old component:
- What to remove (source files, docker services, secrets, env vars)
- Order of removal (remove callers before removing the service)

**Rollback:** If Phase 4 must be reversed, what to restore and how.

---

### G. Implementation Order

A flat ordered list of concrete tasks to implement this spec from zero to done. Each task should be specific enough to act on in a single session. Format:

```
[ ] 1. Task description — what file or service, what specifically to do
[ ] 2. ...
```

Group tasks by phase if a transition plan was written. Otherwise list them sequentially by logical dependency order (infrastructure before code, models before tools, tools before CLI, unit tests alongside implementation).

---

## Step 6 — Offer to write the transition plan as a document

After outputting the analysis, ask:

> "Would you like me to save the transition plan to `docs/specs/<spec-name>-transition-plan.md`?"

If the user says yes, write the transition plan (Sections F and G) to that file. Do not write Section A–E — those are analysis outputs for the current session, not persistent artifacts.

Do not commit — writing the transition plan file is the end of this skill's scope.
