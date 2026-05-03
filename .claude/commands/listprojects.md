# /listprojects

List all projects in the framework with titles and descriptions.

## Input

(no arguments)

## Step 1 — Locate projects

Search for all `project-NNN/` directories under the base path `/Users/ppowell/Documents/vibe-coder-framework/`.

For each directory found, extract the project number `NNN` and look for a corresponding `Project-NNN.md` file in the framework root.

## Step 2 — Extract project metadata

For each `Project-NNN.md` file found:
1. Read the first line (should be `# <title>`)
2. Extract description from lines 2–4:
   - Skip header lines and markdown blocks (lines starting with `##`, `|`, or `###`)
   - Join lines with spaces
   - Take the first sentence or ~80 characters, whichever comes first
   - Clean up markdown formatting
3. Collect: project ID (zero-padded to 3 digits), title, and description

## Step 3 — Display results

If no projects found, output:
```
No projects found.
```

Otherwise, output a table with all projects sorted by ID:

```
**Available Projects:**

| Project | Title | Description |
|---------|-------|-------------|
| **001** | Network and Systems Engineer | Central knowledge base for network and system information collection… |
| **002** | Project 002 — Elasticsearch Cluster Engineering Platform | CLI-first platform for managing isolated Elasticsearch ECK deployments… |

**To load a project context:**

    /setproject 001    # Load project-001
    /setproject 002    # Load project-002
    /setproject 0      # Load framework itself

Which project would you like to work on?
```

---

## Implementation notes

- Sort projects numerically by ID (001, 002, 003, etc.)
- Extract title from the first `# ` line
- Skip lines starting with `##`, `###`, `|`, `---` (markdown formatting)
- Truncate descriptions to ~80 characters if they exceed that, ending with `…`
- Join multi-line descriptions with single spaces
- Format the table in GitHub-flavored markdown
