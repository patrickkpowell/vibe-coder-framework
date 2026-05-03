---
description: Merge worktree branches into main and push to GitHub
argument-hint: [project-id]
allowed-tools: Read, Bash(git -C *:*), Bash(git worktree *:*)
---

The user wants to merge pending branches into main for project: $ARGUMENTS

The projects base directory is: /Users/ppowell/Documents/vibe-coder-framework

## Step 0 — Help check

If `$ARGUMENTS` is exactly `help`, print the following and stop:

```
/merge — merge worktree branches into main and push to GitHub

Usage:
  /merge <project-id>    Merge pending branches for a project
  /merge help            Show this help

Arguments:
  project-id    Accepts: 001, 1, project-001, Project-001, or framework

What it does:
  1. Lists all branches (worktrees and local) with commits ahead of main
  2. Shows the commit log for each branch
  3. Lets you choose which branches to merge
  4. Merges chosen branches into main (fast-forward if possible)
  5. Pushes main to GitHub
  6. Offers to clean up merged worktrees and branches

When to use:
  After completing work in a Claude Code worktree session that you
  want to land on main.
```

---

## Step 1 — Resolve project to a git repo path

The project argument may be provided as `framework`, `001`, `1`, `project-001`, or `Project-001`.

**Special case — `framework` (or empty when context is the framework):**
Use the git repo at: `/Users/ppowell/Documents/vibe-coder-framework`
Refer to this project as "vibe-coder-framework".

**Numbered projects:**
Normalize the number to three digits (e.g., `1` → `001`). The repo path is:
`/Users/ppowell/Documents/vibe-coder-framework/project-NNN`

Store the resolved path as `$REPO`.

If the directory does not exist or is not a git repository, report the path checked and stop.

---

## Step 2 — List branches with pending work

Run the following to discover branches ahead of main:

```
git -C $REPO branch --format="%(refname:short)" | grep -v "^main$"
```

For each branch found, check if it has commits ahead of main:

```
git -C $REPO log --oneline main..<branch>
```

Also list worktrees to cross-reference:

```
git -C $REPO worktree list
```

Build a table of **pending branches** — those with at least one commit ahead of main. For each:
- Branch name
- Number of commits ahead
- Worktree path (if a worktree exists for this branch, show it; otherwise show "no worktree")
- Most recent commit subject

Also check for **uncommitted changes** in each worktree:

```
git -C <worktree-path> status --short
```

If no branches are ahead of main, report: "Nothing to merge — all branches are up to date with main." and stop.

---

## Step 3 — Display summary and ask which to merge

Display a numbered list:

```
Pending branches for [project name]:

  1. claude/serene-neumann-9e5a69   (3 commits)  worktree: .claude/worktrees/serene-neumann-9e5a69
       feat: add /notify skill for Matrix notifications
       feat: add desktop-to-matrix handoff
       docs: update README with notify usage
  2. claude/funny-dubinsky           (1 commit)   no worktree
       fix: correct setproject path normalization

Merge which branches? Enter numbers (e.g. "1 2"), "all", or "none" to cancel.
```

Wait for the user to respond before proceeding.

If the user says "none" or "cancel", stop.

---

## Step 4 — Pre-merge checks

For each selected branch, verify:

1. **No uncommitted changes in the worktree** (if one exists). If there are uncommitted changes, warn:
   ```
   ⚠ Branch <name> has uncommitted changes in its worktree at <path>.
   Commit or discard those changes before merging, or skip this branch.
   ```
   Ask whether to skip this branch or abort entirely. Do not proceed with a dirty worktree.

2. **Merge type** — determine if the merge would be fast-forward:
   ```
   git -C $REPO merge-base --is-ancestor main <branch>
   ```
   - If true: the merge will be fast-forward (clean, no merge commit needed).
   - If false: a merge commit will be created. Show the user the divergence and confirm before proceeding.

---

## Step 5 — Merge into main

Switch to main for the merge operation. Since this is running from a worktree that may itself be on a branch, use `-C $REPO` throughout — do NOT `cd`.

For each selected branch, in order:

**Fast-forward:**
```
git -C $REPO merge --ff-only <branch>
```

**Not fast-forward (requires explicit confirmation from user in Step 4):**
```
git -C $REPO merge --no-ff <branch> -m "Merge branch '<branch>' into main"
```

After each merge, report success or failure. If any merge fails (conflict), stop and report:
```
⚠ Merge conflict on <branch>. Resolve the conflict manually at $REPO, then re-run /merge.
```
Do not attempt further merges after a conflict.

---

## Step 6 — Push to GitHub

After all selected branches have been merged successfully:

```
git -C $REPO push origin main
```

Report the push result. If the push fails (e.g. non-fast-forward rejection), report the error and do NOT force-push. Tell the user to pull and resolve manually.

---

## Step 7 — Offer worktree and branch cleanup

For each successfully merged branch, if a worktree exists:

```
Clean up merged branch "<name>"?
  Worktree at: <path>
  Local branch: <name>
  Remote branch: origin/<name> (if pushed)

Options:
  y   Remove worktree, delete local branch, delete remote branch
  k   Keep everything (leave worktree and branches in place)
```

Wait for a response per branch (or ask once if multiple branches were merged: "Clean up all merged worktrees?").

**If cleanup confirmed:**
```
git -C $REPO worktree remove <path> --force
git -C $REPO branch -d <branch>
git -C $REPO push origin --delete <branch>   # only if the remote branch exists
```

Report what was removed.

**If no worktree:**
Offer to delete the local branch only:
```
Delete local branch "<name>"? (y/n)
```

---

## Step 8 — Final summary

Report what happened:

```
Merge complete for [project name]:
  ✓ Merged: claude/serene-neumann-9e5a69 (3 commits, fast-forward)
  ✓ Merged: claude/funny-dubinsky (1 commit, merge commit)
  ✓ Pushed main to origin
  ✓ Cleaned up: worktree + branch for claude/serene-neumann-9e5a69
  — Kept: worktree + branch for claude/funny-dubinsky (user chose to keep)

main is now at: <commit-hash> <subject>
```
