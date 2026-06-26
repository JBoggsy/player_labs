#!/usr/bin/env bash
# Build a Crewrift player image in-lab (Plan A: Docker-only on the host).
#
# Usage: tools/build_player.sh <policy> [--tag REF] [--push REF] [--game-ref REF]
#   <policy>   crewborg | notsus | suspectra
#   --tag      image tag to build (default: players-<policy>:dev)
#   --push     re-tag the built image as REF and `docker push` it
#   --game-ref override CREWRIFT_REF for this build (Nim players only)
#
# Produces a linux/amd64 image (the Coworld upload contract). All inputs are public,
# so the host needs only Docker — no credentials:
#   crewborg (Python) installs the shared SDK from the public players repo
#     (PLAYERS_SDK_REF) and runs the vendored fork.
#   notsus / suspectra (Nim) clone the public crewrift game repo (+ its bitworld dep)
#     at the pinned CREWRIFT_REF and compile.
#
# See docs/designs/building_players.md for the full design.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # crewrift_lab/
CREWRIFT_DIR="$LAB_DIR/crewrift"

# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"

die() { echo "build_player.sh: $*" >&2; exit 1; }

policy="${1:-}"; shift || true
if [ -z "$policy" ]; then
  sed -n '3,11p' "$0" >&2
  exit 2
fi

tag=""
push_ref=""
while (( $# )); do
  case "$1" in
    --tag)      tag="$2";          shift 2 ;;
    --push)     push_ref="$2";     shift 2 ;;
    --game-ref) CREWRIFT_REF="$2"; shift 2 ;;
    -h|--help)  sed -n '3,11p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
: "${tag:=players-$policy:dev}"

command -v docker >/dev/null 2>&1 || die "docker not found on PATH"

# build <context> <dockerfile> [extra docker args...]
build() {
  local ctx="$1" dockerfile="$2"; shift 2
  echo "==> docker buildx build --platform=linux/amd64 -t $tag (context: $ctx)"
  docker buildx build --platform=linux/amd64 --load \
    -f "$dockerfile" -t "$tag" "$@" "$ctx"
}

case "$policy" in
  notsus|suspectra)
    # Self-contained: context is the policy dir; the Dockerfile clones the (public)
    # game repo at CREWRIFT_REF, nimby-syncs, overlays this source, and compiles.
    dir="$CREWRIFT_DIR/$policy"
    [ -f "$dir/Dockerfile" ] || die "no Dockerfile at $dir"
    build "$dir" "$dir/Dockerfile" --build-arg "CREWRIFT_REF=$CREWRIFT_REF"
    ;;

  crewborg)
    # Python fork re-rooted out of `players`: it imports only players.player_sdk.
    # The Dockerfile installs the SDK from the coworld-tools monorepo (players/ subdir)
    # at PLAYERS_SDK_REF, so we just stage the fork + the lab's crewrift/__init__.py and
    # put it on PYTHONPATH. No local players checkout needed.
    #
    # Resolve PLAYERS_SDK_REF=main to coworld-tools' current main commit via ls-remote:
    # "main" as a build-arg is a Docker layer-cache trap (the pip-install layer caches on
    # the unchanged tarball URL string, so a moved main silently does NOT rebuild — the
    # image keeps the stale SDK). Pinning the SHA busts the cache exactly when main moves.
    # We resolve from the remote (not uv.lock) because uv cannot lock coworld-tools — its
    # broken `players/users/relh/co-gas` submodule fails uv's recursive clone; the Docker
    # tarball install sidesteps submodules entirely.
    if [ "$PLAYERS_SDK_REF" = "main" ]; then
      remote_sha="$(git ls-remote https://github.com/Metta-AI/coworld-tools.git refs/heads/main | awk '{print $1}' | head -1)"
      if [ -n "$remote_sha" ]; then
        echo "==> PLAYERS_SDK_REF=main resolved to coworld-tools main $remote_sha"
        PLAYERS_SDK_REF="$remote_sha"
      else
        echo "WARNING: could not resolve coworld-tools main via ls-remote; building at 'main' (Docker may reuse a stale cached SDK layer)" >&2
      fi
    fi
    dir="$CREWRIFT_DIR/crewborg"
    stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
    cp "$CREWRIFT_DIR/__init__.py" "$stage/crewrift_init.py"
    rsync -a --exclude '__pycache__' --exclude '*.egg-info' "$dir/" "$stage/crewborg/"
    build "$stage" "$dir/coworld/Dockerfile" --build-arg "PLAYERS_SDK_REF=$PLAYERS_SDK_REF"
    ;;

  *)
    die "unknown policy '$policy' (want: crewborg | notsus | suspectra)" ;;
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
       (see ../AGENTS.md loop steps 5-8 and the coworld-policy-lifecycle skill).
EOF
