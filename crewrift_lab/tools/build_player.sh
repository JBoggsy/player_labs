#!/usr/bin/env bash
# Build a Crewrift player image in-lab (Plan A: Docker-only on the host).
#
# Usage: tools/build_player.sh <policy> [--tag REF] [--push REF] [--game-ref REF]
#   <policy>   crewborg | notsus | suspectra
#   --tag      image tag to build (default: players-<policy>:dev)
#   --push     re-tag the built image as REF and `docker push` it
#   --game-ref override CREWRIFT_REF for this build (Nim players only)
#
# Produces a linux/amd64 image (the Coworld upload contract).
#   crewborg (Python) installs the shared SDK from the local players checkout and
#     runs the vendored fork. Needs only Docker.
#   notsus / suspectra (Nim) clone the PRIVATE crewrift game repo (+ its private
#     bitworld dep) at the pinned CREWRIFT_REF and compile, so they ALSO need a
#     GitHub token (GITHUB_PAT or `gh auth token`) with read access to the Metta-AI
#     org. The token is passed as a BuildKit secret and never baked into the image.
#
# See docs/designs/building_players.md for the full design (incl. how to mint the PAT).
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # crewrift_lab/
CREWRIFT_DIR="$LAB_DIR/crewrift"
PLAYERS_REPO="${PLAYERS_REPO:-$HOME/coding/players}"         # SDK source of truth
GAME_REPO_SLUG="Metta-AI/coworld-crewrift"                   # private; needs the PAT

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

# --- GitHub PAT handling for the Nim players (private game + bitworld repos) -------

# Print the "how to get a PAT" guidance and exit. $1 = the specific problem line.
pat_required_error() {
  cat >&2 <<EOF
build_player.sh: cannot build '$policy' — $1

notsus and suspectra compile against PRIVATE Metta-AI repos (coworld-crewrift and
its bitworld dependency), so building them needs a GitHub token with read access to
the Metta-AI org. (crewborg does NOT need a token — its SDK is staged from the local
checkout.)

If you are a coding agent and no token is configured, ASK YOUR USER to do this:
  1. Mint a GitHub Personal Access Token with read access to the Metta-AI repos
     'coworld-crewrift' and 'bitworld':
       - Fine-grained PAT (https://github.com/settings/tokens?type=beta):
         Resource owner = Metta-AI, Repository access = those two repos (or all),
         Permissions = Contents: Read-only.
       - or a classic PAT with the 'repo' scope.
  2. Provide it to this script by EITHER:
       - export GITHUB_PAT=<token>     (preferred), or
       - run 'gh auth login'           (the script falls back to 'gh auth token').
  3. Re-run: tools/build_player.sh $policy

Details: crewrift_lab/docs/designs/building_players.md §"Credentials".
EOF
  exit 1
}

# Echo a token to stdout (GITHUB_PAT, else `gh auth token`), or nothing.
resolve_github_pat() {
  if [ -n "${GITHUB_PAT:-}" ]; then printf '%s' "$GITHUB_PAT"; return; fi
  if command -v gh >/dev/null 2>&1; then gh auth token 2>/dev/null || true; fi
}

# Fail fast with a clear message if the token can't read the private game repo,
# instead of letting a slow Docker build fail deep inside the clone.
preflight_repo_access() {
  local token="$1" code
  code="$(curl -s -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer $token" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$GAME_REPO_SLUG" 2>/dev/null || echo 000)"
  case "$code" in
    200) ;;  # token valid + has access
    401) pat_required_error "the GitHub token is invalid or expired (GitHub returned 401)." ;;
    403|404) pat_required_error "the token is valid but lacks read access to $GAME_REPO_SLUG (got HTTP $code); it also needs access to Metta-AI/bitworld." ;;
    000) echo "build_player.sh: warning — couldn't reach api.github.com to verify the token; proceeding (the build will fail if it's wrong)." >&2 ;;
    *) pat_required_error "unexpected GitHub API response (HTTP $code) while verifying access to $GAME_REPO_SLUG." ;;
  esac
}

# build <context> <dockerfile> [extra docker args...]
build() {
  local ctx="$1" dockerfile="$2"; shift 2
  echo "==> docker buildx build --platform=linux/amd64 -t $tag (context: $ctx)"
  docker buildx build --platform=linux/amd64 --load \
    -f "$dockerfile" -t "$tag" "$@" "$ctx"
}

case "$policy" in
  notsus|suspectra)
    # Self-contained: context is the policy dir; the Dockerfile clones the game
    # repo at CREWRIFT_REF, nimby-syncs, overlays this source, and compiles.
    dir="$CREWRIFT_DIR/$policy"
    [ -f "$dir/Dockerfile" ] || die "no Dockerfile at $dir"

    GITHUB_PAT="$(resolve_github_pat)"
    [ -n "$GITHUB_PAT" ] || pat_required_error "no GitHub token found (GITHUB_PAT unset and 'gh auth token' unavailable)."
    export GITHUB_PAT
    preflight_repo_access "$GITHUB_PAT"

    build "$dir" "$dir/Dockerfile" \
      --secret "id=gh_token,env=GITHUB_PAT" \
      --build-arg "CREWRIFT_REF=$CREWRIFT_REF"
    ;;

  crewborg)
    # Python fork re-rooted out of `players`: it imports only players.player_sdk,
    # so we stage a composed context = {the SDK checkout, the vendored fork} and
    # the Dockerfile installs the SDK then puts the fork on PYTHONPATH.
    dir="$CREWRIFT_DIR/crewborg"
    [ -d "$PLAYERS_REPO/players/player_sdk" ] || die \
      "SDK checkout not found at $PLAYERS_REPO (set PLAYERS_REPO=/path/to/players)"
    stage="$(mktemp -d)"; trap 'rm -rf "$stage"' EXIT
    mkdir -p "$stage/sdk"
    cp "$PLAYERS_REPO/pyproject.toml" "$PLAYERS_REPO/README.md" "$stage/sdk/"
    rsync -a --exclude '__pycache__' --exclude '*.egg-info' "$PLAYERS_REPO/players" "$stage/sdk/"
    cp "$CREWRIFT_DIR/__init__.py" "$stage/crewrift_init.py"
    rsync -a --exclude '__pycache__' --exclude '*.egg-info' "$dir/" "$stage/crewborg/"
    build "$stage" "$dir/coworld/Dockerfile"
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
