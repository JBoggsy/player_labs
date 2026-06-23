#!/usr/bin/env bash
# Build an agricogla player image in-lab (Docker-only on the host).
#
# Usage: tools/build_player.sh farmhand [--tag REF] [--push REF]
#   --tag   image tag to build (default: players-farmhand:dev)
#   --push  re-tag the built image as REF and `docker push` it
#
# Produces a linux/amd64 image (the Coworld upload contract). All inputs public:
# farmhand installs the shared SDK from the public players repo (PLAYERS_SDK_REF)
# and runs the vendored package (which vendors the cogweb bridge until it's in the SDK).
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # agricogla_lab/
AGR_DIR="$LAB_DIR/agricogla"
[ -f "$LAB_DIR/tools/versions.env" ] && source "$LAB_DIR/tools/versions.env"
: "${PLAYERS_SDK_REF:=main}"

die() { echo "build_player.sh: $*" >&2; exit 1; }

policy="${1:-farmhand}"; shift || true
tag=""; push_ref=""
while (( $# )); do
  case "$1" in
    --tag)  tag="$2";      shift 2 ;;
    --push) push_ref="$2"; shift 2 ;;
    -h|--help) sed -n '3,9p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
: "${tag:=players-$policy:dev}"
[ "$policy" = "farmhand" ] || die "unknown policy '$policy' (want: farmhand)"
command -v docker >/dev/null 2>&1 || die "docker not found on PATH"

# Resolve PLAYERS_SDK_REF=main to the exact uv.lock commit — "main" as a build-arg
# is a Docker layer-cache trap (pip layer caches on the unchanged tarball URL).
if [ "$PLAYERS_SDK_REF" = "main" ]; then
  locked_sha="$(sed -n 's/.*github\.com\/Metta-AI\/players?branch=main#\([0-9a-f]\{40\}\).*/\1/p' "$LAB_DIR/../uv.lock" | head -1)"
  if [ -n "$locked_sha" ]; then
    echo "==> PLAYERS_SDK_REF=main resolved to uv.lock commit $locked_sha"
    PLAYERS_SDK_REF="$locked_sha"
  else
    echo "WARNING: could not resolve players commit from uv.lock; building at 'main'" >&2
  fi
fi

dir="$AGR_DIR/farmhand"
stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
cp "$AGR_DIR/__init__.py" "$stage/agricogla_init.py"
# Stage the package source (rsync isn't available in this env; use cp + prune caches).
mkdir -p "$stage/farmhand"
cp -r "$dir/." "$stage/farmhand/"
find "$stage/farmhand" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$stage/farmhand" -name '*.egg-info' -prune -exec rm -rf {} + 2>/dev/null || true

echo "==> docker buildx build --platform=linux/amd64 -t $tag"
docker buildx build --platform=linux/amd64 --load \
  -f "$dir/coworld/Dockerfile" -t "$tag" \
  --build-arg "PLAYERS_SDK_REF=$PLAYERS_SDK_REF" "$stage"

if [ -n "$push_ref" ]; then
  docker tag "$tag" "$push_ref"
  docker push "$push_ref"
  tag="$push_ref"
fi

cat <<EOF

Built: $tag  (linux/amd64)
Next:  uv run coworld upload-policy $tag --name agricogla-farmhand
EOF
