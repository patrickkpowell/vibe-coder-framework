# Abstract
This file serves as top-level guidance for starting projects. Project files should be treated as high-level planning and represent the first step in the project workflow.

## Overall Guidance
- All code will be its own git repository.
- All code in each repository will be committed to GitHub.
- No credentials will ever be stored in git — credentials always go in `.env` files, which are always listed in `.gitignore` from step one.
- Every project directory will have a `CLAUDE.md` file defining project conventions, coding standards, and persistent context for Claude Code sessions.
- Create appropriate Claude Code Agent Teams for each project (see Agent Team Guidance below).
- Create Claude Code skills when a multi-step operation will be repeated across projects or sessions.

## Project Directory Standard Structure
Every project must be initialized with the following structure:

```
project-name/
├── .gitignore          # Always includes .env, credentials, secrets
├── .env.example        # Template showing required env vars (no real values)
├── CLAUDE.md           # Claude Code persistent context and project conventions
├── README.md           # Project overview and setup instructions
├── docs/
│   ├── architecture.md # Architectural decisions and guidelines
│   └── specs/          # API contracts, data models, user stories
├── src/                # Application source code
├── tests/              # Unit and integration tests
└── infra/              # Infrastructure setup scripts (docker-compose, makefiles, etc.)
```

## Session Startup Ritual
At the start of every Claude Code session:
1. Read `CLAUDE.md` to restore project conventions and context.
2. Read `docs/architecture.md` to restore architectural decisions.
3. Review open tasks or the current epic/story in scope before writing any code.

---

## Discussion-Driven Development

Every project is built through a structured conversation with AI at each stage. The main project file (e.g., `Project-001.md`) is intentionally high-level — it is the starting point for discussion, not a finished specification.

### How it works

**Project Kick Off Discussion** — Before any implementation begins, have a full discussion with AI covering all phases of the project. This is where language, databases, infrastructure, RAG strategy, credential handling, tooling, and deployment approach are decided. The outcomes of this discussion are captured in `docs/architecture.md` and an `docs/implementation-guide.md` within the project folder.

**Phase-Level Discussion** — Before entering each development phase, have a focused discussion specific to that phase. Decisions made here are captured in a spec under `docs/specs/` before any code is written.

**No implementation code is written before the relevant discussion is complete and its decisions are documented.**

---

## Project Workflow

The workflow below is **iterative, not linear**. Architecture decisions frequently need revisiting during development. The Kick Off and Development phases can and should feed back into each other.

---

### Phase 1: Initial Project Setup
#### Objective
Provision the directory structure and resources for the project.

#### Entry Criteria
- An idea

#### Exit Criteria
- Project directory created with standard structure
- Git repository initialized and pushed to GitHub
- High-level project description written

#### Steps
1. Create a top-level project file (e.g., `Project-001.md`) with a high-level description of the project goals, intended users, and rough scope.
2. Initialize a git repository and create the standard directory structure defined above.
3. Create `.gitignore` immediately — before any other files. Always include: `.env`, `*.key`, `*.pem`, `credentials.*`, and any language-specific ignores.
4. Create `.env.example` listing all environment variables the project will need (with placeholder values, never real ones).
5. Create a stub `CLAUDE.md` with the project name and a placeholder for conventions — this will be filled in during Kick Off.
6. Make an initial commit and push to GitHub.

---

### Phase 2: Kick Off — Architecture and Design
#### Objective
An engineering kick off equivalent to agile sprint planning. Major design decisions are made here and captured in architectural guideline files. **This phase is repeatable** — return here whenever requirements change or new decisions are needed.

#### Entry Criteria
- High-level project description

#### Exit Criteria
- `docs/architecture.md` written and committed
- `CLAUDE.md` updated with project-specific conventions
- Key specs (data models, API contracts) written into `docs/specs/`

#### Steps
1. Analyze the project requirements and identify unknowns.
2. Develop a decision questionnaire covering at minimum:
   - What databases are needed and what type (relational, document, key-value)?
   - What development frameworks and languages?
   - What external APIs or services are required?
   - What are the authentication and authorization requirements?
   - What are the logging and error handling patterns?
   - What is the deployment target (local, cloud, containerized)?
3. Most projects will start as CLI tools but must be designed so the core logic can later be exposed through a UI or API layer without major refactoring.
4. Write `docs/architecture.md` capturing all decisions and their rationale.
5. Update `CLAUDE.md` with: coding conventions, naming standards, patterns to use, patterns to avoid, and any project-specific Claude instructions.
6. Write initial specs into `docs/specs/` — data models, API contracts, or user stories as appropriate for the project.
7. Commit and push all architectural artifacts before development begins.

---

