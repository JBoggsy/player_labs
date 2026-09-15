#!/usr/bin/env bash
# SessionStart hook: rotate the tentative-lessons buffer (James, 2026-06-12).
#
# Mechanism, not trust: on every NEW session (source = startup|clear — never
# resume/compact), the previous session's buffer is archived with a timestamp and
# a fresh, stamped buffer is created. The agent is pointed at it via
# additionalContext.
#
# Stdin: hook JSON {session_id, source, ...}. Stdout: hook JSON (additionalContext).
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB="${1:?Pass the game lab directory name}"
[[ "$LAB" == *_lab && "$LAB" != */* && -d "$REPO/$LAB" ]] || exit 1
BUFFER="$REPO/$LAB/TENTATIVE_LESSONS.md"
ARCHIVE_DIR="$REPO/$LAB/lessons_archive"

INPUT="$(cat 2>/dev/null || true)"
SOURCE="$(printf '%s' "$INPUT" | jq -r '.source // "startup"' 2>/dev/null || echo startup)"

emit_context() {
  jq -n --arg ctx "$1" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
}

hash_file() {
  if command -v md5 >/dev/null 2>&1; then md5 -q "$1"; else md5sum "$1" | cut -d" " -f1; fi
}

# A git sync/merge can restore an already-archived buffer; re-archiving it under
# a new timestamp mints byte-identical duplicate archives and inflates the
# recurrence signal /lessons-review graduates on (seen in 3 labs, 2026-07-13).
buffer_is_already_archived() {
  local buf_md5 f
  buf_md5="$(hash_file "$BUFFER")" || return 1
  while IFS= read -r -d "" f; do
    [[ "$(hash_file "$f")" == "$buf_md5" ]] && return 0
  done < <(find "$ARCHIVE_DIR" -name "TENTATIVE_LESSONS-*.md" -print0 2>/dev/null)
  return 1
}

NOW="$(date '+%Y-%m-%d %H:%M')"
STAMP="$(date '+%Y%m%d-%H%M%S')-$$"

if [[ "$SOURCE" != "startup" && "$SOURCE" != "clear" ]]; then
  # Resumed/compacted session: same session, do NOT rotate. Just point at the buffer.
  emit_context "Tentative-lessons buffer (this session's, write lessons AS YOU GO): $LAB/TENTATIVE_LESSONS.md"
  exit 0
fi

mkdir -p "$ARCHIVE_DIR" || exit 1
ARCHIVED=""
SKIPPED_DUP=""
render_buffer() {
cat << EOF
# $LAB tentative lessons — session buffer

**Session started:** $NOW. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
\`$LAB/lessons_archive/\` and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
\`$LAB/tools/rotate_lessons.sh\`) → periodic human+agent review
(\`/lessons-review\`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to \`best_practices.md\` ($LAB-specific) or the root
\`best_practices.md\` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** \`### <lesson, one line>\` then \`Evidence:\` (what you observed,
concrete) and optional \`Status:\` notes. Terse. One lesson per \`###\`.

---
EOF
}

# Ignore only the generated timestamp when recognizing an unchanged template.
# Any other edit (including nonstandard entries before the divider) is preserved.
buffer_is_empty_template() {
  cmp -s <(sed -E 's/^(\*\*Session started:\*\*) [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}/\1 TIMESTAMP/' "$BUFFER") \
    <(render_buffer | sed -E 's/^(\*\*Session started:\*\*) [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}/\1 TIMESTAMP/')
}

if [[ -s "$BUFFER" ]] && ! buffer_is_empty_template; then
  if buffer_is_already_archived; then
    SKIPPED_DUP=1
  else
    ARCHIVE_FILE="$ARCHIVE_DIR/TENTATIVE_LESSONS-$STAMP.md"
    mv "$BUFFER" "$ARCHIVE_FILE" || exit 1
    ARCHIVED="$(basename "$ARCHIVE_FILE")"
  fi
fi

render_buffer > "$BUFFER" || exit 1

if [[ -n "$ARCHIVED" ]]; then
  CTX="Tentative-lessons buffer rotated: previous session's lessons archived to $LAB/lessons_archive/$ARCHIVED. Fresh buffer: $LAB/TENTATIVE_LESSONS.md — write candidate lessons there AS YOU GO."
elif [[ -n "$SKIPPED_DUP" ]]; then
  CTX="Fresh tentative-lessons buffer: $LAB/TENTATIVE_LESSONS.md (previous buffer was a byte-identical copy of an existing archive - likely restored by a git sync; not re-archived) - write candidate lessons there AS YOU GO."
else
  CTX="Fresh tentative-lessons buffer: $LAB/TENTATIVE_LESSONS.md (previous buffer was empty or an unchanged template; nothing archived) — write candidate lessons there AS YOU GO."
fi

# Rotation stays uncommitted; the normal documentation audit precedes commits.

emit_context "$CTX"
