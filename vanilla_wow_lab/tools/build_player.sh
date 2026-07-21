#!/usr/bin/env bash
# Build the wowborg v2 player image (our policy layered on the deployed Nim shim).
#
# Usage: tools/build_player.sh [--tag REF] [--base IMAGE]
#   --tag    image tag to build (default: players-wowborg:dev)
#   --base   override WOWBORG_BASE_IMAGE for this build (default: versions.env pin)
#
# Produces a linux/amd64 image (the Coworld upload contract). The base is the deployed
# reference player image, pinned BY DIGEST in tools/versions.env; if it isn't present
# locally, docker pulls it from the public ECR. After building, sanity-checks that the
# base still provides everything the shim relies on. Design:
# docs/designs/wowborg-v2-shim-adoption.md.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # vanilla_wow_lab/

# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"

die() { echo "build_player.sh: $*" >&2; exit 1; }

tag="players-wowborg:dev"
while (( $# )); do
  case "$1" in
    --tag)     tag="$2";                shift 2 ;;
    --base)    WOWBORG_BASE_IMAGE="$2"; shift 2 ;;
    -h|--help) sed -n '3,8p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

command -v docker >/dev/null 2>&1 || die "docker not found on PATH"
[ -n "${WOWBORG_BASE_IMAGE:-}" ] || die "WOWBORG_BASE_IMAGE not set (tools/versions.env)"

echo "==> base: $WOWBORG_BASE_IMAGE"
echo "==> docker buildx build --platform=linux/amd64 -t $tag (context: $LAB_DIR/wowborg)"
docker buildx build --platform=linux/amd64 --load \
  -f "$LAB_DIR/wowborg/Dockerfile" \
  --build-arg "WOWBORG_BASE_IMAGE=$WOWBORG_BASE_IMAGE" \
  -t "$tag" \
  "$LAB_DIR/wowborg"

echo "==> sanity-checking built image (base contract + our layer)"
# 0.1.31 base: world data is NOT bundled (game serves it via --assets URL); the control
# seam is wow_sdk.nim_control (binary TCP socket), not the old action.json file bridge.
docker run --rm --entrypoint sh "$tag" -c '
  set -e
  test -x /usr/local/bin/king_richard
  python3 -c "import wow_sdk.nim_control, wow_sdk.runtime, wow_sdk.protocol"
  python3 -c "from wow_sdk.nim_control import NimControlClient, EnvironmentFrame, FactorizedAction"
  python3 -c "import vanilla_wow_coworld.player"
  python3 -c "import wowborg.shim, wowborg.bridge, wowborg.policies"
  [ "$KING_NIMROD_COMMAND" = "python3 -m wowborg.shim" ]
' || die "sanity check FAILED — the base image contract moved; see versions.env bump notes"

echo "==> OK: $tag"
