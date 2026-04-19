#!/usr/bin/env bash
# Wrapper called by PreToolUse hook — runs sync.sh once per Claude session.
# Uses PPID (the Claude Code process) as a stable per-session identifier.

MARKER="/tmp/vibe-coder-synced-${PPID}"

if [[ -f "$MARKER" ]]; then
  exit 0
fi

touch "$MARKER"

bash "$(dirname "${BASH_SOURCE[0]}")/sync.sh"
