#!/bin/zsh
# Backfill results.json for every episode dir under $1 (fetch_artifacts layout:
# <dir>/<stamp>_ereq_<8+2hex> — the full ereq id lives in episode.json's id field).
set -u
root="$1"
ok=0; fail=0
for d in "$root"/*_ereq_*; do
  [ -d "$d" ] || continue
  [ -f "$d/results.json" ] && { ok=$((ok+1)); continue; }
  eid=$(python3 -c "import json;print(json.load(open('$d/episode.json'))['id'])" 2>/dev/null)
  [ -n "$eid" ] || { fail=$((fail+1)); continue; }
  if uv run coworld episode-results "$eid" -o "$d/results.json" >/dev/null 2>&1; then
    ok=$((ok+1))
  else
    fail=$((fail+1))
  fi
done
echo "results present: $ok  failed: $fail"
