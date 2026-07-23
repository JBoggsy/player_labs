#!/usr/bin/env bash
# Route lab runner — real-navmesh nav validation in SECONDS, not hosted hours.
#
# Mounts the wowborg source into the pinned GAME image (which carries the full
# world navmesh at /vmangos-data/mmaps + the vmangos-navmesh-helper binary) and
# runs tools/route_lab.py against the actual L1/L2 planning code.
#
# Usage: tools/route_lab.sh [stations | station NAME | route X Y Z [MAP]]
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GAME_IMAGE="$(docker images --format '{{.Repository}}:{{.Tag}}' \
  | grep 'cow_e8eef946.*vanilla_wow-0.1.31-2' | head -1)"
[ -n "$GAME_IMAGE" ] || {
  echo "route_lab.sh: 0.1.31 game image (…-2, the vmangos data image) not present locally." >&2
  echo "Download it once via the coworld-local-run skill, then re-run." >&2
  exit 1
}

exec docker run --rm \
  -v "$LAB_DIR/wowborg:/opt/wowborg/wowborg:ro" \
  -v "$LAB_DIR/tools/route_lab.py:/opt/route_lab.py:ro" \
  -e VANILLA_WOW_NAVMESH_HELPER=/usr/local/bin/vmangos-navmesh-helper \
  -e VANILLA_WOW_MMAPS_DIR=/vmangos-data/mmaps \
  -e "WOWBORG_STATIONS=${WOWBORG_STATIONS:-}" \
  --entrypoint python3 \
  "$GAME_IMAGE" /opt/route_lab.py "$@"
