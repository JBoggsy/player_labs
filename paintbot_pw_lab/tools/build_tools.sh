#!/usr/bin/env bash
# Build the paintbot-pw engine binaries the lab uses, pinned to one release tag.
#
#   paintbot_pw_lab/tools/build_tools.sh [coworld-vX.Y.Z]    # default: PW_RELEASE_TAG below
#
# Produces, in paintbot_pw_lab/tools/bin/<tag>/:
#   paintbot-headless   hash-checked replay validator and native runner
#                       (--replay FILE; --bot a.bas:N --seed S --ticks T --record out.replay)
#   replay_stats        the repo's per-team summary (NOT hash-checked; see docs/evidence-pipeline.md)
# and leaves a worktree at paintbot_pw_lab/tools/.cache/<tag>/ whose tmp/paintbot-coworld engine
# lets coworld/paintbot/local.py run there.
#
# The source clone (~/coding/coworlds/paintbot-pw, override with PW_CLONE) is only fetched;
# its own checkout is never changed. A newer build replays older rules versions hash-exactly,
# so building the league's current tag is enough for analysis.
set -euo pipefail

PW_RELEASE_TAG="coworld-v0.3.65"   # 7b2b19f5, the release the docs are verified against
TAG="${1:-$PW_RELEASE_TAG}"
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLONE="${PW_CLONE:-$HOME/coding/coworlds/paintbot-pw}"
TREE="$LAB/tools/.cache/$TAG"
OUT="$LAB/tools/bin/$TAG"

[[ -d "$CLONE/.git" ]] || git clone --filter=blob:none https://github.com/Metta-AI/paintbot-pw.git "$CLONE"
git -C "$CLONE" fetch --quiet --tags origin
git -C "$CLONE" worktree prune
[[ -d "$TREE" ]] || git -C "$CLONE" worktree add --detach "$TREE" "$TAG"

cd "$TREE"
python3 coworld/tools/sync_dependencies.py
export POLYWORLD_DEPS="$TREE/tmp/coworld/deps"
mkdir -p "$OUT"
nim c -d:headless -o:"$OUT/paintbot-headless" examples/paintbot/paintbot.nim
nim c -o:"$OUT/replay_stats" examples/paintbot/replay_stats.nim
nim c -d:coworld -o:tmp/paintbot-coworld examples/paintbot/paintbot.nim
echo "built $TAG ($(git rev-parse --short HEAD)) into $OUT; local.py runs from $TREE"
