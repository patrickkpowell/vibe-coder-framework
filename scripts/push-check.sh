#!/usr/bin/env bash
# Runs on session Stop — warns about unpushed commits or uncommitted changes.

FRAMEWORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISSUES=()

check_repo() {
  local dir="$1"
  local name="$2"

  [[ ! -d "$dir/.git" ]] && return

  if ! git -C "$dir" remote | grep -q .; then
    return
  fi

  local branch
  branch=$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)

  if git -C "$dir" rev-parse --verify "origin/$branch" &>/dev/null; then
    local ahead
    ahead=$(git -C "$dir" rev-list --count "origin/$branch..HEAD" 2>/dev/null || echo 0)
    [[ "$ahead" -gt 0 ]] && ISSUES+=("$name ($branch): $ahead unpushed commit(s)")
  fi

  if ! git -C "$dir" diff --quiet || ! git -C "$dir" diff --cached --quiet; then
    ISSUES+=("$name: uncommitted changes")
  fi
}

check_repo "$FRAMEWORK_DIR" "vibe-coder-framework"

for dir in "$FRAMEWORK_DIR"/project-*/; do
  check_repo "$dir" "$(basename "$dir")"
done

if [[ "${#ISSUES[@]}" -gt 0 ]]; then
  echo ""
  echo "WARNING: Unsync'd work detected — push before switching machines!"
  for item in "${ISSUES[@]}"; do
    echo "   • $item"
  done
  echo ""
fi
