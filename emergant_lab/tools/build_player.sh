#!/usr/bin/env bash
# Build the native Emerg-ant player image in-lab (Docker-only on the host).
#
# Usage: tools/build_player.sh <policy> [--tag REF] [--push REF]
#   <policy>   stencil-ant
#   --tag      image tag to build (default: players-<policy>:dev)
#   --push     re-tag the built image as REF and `docker push` it
#
# Produces a linux/amd64 image (the Coworld upload contract). All inputs are public,
# so the host needs only Docker — no credentials. Stencil builds its world model
# online from the Sprite-v1 init snapshot; no map artifact is baked into the image.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG_DIR="$LAB_DIR/emergant"

# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"

die() { echo "build_player.sh: $*" >&2; exit 1; }

policy="${1:-}"; shift || true
if [ -z "$policy" ]; then
  sed -n '3,9p' "$0" >&2
  exit 2
fi

tag=""
push_ref=""
while (( $# )); do
  case "$1" in
    --tag)  tag="$2";      shift 2 ;;
    --push) push_ref="$2"; shift 2 ;;
    -h|--help) sed -n '3,9p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
: "${tag:=players-$policy:dev}"

command -v docker >/dev/null 2>&1 || die "docker not found on PATH"

case "$policy" in
  stencil-ant)
    dir="$PKG_DIR/stencil_ant_gv57_nim"
    [ -f "$dir/Dockerfile" ] || die "no Dockerfile at $dir"
    stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
    rsync -a --exclude 'Dockerfile' "$dir/" "$stage/"
    echo "==> docker buildx build --platform=linux/amd64 -t $tag"
    docker buildx build --platform=linux/amd64 --load \
      -f "$dir/Dockerfile" -t "$tag" \
      --build-arg "EMERG_ANT_GAME_REF=$EMERG_ANT_GAME_REF" "$stage"
    ;;
  *)
    die "unknown policy '$policy' (want: stencil-ant)" ;;
esac

if [ -n "$push_ref" ]; then
  docker tag "$tag" "$push_ref"
  docker push "$push_ref"
  tag="$push_ref"
fi

cat <<EOF

Built: $tag  (linux/amd64)
Next:  uv run coworld upload-policy $tag --name $policy
       Upload is routine; submitting to a league is the gated step
       (see ../AGENTS.md and the coworld-policy-lifecycle skill).
EOF
