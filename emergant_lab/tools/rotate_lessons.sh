#!/usr/bin/env bash
# SessionStart hook: archive the previous Emerg-ant lessons buffer and seed a new one.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUFFER="$REPO/emergant_lab/TENTATIVE_LESSONS.md"
ARCHIVE_DIR="$REPO/emergant_lab/lessons_archive"

INPUT="$(cat 2>/dev/null || true)"
SOURCE="$(printf '%s' "$INPUT" | jq -r '.source // "startup"' 2>/dev/null || echo startup)"

emit_context() {
  jq -n --arg ctx "$1" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
}

if [[ "$SOURCE" != "startup" && "$SOURCE" != "clear" ]]; then
  emit_context "Tentative-lessons buffer: emergant_lab/TENTATIVE_LESSONS.md"
  exit 0
fi

mkdir -p "$ARCHIVE_DIR"
if [[ -f "$BUFFER" ]] && grep -q '^### ' "$BUFFER"; then
  STAMP="$(date '+%Y%m%d-%H%M%S')"
  ARCHIVE="$ARCHIVE_DIR/TENTATIVE_LESSONS-$STAMP.md"
  # Avoid minting duplicate recurrence evidence after a git sync restores a buffer.
  DUPLICATE=""
  while IFS= read -r -d '' candidate; do
    if cmp -s "$BUFFER" "$candidate"; then DUPLICATE=1; break; fi
  done < <(find "$ARCHIVE_DIR" -name 'TENTATIVE_LESSONS-*.md' -print0 2>/dev/null)
  [[ -n "$DUPLICATE" ]] || cp "$BUFFER" "$ARCHIVE"
fi

NOW="$(date '+%Y-%m-%d %H:%M')"
printf '# Tentative lessons — current session\n\nRotated %s. Add candidate lessons eagerly under `###` headings.\n' "$NOW" > "$BUFFER"
emit_context "Fresh Emerg-ant tentative-lessons buffer: emergant_lab/TENTATIVE_LESSONS.md"

