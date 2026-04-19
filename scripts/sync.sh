#!/usr/bin/env bash
# Syncs vibe-coder-framework and all project-NNN repos with their remotes.

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0
WARNINGS=0

sync_repo() {
  local dir="$1"
  local name="$2"

  if ! git -C "$dir" remote | grep -q .; then
    echo "  ~  $name: no remote configured, skipping"
    ((WARNINGS++))
    return
  fi

  if ! git -C "$dir" fetch origin --quiet 2>&1; then
    echo "  ✗  $name: fetch failed"
    ((ERRORS++))
    return
  fi

  local branch
  branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)

  if ! git -C "$dir" rev-parse --verify "origin/$branch" &>/dev/null; then
    echo "  ~  $name ($branch): no upstream branch, skipping pull"
    ((WARNINGS++))
    return
  fi

  local ahead behind
  ahead=$(git -C "$dir" rev-list --count "origin/$branch..HEAD" 2>/dev/null || echo 0)
  behind=$(git -C "$dir" rev-list --count "HEAD..origin/$branch" 2>/dev/null || echo 0)
  local dirty=false
  git -C "$dir" diff --quiet && git -C "$dir" diff --cached --quiet || dirty=true

  if [[ "$ahead" -gt 0 && "$behind" -gt 0 ]]; then
    echo "  !  $name ($branch): DIVERGED — $ahead ahead, $behind behind. Manual resolution needed."
    ((WARNINGS++))
  elif [[ "$behind" -gt 0 ]]; then
    if [[ "$dirty" == true ]]; then
      git -C "$dir" stash --quiet
      git -C "$dir" pull --rebase --quiet
      git -C "$dir" stash pop --quiet 2>/dev/null
      echo "  ↓  $name ($branch): pulled $behind commit(s) (local changes stashed/restored)"
    else
      git -C "$dir" pull --rebase --quiet
      echo "  ↓  $name ($branch): pulled $behind commit(s)"
    fi
  elif [[ "$ahead" -gt 0 ]]; then
    echo "  ↑  $name ($branch): $ahead unpushed commit(s) — push before switching machines"
    ((WARNINGS++))
  else
    echo "  ✓  $name ($branch): up to date"
  fi
}

echo "=== Vibe Coder Framework Sync ==="
echo ""
echo "Framework:"
sync_repo "$FRAMEWORK_DIR" "vibe-coder-framework"
echo ""
echo "Projects:"
found=0
for dir in "$FRAMEWORK_DIR"/project-*/; do
  if [[ -d "$dir/.git" ]]; then
    sync_repo "$dir" "$(basename "$dir")"
    ((found++))
  fi
done
[[ "$found" -eq 0 ]] && echo "  (no projects found)"
echo ""

if [[ "$ERRORS" -gt 0 ]]; then
  echo "Done — $ERRORS error(s), $WARNINGS warning(s)."
  exit 1
elif [[ "$WARNINGS" -gt 0 ]]; then
  echo "Done — $WARNINGS warning(s). Review items marked with ↑ or ! before switching machines."
else
  echo "All repos in sync."
fi
