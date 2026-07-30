#!/usr/bin/env bash
# Build wowborg's Python WS /env policy image.
#
# Usage: tools/build_player.sh [--tag REF] [--base IMAGE] [--policy NAME] [--stations JSON]
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"

die() { echo "build_player.sh: $*" >&2; exit 1; }

tag="players-wowborg:dev"
policy="world_race"
stations=""
while (( $# )); do
  case "$1" in
    --tag)      tag="$2";                         shift 2 ;;
    --base)     WOWBORG_ENVIRONMENT_IMAGE="$2";  shift 2 ;;
    --policy)   policy="$2";                      shift 2 ;;
    --stations) stations="$2";                    shift 2 ;;
    -h|--help)  sed -n '2,4p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

command -v docker >/dev/null 2>&1 || die "docker not found on PATH"
[ -n "${WOWBORG_ENVIRONMENT_IMAGE:-}" ] \
  || die "WOWBORG_ENVIRONMENT_IMAGE not set"

echo "==> environment contract: $WOWBORG_ENVIRONMENT_IMAGE"
docker buildx build --platform=linux/amd64 --load \
  -f "$LAB_DIR/wowborg/Dockerfile" \
  --build-arg "WOWBORG_ENVIRONMENT_IMAGE=$WOWBORG_ENVIRONMENT_IMAGE" \
  --build-arg "WOWBORG_POLICY=$policy" \
  --build-arg "WOWBORG_STATIONS=$stations" \
  -t "$tag" \
  "$LAB_DIR/wowborg"

echo "==> verifying /env-only player surface"
docker run --rm --entrypoint python3 "$tag" -c '
from environment import VanillaWowEnv
from environment.runtime.episode import hosted_runtime_factory
from environment.contract.agent import AgentFrame, MoveAction
from player.sdk.navmesh import route_navmesh
import wowborg.environment, wowborg.main, wowborg.policies
' || die "sanity check FAILED"

if docker run --rm --entrypoint sh "$tag" -c \
  'test -e /usr/local/bin/vanilla-wow-reference-player -o -e /usr/local/bin/king_richard'
then
  die "player unexpectedly contains a bundled WoW client"
fi

echo "==> OK: $tag"
