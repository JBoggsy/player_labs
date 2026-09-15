#!/usr/bin/env bash
# SessionStart: point the agent at current lab knowledge without changing files.
set -eu
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="${1:?Pass the game lab directory name}"
[[ "$LAB" == *_lab && "$LAB" != */* && -d "$REPO/$LAB" ]] || exit 1
cat >/dev/null
jq -n --arg ctx "Read $LAB/WORKING_CONTEXT.md and $LAB/TENTATIVE_LESSONS.md. Keep supported guidance current; replace resolved questions and superseded claims in place. Follow docs/learning.md." \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
