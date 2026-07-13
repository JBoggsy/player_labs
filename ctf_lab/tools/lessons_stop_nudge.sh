#!/usr/bin/env bash
# Stop hook: block ONCE per session if substantive work happened but the
# tentative-lessons buffer is untouched (James, 2026-07-10).
#
# This is the hardest mechanically-available end-of-session guarantee: a script
# can't write good lessons, but it CAN refuse to let the agent stop until it
# either writes them or explicitly states there are none. Fires at most once per
# session, and only when:
#   - the rotation hook recorded a baseline hash for this session, AND
#   - the buffer's hash still equals that baseline (untouched), AND
#   - the transcript shows substantive work (>= TOOL_USE_MIN tool uses).
#
# Stdin: hook JSON {session_id, transcript_path, stop_hook_active, ...}.
# Stdout: {"decision":"block","reason":...} to nudge; nothing to allow the stop.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUFFER="$REPO/ctf_lab/TENTATIVE_LESSONS.md"
STATE_DIR="${TMPDIR:-/tmp}"
TOOL_USE_MIN=15

INPUT="$(cat 2>/dev/null || true)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)"
TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)"
STOP_ACTIVE="$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null || echo false)"

# Never re-block a continuation we ourselves caused, and never block twice.
[[ -n "$SESSION_ID" ]] || exit 0
[[ "$STOP_ACTIVE" == "true" ]] && exit 0
MARKER="$STATE_DIR/claude_ctf_lessons_nudged_$SESSION_ID"
[[ -f "$MARKER" ]] && exit 0

BASELINE_FILE="$STATE_DIR/claude_ctf_lessons_baseline_$SESSION_ID"
[[ -f "$BASELINE_FILE" && -f "$BUFFER" ]] || exit 0
BASELINE="$(cat "$BASELINE_FILE")"
CURRENT="$( { md5 -q "$BUFFER" 2>/dev/null || md5sum "$BUFFER" 2>/dev/null | cut -d' ' -f1; } )"
[[ "$CURRENT" == "$BASELINE" ]] || exit 0   # buffer was touched — all good

# Substantive-work proxy: enough tool uses in the transcript.
[[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]] || exit 0
TOOL_USES="$(grep -c '"type":"tool_use"' "$TRANSCRIPT" 2>/dev/null || echo 0)"
[[ "$TOOL_USES" -ge "$TOOL_USE_MIN" ]] || exit 0

touch "$MARKER"
jq -n '{decision: "block",
        reason: "Lessons check (automated, fires once per session): this session did substantive work but ctf_lab/TENTATIVE_LESSONS.md is untouched. Before stopping, either (a) add the session'\''s candidate tentative lessons to that buffer — eagerly, noise is fine — or (b) if you judge there are genuinely none, append a one-line entry saying so with a short justification. Then finish your reply."}'
