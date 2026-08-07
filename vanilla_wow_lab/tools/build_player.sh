#!/usr/bin/env bash
# Build wowborg's Python WS /env policy image.
#
# Usage: tools/build_player.sh [--tag REF] [--base IMAGE] [--strategy NAME]
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"

die() { echo "build_player.sh: $*" >&2; exit 1; }

tag="players-wowborg:dev"
strategy="traverse"
while (( $# )); do
  case "$1" in
    --tag)      tag="$2";                         shift 2 ;;
    --base)     WOWBORG_ENVIRONMENT_IMAGE="$2";  shift 2 ;;
    --strategy) strategy="$2";                    shift 2 ;;
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
  --build-arg "WOWBORG_STRATEGY=$strategy" \
  -t "$tag" \
  "$LAB_DIR/wowborg"

echo "==> verifying /env policy and /player observer surface"
docker run --rm --entrypoint python3 "$tag" -c '
from environment import VanillaWowEnv
from environment.runtime.episode import hosted_runtime_factory
from environment.contract.agent import AgentAction, AgentFrame
from player.sdk.navmesh.client import route_navmesh
import wowborg.environment, wowborg.main, wowborg.player_progress, wowborg.strategies
' || die "sanity check FAILED"

if docker run --rm --entrypoint sh "$tag" -c \
  'test -e /usr/local/bin/vanilla-wow-reference-player -o -e /usr/local/bin/king_richard'
then
  die "player unexpectedly contains a bundled WoW client"
fi

echo "==> OK: $tag"
