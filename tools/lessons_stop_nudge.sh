#!/usr/bin/env bash
# Stop hook: block ONCE per session if substantive work happened in one or more
# game labs but those labs' tentative-lessons buffers are untouched (James, 2026-07-13).
#
# ONE repo-wide hook — replaces the old per-lab nudges, which all fired on every
# stop regardless of which labs the session touched. A lab counts as "worked on"
# when its directory path appears often enough inside the transcript's tool_use
# lines (raw transcript mentions are too noisy — the SessionStart context alone
# names every lab); its buffer counts as "untouched" when it has no `### ` lesson
# entries (the rotated fresh buffer has none). The nudge names ONLY the
# worked-on, untouched labs and instructs the agent not to add entries to labs
# it didn't work in.
#
# Stdin: hook JSON {session_id, transcript_path, stop_hook_active, ...}.
# Stdout: {"decision":"block","reason":...} to nudge; nothing to allow the stop.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${TMPDIR:-/tmp}"
TOOL_USE_MIN=15        # substantive-work proxy: tool uses in the transcript
LAB_MENTION_MIN=12     # lab-path hits in tool_use lines for it to count as worked-on
LABS=(crewrift_lab cue_n_woo_lab heartleaf_lab ctf_lab)

INPUT="$(cat 2>/dev/null || true)"
SESSION_ID="$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null || true)"
TRANSCRIPT="$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null || true)"
STOP_ACTIVE="$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null || echo false)"

# Never re-block a continuation we ourselves caused, and never block twice.
[[ -n "$SESSION_ID" ]] || exit 0
[[ "$STOP_ACTIVE" == "true" ]] && exit 0
MARKER="$STATE_DIR/claude_lessons_nudged_$SESSION_ID"
[[ -f "$MARKER" ]] && exit 0

# Substantive-work proxy: enough tool uses in the transcript.
[[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]] || exit 0
TOOL_USES="$(grep -c '"type":"tool_use"' "$TRANSCRIPT" 2>/dev/null || true)"
[[ "${TOOL_USES:-0}" -ge "$TOOL_USE_MIN" ]] || exit 0

TOOL_USE_LINES="$(grep '"type":"tool_use"' "$TRANSCRIPT" 2>/dev/null || true)"
UNTOUCHED=()
for LAB in "${LABS[@]}"; do
  BUFFER="$REPO/$LAB/TENTATIVE_LESSONS.md"
  [[ -f "$BUFFER" ]] || continue
  MENTIONS="$(printf '%s' "$TOOL_USE_LINES" | grep -o "$LAB/" | wc -l | tr -d ' ')"
  [[ "${MENTIONS:-0}" -ge "$LAB_MENTION_MIN" ]] || continue   # lab not worked on
  grep -q '^### ' "$BUFFER" && continue                       # lessons written — good
  UNTOUCHED+=("$LAB")
done
[[ "${#UNTOUCHED[@]}" -gt 0 ]] || exit 0

touch "$MARKER"
LAB_LIST="$(printf '%s, ' "${UNTOUCHED[@]}")"
LAB_LIST="${LAB_LIST%, }"
jq -n --arg labs "$LAB_LIST" \
  '{decision: "block",
    reason: ("Lessons check (automated, fires once per session): this session did substantive work in these lab(s) but their TENTATIVE_LESSONS.md buffers are untouched: " + $labs + ". For EACH lab just named — and ONLY those; do not add entries to labs you did not work in this session — either (a) add the session'\''s candidate tentative lessons to <lab>/TENTATIVE_LESSONS.md (eagerly; noise is fine), or (b) if you judge there are genuinely none, append a one-line entry saying so with a short justification. Then finish your reply.")}'
