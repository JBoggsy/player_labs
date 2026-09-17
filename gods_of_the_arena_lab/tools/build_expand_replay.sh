#!/bin/sh
# Build the Gods of the Arena replay expander against a polyworld commit.
#
# Usage: build_expand_replay.sh [POLYWORLD_COMMIT]
# Default commit: the league's deployed commit as printed by tools/deployed_ref.py
# ("deployed commit : <sha>"). Replays only re-simulate at their recording commit.
#
# Output: gods_of_the_arena_lab/tools/bin/expand_replay-<sha> (gitignored).
# Needs: nim 2.x on PATH, git, network on first use. The polyworld clone and its
# dependency cache live under gods_of_the_arena_lab/tools/.cache/.
set -eu
LAB=$(cd "$(dirname "$0")/.." && pwd)
TOOLS="$LAB/tools"
CACHE="$TOOLS/.cache"
COMMIT=${1:-}
if [ -z "$COMMIT" ]; then
  COMMIT=$(cd "$LAB/.." && .venv/bin/python gods_of_the_arena_lab/tools/deployed_ref.py | sed -n 's/^deployed commit *: *//p')
fi
[ -n "$COMMIT" ] || { echo "could not resolve the deployed commit" >&2; exit 1; }
SHORT=$(printf '%s' "$COMMIT" | cut -c1-8)
OUT="$TOOLS/bin/expand_replay-$SHORT"
if [ -x "$OUT" ] && [ "$OUT" -nt "$TOOLS/expand_replay.nim" ] && [ "$OUT" -nt "$0" ]; then
  echo "$OUT"
  exit 0
fi
mkdir -p "$CACHE" "$TOOLS/bin"
CLONE="$CACHE/polyworld"
if [ ! -d "$CLONE/.git" ]; then
  git clone -q https://github.com/Metta-AI/polyworld.git "$CLONE"
fi
git -C "$CLONE" fetch -q origin "$COMMIT" 2>/dev/null || git -C "$CLONE" fetch -q origin
git -C "$CLONE" checkout -q "$COMMIT"
# polyworld's own dependency sync: pins every Nim package the sim needs.
(cd "$CLONE" && nim r --hints:off coworld/tools/sync_dependencies.nim >/dev/null)
export POLYWORLD_DEPS="$CLONE/tmp/coworld/deps"
# Compile from inside the clone so its config.nims applies (dependency paths),
# with the game modules and our source on the path.
cp "$TOOLS/expand_replay.nim" "$CLONE/examples/gods_of_the_arena/tools/lab_expand_replay.nim"
(cd "$CLONE" && nim c --hints:off -d:release --nimcache:"$CACHE/nimcache-$SHORT" \
  -o:"$OUT" examples/gods_of_the_arena/tools/lab_expand_replay.nim)
echo "$OUT"
