#!/usr/bin/env bash
# Build a version-matched `expand_replay` binary for reading Crewrift replays.
#
# Usage: tools/build_expand_replay.sh [--ref SHA] [--force] [--run REPLAY]
#   --ref SHA    crewrift game ref to build against (default: CREWRIFT_REF from
#                tools/versions.env — the version our players/replays use)
#   --force      re-fetch source and rebuild even if a cached binary exists
#   --run REPLAY build if needed, then run the binary on REPLAY (a .bitreplay/replay.json)
#
# `expand_replay` re-simulates a recorded replay through the crewrift `sim` and
# validates a per-tick hash, so it only expands a replay fully when built from the
# SAME game version that recorded it (see docs/crewrift-replays.md §B). This builds
# it at a pinned ref so it matches the replays from our own experience requests.
#
# It is a HOST analysis tool (you run it locally to read a replay), so it builds
# native to this host's arch — no Docker, no amd64. The crewrift game source + its
# bitworld dep are public, so the source fetch and `nimby sync` need no credentials.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # crewrift_lab/
BIN_DIR="$LAB_DIR/tools/bin"
CACHE_ROOT="$LAB_DIR/.cache/crewrift-src"
GAME_REPO_SLUG="Metta-AI/coworld-crewrift"

# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"

die() { echo "build_expand_replay.sh: $*" >&2; exit 1; }

ref="$CREWRIFT_REF"
force=0
run_replay=""
while (( $# )); do
  case "$1" in
    --ref)   ref="$2";        shift 2 ;;
    --force) force=1;         shift ;;
    --run)   run_replay="$2"; shift 2 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

# Nim toolchain (host-native build). nimby installs nim under ~/.nimby/nim/bin;
# user installs often live in ~/.local/bin. Make both reachable, then verify.
export PATH="$HOME/.local/bin:$HOME/.nimby/nim/bin:$PATH"
command -v nim   >/dev/null 2>&1 || die "nim not found (install via nimby; see the crewrift repo README)"
command -v nimby >/dev/null 2>&1 || die "nimby not found (https://github.com/treeform/nimby)"

out_bin="$BIN_DIR/expand_replay-$ref"
stable="$BIN_DIR/expand_replay"

link_stable() { mkdir -p "$BIN_DIR"; ln -sf "expand_replay-$ref" "$stable"; }

# Fast path: already built for this ref.
if [[ -x "$out_bin" && $force -eq 0 ]]; then
  echo "build_expand_replay.sh: cached binary up to date: $out_bin"
  link_stable
  [[ -n "$run_replay" ]] && exec "$out_bin" "$run_replay"
  echo "Run it: $stable <replay.json>"
  exit 0
fi

# --- Fetch source for the ref (a public tarball snapshot — never a clone) ---------
src_dir="$CACHE_ROOT/$ref"
if [[ ! -f "$src_dir/tools/expand_replay.nim" || $force -eq 1 ]]; then
  echo "==> fetching $GAME_REPO_SLUG @ $ref (tarball, no clone)"
  rm -rf "$src_dir"; mkdir -p "$src_dir"
  tgz="$(mktemp)"; trap 'rm -f "$tgz"' EXIT
  curl -fsSL "https://github.com/$GAME_REPO_SLUG/archive/$ref.tar.gz" -o "$tgz" \
    || die "could not download $GAME_REPO_SLUG @ $ref — check the ref (and your network)."
  tar xzf "$tgz" -C "$src_dir" --strip-components=1
fi

# --- Resolve Nim deps (bitworld, etc.) --------------------------------------------
# nimby clones the (public) deps via git into the persistent global store
# (~/.nimby/pkgs), so this is normally a cache hit and needs no credentials.
echo "==> nimby sync (deps; cache hit unless nimby.lock changed)"
( cd "$src_dir" && nimby --global sync nimby.lock )

# --- Build host-native ------------------------------------------------------------
echo "==> compiling expand_replay (host-native) -> $out_bin"
mkdir -p "$BIN_DIR"
( cd "$src_dir" && nim c -d:release --opt:speed \
    --nimcache:"$(mktemp -d)" \
    --out:"$out_bin" \
    tools/expand_replay.nim )
link_stable

echo ""
echo "Built: $out_bin  (host-native; ref $ref)"
echo "Stable symlink: $stable"
if [[ -n "$run_replay" ]]; then
  echo "==> $stable $run_replay"
  exec "$out_bin" "$run_replay"
fi
echo "Run it: $stable <replay.json>     # see docs/crewrift-replays.md §B"
