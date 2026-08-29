#!/usr/bin/env bash
# Route lab runner — real-navmesh nav validation in SECONDS, not hosted hours.
#
# Mounts the wowborg source into the pinned GAME image (which carries the full
# world navmesh at /vmangos-data/mmaps + the vmangos-navmesh-helper binary) and
# runs tools/route_lab.py against the actual L1/L2 planning code.
#
# Usage: tools/route_lab.sh [stations | course | station NAME | route X Y Z [MAP] |
#                            segment SX SY SZ TX TY TZ [MAP] |
#                            chain SX SY SZ TX TY TZ [MAP] [TOLERANCE]]
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"
GAME_IMAGE="$WOWBORG_ENVIRONMENT_IMAGE"

exec docker run --rm --platform=linux/amd64 \
  -v "$LAB_DIR/wowborg:/opt/wowborg/wowborg:ro" \
  -v "$LAB_DIR/tools/route_lab.py:/opt/route_lab.py:ro" \
  -e VANILLA_WOW_NAVMESH_HELPER=/usr/local/bin/vmangos-navmesh-helper \
  -e VANILLA_WOW_MMAPS_DIR=/vmangos-data/mmaps \
  -e "WOWBORG_STATIONS=${WOWBORG_STATIONS:-}" \
  --entrypoint python3 \
  "$GAME_IMAGE" /opt/route_lab.py "$@"
