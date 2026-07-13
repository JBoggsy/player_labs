#!/usr/bin/env bash
# Build a CTF player image in-lab (Docker-only on the host).
#
# Usage: tools/build_player.sh <policy> [--tag REF] [--push REF]
#   <policy>   beacon
#   --tag      image tag to build (default: players-<policy>:dev)
#   --push     re-tag the built image as REF and `docker push` it
#
# Produces a linux/amd64 image (the Coworld upload contract). All inputs are public,
# so the host needs only Docker — no credentials: beacon (Python) installs the shared
# SDK from the public coworld-tools repo (PLAYERS_SDK_REF) and runs the vendored fork
# (which ships its own offline-baked nav grid).
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # ctf_lab/
CTF_DIR="$LAB_DIR/ctf"

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
  beacon)
    # Python fork re-rooted out of `players`: it imports only players.player_sdk. The
    # Dockerfile installs the SDK from the coworld-tools monorepo at PLAYERS_SDK_REF, so
    # we stage the fork + a minimal ctf/__init__.py and put it on PYTHONPATH.
    # Resolve PLAYERS_SDK_REF=main to a SHA via ls-remote (a literal `main` build-arg is a
    # Docker layer-cache trap: the pip layer caches on the unchanged tarball URL, so a
    # moved main keeps the stale SDK). Pinning the SHA busts the cache when main moves.
    if [ "$PLAYERS_SDK_REF" = "main" ]; then
      remote_sha="$(git ls-remote https://github.com/Metta-AI/coworld-tools.git refs/heads/main | awk '{print $1}' | head -1)"
      if [ -n "$remote_sha" ]; then
        echo "==> PLAYERS_SDK_REF=main resolved to coworld-tools main $remote_sha"
        PLAYERS_SDK_REF="$remote_sha"
      else
        echo "WARNING: could not resolve coworld-tools main; building at 'main' (Docker may reuse a stale SDK layer)" >&2
      fi
    fi
    dir="$CTF_DIR/beacon"
    [ -f "$dir/Dockerfile" ] || die "no Dockerfile at $dir"
    [ -f "$dir/mapdata/nav.npz" ] || die "missing baked nav grid ($dir/mapdata/nav.npz); run: uv run python -m ctf.beacon.tools.bake_map"
    stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
    cp "$CTF_DIR/__init__.py" "$stage/ctf_init.py"
    rsync -a --exclude '__pycache__' --exclude '*.egg-info' --exclude '.cache' "$dir/" "$stage/beacon/"
    echo "==> docker buildx build --platform=linux/amd64 -t $tag"
    docker buildx build --platform=linux/amd64 --load \
      -f "$dir/Dockerfile" -t "$tag" \
      --build-arg "PLAYERS_SDK_REF=$PLAYERS_SDK_REF" "$stage"
    ;;
  *)
    die "unknown policy '$policy' (want: beacon)" ;;
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
