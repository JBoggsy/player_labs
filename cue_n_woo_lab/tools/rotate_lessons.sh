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

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUFFER="$REPO/cue_n_woo_lab/TENTATIVE_LESSONS.md"
ARCHIVE_DIR="$REPO/cue_n_woo_lab/lessons_archive"

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
STAMP="$(date '+%Y%m%d-%H%M%S')"

if [[ "$SOURCE" != "startup" && "$SOURCE" != "clear" ]]; then
  # Resumed/compacted session: same session, do NOT rotate. Just point at the buffer.
  emit_context "Tentative-lessons buffer (this session's, write lessons AS YOU GO): cue_n_woo_lab/TENTATIVE_LESSONS.md"
  exit 0
fi

mkdir -p "$ARCHIVE_DIR"
ARCHIVED=""
SKIPPED_DUP=""
if [[ -f "$BUFFER" ]] && grep -q '^### ' "$BUFFER"; then
  if buffer_is_already_archived; then
    SKIPPED_DUP=1
  else
    ARCHIVE_FILE="$ARCHIVE_DIR/TENTATIVE_LESSONS-$STAMP.md"
    mv "$BUFFER" "$ARCHIVE_FILE"
    ARCHIVED="$(basename "$ARCHIVE_FILE")"
  fi
fi

cat > "$BUFFER" << EOF
# Cue-n-Woo tentative lessons — session buffer

**Session started:** $NOW. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[\`lessons_archive/\`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
\`cue_n_woo_lab/tools/rotate_lessons.sh\`) → periodic human+agent review
(\`/lessons-review\`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to \`best_practices.md\` (Cue-n-Woo-specific) or the root
\`best_practices.md\` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** \`### <lesson, one line>\` then \`Evidence:\` (what you observed,
concrete) and optional \`Status:\` notes. Terse. One lesson per \`###\`.

---
EOF

if [[ -n "$ARCHIVED" ]]; then
  CTX="Tentative-lessons buffer rotated: previous session's lessons archived to cue_n_woo_lab/lessons_archive/$ARCHIVED. Fresh buffer: cue_n_woo_lab/TENTATIVE_LESSONS.md — write candidate lessons there AS YOU GO."
elif [[ -n "$SKIPPED_DUP" ]]; then
  CTX="Fresh tentative-lessons buffer: cue_n_woo_lab/TENTATIVE_LESSONS.md (previous buffer was a byte-identical copy of an existing archive - likely restored by a git sync; not re-archived) - write candidate lessons there AS YOU GO."
else
  CTX="Fresh tentative-lessons buffer: cue_n_woo_lab/TENTATIVE_LESSONS.md (previous buffer was empty; nothing archived) — write candidate lessons there AS YOU GO."
fi

# Keep git tidy: commit the rotation if the tree allows it (best effort, never block).
if [[ -n "$ARCHIVED" ]]; then
  git -C "$REPO" add "$BUFFER" "$ARCHIVE_DIR" >/dev/null 2>&1 \
    && git -C "$REPO" commit -q -m "lessons: rotate cue-n-woo session buffer -> lessons_archive/$ARCHIVED (SessionStart hook)" \
       -- "$BUFFER" "$ARCHIVE_DIR" >/dev/null 2>&1 \
    || true
fi

emit_context "$CTX"
