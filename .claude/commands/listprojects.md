# /listprojects

List all projects in the framework with titles and descriptions.

## Input

(no arguments)

## Step 1 — Locate projects

Search for all `project-NNN/` directories under the base path `/Users/ppowell/Documents/vibe-coder-framework/`.

For each directory found, extract the project number `NNN` and look for a corresponding `Project-NNN.md` file in the framework root.

## Step 2 — Extract project metadata

For each `Project-NNN.md` file:
1. Read the first line (should be `# <title>`)
2. Read the next few lines to extract a brief description (usually 1–3 sentences)
3. Collect: project ID, title, and description

## Step 3 — Display results

If no projects found, output:
```
No projects found.
```

Otherwise, output a table like this:

```
**Available Projects:**

| Project | Title | Description |
|---------|-------|-------------|
| **001** | Project Title | Brief description from first lines of Project-001.md |
| **002** | Project Title | Brief description from first lines of Project-002.md |

**To load a project context:**

/setproject 001    # Load project-001
/setproject 002    # Load project-002
/setproject 0      # Load framework itself

Which project would you like to work on?
```

---

## Implementation notes

- Sort projects numerically by ID (001, 002, 003, etc.)
- Extract the title from the first `# ` line in each Project-NNN.md file
- Extract description by reading lines 2–4 and joining them, stopping at the first blank line or `---` separator
- Truncate descriptions to ~100 characters if they exceed that length, ending with `…`
- Format the table in GitHub-flavored markdown
