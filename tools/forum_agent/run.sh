#!/bin/zsh
# Run the lab's forum agent once for one Coworld.
#
# Usage: tools/forum_agent/run.sh <path-to-lab-brief.md>
#
# Builds the prompt from the game-agnostic operating rules (prompt.md, next to this
# script) plus the lab's brief, and runs headless Claude Code in the repository root
# so the agent has the same CLAUDE.md, skills, and memory as interactive sessions.
# Writes are restricted to the community CLI and repository files; the agent never
# commits. Schedule it with launchd (see README.md).

set -euo pipefail

BRIEF="${1:?usage: run.sh <lab brief.md>}"
HERE="${0:A:h}"
REPO="${HERE:h:h}"
CLAUDE="${CLAUDE_BIN:-$HOME/.local/bin/claude}"

export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

cd "$REPO"

PROMPT="$(cat "$HERE/prompt.md"; printf '\n\n---\n\n# Lab brief\n\n'; cat "$BRIEF")"

exec "$CLAUDE" -p "$PROMPT" \
  --permission-mode acceptEdits \
  --allowedTools \
    "Bash(uv run python tools/coworld_community.py:*)" \
    "Bash(cat:*)" "Bash(ls:*)" "Bash(grep:*)" "Bash(sed -n:*)" "Bash(date:*)" \
    Read Write Edit Glob Grep \
  --max-turns 60 \
  --output-format text
