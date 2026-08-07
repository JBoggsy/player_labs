#!/usr/bin/env bash
# Build the version-matched replay reader for PAINTBOT replays.
#
# Usage: paintbot_lab/tools/build_expand_replay.sh [--ref SHA] [--force] [--run REPLAY]
#
# The reader itself lives in ctf_lab (paintbot is a second manifest over the same
# engine, so the tool is shared). That script defaults to `CTF_REF` — a CTF game
# commit — and the re-sim validates a per-tick hash, so running it bare against a
# Paintbot replay fails the hash and yields no usable events. This wrapper builds
# at the ref this lab is actually pinned to.
#
# It prints the exact per-ref binary path to pass to the bundler's
# `--expand-replay`. Both labs share one `expand_replay_json` symlink in
# ctf_lab/tools/bin/, so whichever lab built last owns it; passing the per-ref
# path explicitly makes the choice unambiguous instead of order-dependent.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # paintbot_lab/
CTF_SCRIPT="$LAB_DIR/../ctf_lab/tools/build_expand_replay.sh"

[[ -x "$CTF_SCRIPT" ]] || {
  echo "build_expand_replay.sh: missing shared reader build script: $CTF_SCRIPT" >&2
  exit 1
}

# PAINTBOT_GAME_REF is this lab's pinned game commit and its game-sync ledger.
# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"

: "${PAINTBOT_GAME_REF:?versions.env did not define PAINTBOT_GAME_REF}"

# An explicit --ref from the caller still wins: expanding an OLD episode requires
# that episode's source commit, not whatever this lab is pinned to today.
if [[ " $* " == *" --ref "* ]]; then
  exec "$CTF_SCRIPT" "$@"
fi

echo "build_expand_replay.sh: building for Paintbot ${PAINTBOT_GAME_VERSION:-?} / $PAINTBOT_GAME_REF"
CTF_REF="$PAINTBOT_GAME_REF" "$CTF_SCRIPT" "$@"

cat <<EOF

Paintbot reader: $LAB_DIR/../ctf_lab/tools/bin/expand_replay_json-$PAINTBOT_GAME_REF
Pass it explicitly so a CTF build cannot shadow it:
  uv run python ctf_lab/tools/viewer_bundle.py <episode-dir> \\
    --expand-replay ctf_lab/tools/bin/expand_replay_json-$PAINTBOT_GAME_REF
EOF
