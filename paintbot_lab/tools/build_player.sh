#!/usr/bin/env bash
# Build a Paintbot player image in-lab (Docker-only on the host).
#
# Usage: tools/build_player.sh <policy> [--tag REF] [--push REF]
#   <policy>   stencil
#   --tag      image tag to build (default: players-<policy>:dev)
#   --push     re-tag the built image as REF and `docker push` it
#
# Produces a linux/amd64 image (the Coworld upload contract). All inputs are public,
# so the host needs only Docker — no credentials. Unlike ctf_lab's beacon there is
# NO baked nav artifact to check: stencil builds its world model online per episode.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # paintbot_lab/
PKG_DIR="$LAB_DIR/paintbot"

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
  stencil)
    # Resolve PLAYERS_SDK_REF=main to a SHA via ls-remote (a literal `main` build-arg
    # is a Docker layer-cache trap: the pip layer caches on the unchanged tarball URL).
    if [ "$PLAYERS_SDK_REF" = "main" ]; then
      remote_sha="$(git ls-remote https://github.com/Metta-AI/coworld-tools.git refs/heads/main | awk '{print $1}' | head -1)"
      if [ -n "$remote_sha" ]; then
        echo "==> PLAYERS_SDK_REF=main resolved to coworld-tools main $remote_sha"
        PLAYERS_SDK_REF="$remote_sha"
      else
        echo "WARNING: could not resolve coworld-tools main; building at 'main' (Docker may reuse a stale SDK layer)" >&2
      fi
    fi
    dir="$PKG_DIR/stencil"
    [ -f "$dir/Dockerfile" ] || die "no Dockerfile at $dir"
    stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
    cp "$PKG_DIR/__init__.py" "$stage/paintbot_init.py"
    rsync -a --exclude '__pycache__' --exclude '*.egg-info' --exclude '.cache' \
      --exclude 'tests' "$dir/" "$stage/stencil/"
    echo "==> docker buildx build --platform=linux/amd64 -t $tag"
    docker buildx build --platform=linux/amd64 --load \
      -f "$dir/Dockerfile" -t "$tag" \
      --build-arg "PLAYERS_SDK_REF=$PLAYERS_SDK_REF" "$stage"
    ;;
  *)
    die "unknown policy '$policy' (want: stencil)" ;;
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