### Phase 3: Development Infrastructure Deployment
#### Objective
Deploy required infrastructure for the project such as web servers, application servers, databases, etc. All infrastructure must be easily reproducible.

#### Entry Criteria
- `docs/architecture.md` completed

#### Exit Criteria
- All development infrastructure deployed and accessible
- Infrastructure setup is scripted and repeatable

#### Steps
1. Identify all infrastructure resources needed based on architectural guidelines.
2. Write setup scripts or a `docker-compose.yml` in `infra/` so the environment can be torn down and rebuilt in one command.
3. Set up local resources wherever possible (web servers, databases, message queues, etc.) — minimize cloud dependencies during development.
4. Deploy infrastructure and verify all services are accessible.
5. Generate mock data where needed and store generation scripts (not the data itself if large) in `infra/`.
6. Document the infrastructure setup and teardown process in `README.md`.

---

### Phase 4: Project Development
#### Objective
Write and refactor code. Development communicates with Unit Testing in an iterative loop until all tests pass or a configurable iteration limit is reached. **AI-generated code must be reviewed by a human before it is merged.**

#### Entry Criteria
- `docs/architecture.md` completed
- All development infrastructure deployed and accessible
- Specs in `docs/specs/` are current

#### Exit Criteria
- Code written and linter passes
- No secrets or credentials in source files
- Human code review completed
- Code committed to a feature branch (not directly to `main`)

#### Steps
1. Break work into epics → stories → tasks. Each Claude Code session should have a bounded, focused task scope.
2. Write or refactor code based on the latest architectural guidelines and specs.
3. Create configuration files where necessary:
   - All infrastructure connections (hostnames, ports, paths) must be user-configurable via environment variables.
   - Reference `.env.example` for required variables — never hardcode connection strings.
   - Credentials go in `.env` only, never in source files.
4. Run the linter and static analysis tools before committing.
5. Run a secret scanner (e.g., `git-secrets` or `trufflehog`) before committing.
6. Create a pull request for human review before merging to `main`.

#### Branching Strategy
- `main` — stable, always deployable
- `feature/<short-description>` — all development work
- Merge to `main` via pull request only, after tests pass and code is reviewed

---

### Phase 5: Project Unit Testing
#### Objective
Ensure code changes did not unexpectedly affect other functionality. Identify dead code. Report failures back to Development.

#### Entry Criteria
- Written and executable code
- Mock data deployed into databases and configurations where needed
- All development infrastructure deployed and accessible

#### Exit Criteria
- All unit tests pass
- Dead code report generated
- Results reported back to Development if failures exist

#### Steps
1. Create, modify, or re-use mock data and assertions as appropriate.
2. Deploy mock data through development infrastructure.
3. Execute unit tests against mock data and assertions.
4. Report dead code.
5. On failure: report specific failures back to Phase 4 (Development). Do not mark the iteration complete until all tests pass or the iteration limit is reached.

---

### Phase 6: Integration Testing
#### Objective
Verify that application components communicate correctly with each other and with external infrastructure (databases, APIs, services). This is distinct from unit testing, which tests individual functions in isolation.

#### Entry Criteria
- All unit tests passing
- All development infrastructure deployed and accessible

#### Exit Criteria
- All integration tests pass
- End-to-end flows verified against real (or realistic mock) infrastructure

#### Steps
1. Identify all integration points: database queries, API calls, service-to-service communication.
2. Write integration tests that exercise these points against the deployed development infrastructure.
3. Execute integration tests.
4. On failure: report back to Phase 4 (Development).

---

## Agent Team Guidance
When creating Claude Code Agent Teams, consider these roles:

- **Architect Agent** — Responsible for reviewing and updating `docs/architecture.md`. Runs during Kick Off and whenever requirements change.
- **Developer Agent** — Writes and refactors code within a bounded task scope. Always reads `CLAUDE.md` and current specs before starting.
- **Test Agent** — Writes and executes unit and integration tests. Reports failures with specificity.
- **Infrastructure Agent** — Manages `infra/` scripts, deploys and verifies local infrastructure.
- **Review Agent** — Reviews AI-generated code for correctness, security issues, and adherence to architectural guidelines before merge.

Use multi-agent setups when tasks are clearly parallelizable (e.g., writing tests while another agent writes code). Keep single-agent sessions for tasks requiring tight sequential context.

---

## Security Checklist (run before every commit)
- [ ] No credentials, API keys, or tokens in any source file
- [ ] `.env` is in `.gitignore` and not staged
- [ ] `.env.example` is up to date with any new variables added
- [ ] No `TODO: add real key` or similar placeholders that mask missing `.gitignore` entries
- [ ] Secret scanner has been run
