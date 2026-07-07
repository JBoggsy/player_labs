#!/usr/bin/env bash
# Build a version-matched `expand_replay` binary for reading Heartleaf replays.
#
# Usage: heartleaf_lab/tools/build_expand_replay.sh [--ref SHA] [--force] [--run REPLAY]
#   --ref SHA    coworld-heartleaf game ref to build against
#                (default: HEARTLEAF_REF below — the version our replays use)
#   --force      re-fetch source and rebuild even if a cached binary exists
#   --run REPLAY build if needed, then run the binary on REPLAY (a replay.json/.bitreplay)
#
# `expand_replay` re-simulates a recorded replay through the heartleaf sim and
# validates a per-tick hash, so it expands a replay faithfully only when built
# from the SAME game version that recorded it. Heartleaf replays pin game
# version "0.1.0" internally; this builds at a matching source ref.
#
# It is a HOST analysis tool (run locally to read a replay), so it builds native
# to this host's arch — no Docker, no amd64. The heartleaf game source + its
# bitworld dep are public, so the fetch and `nimby sync` need no credentials.
set -euo pipefail

# The heartleaf source ref to build the tool from. It must contain
# tools/expand_replay.nim and be the same game version that recorded the
# replays (re-sim validates a per-tick hash). Currently the replay-expander
# branch (Metta-AI/coworld-heartleaf#15); bump to the merge commit once it
# lands, and again if the deployed league game advances and hashes mismatch.
HEARTLEAF_REF="${HEARTLEAF_REF:-7aa7adb}"
GAME_REPO_SLUG="Metta-AI/coworld-heartleaf"

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # heartleaf_lab/
BIN_DIR="$LAB_DIR/tools/bin"
CACHE_ROOT="$LAB_DIR/.cache/heartleaf-src"

die() { echo "build_expand_replay.sh: $*" >&2; exit 1; }

ref="$HEARTLEAF_REF"
force=0
run_replay=""
while (( $# )); do
  case "$1" in
    --ref)   ref="$2";        shift 2 ;;
    --force) force=1;         shift ;;
    --run)   run_replay="$2"; shift 2 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

# Nim toolchain (host-native build). nimby installs nim under ~/.nimby/nim/bin;
# user installs often live in ~/.local/bin. Make both reachable, then verify.
export PATH="$HOME/.local/bin:$HOME/.nimby/nim/bin:$PATH"
command -v nim   >/dev/null 2>&1 || die "nim not found (install via nimby; see the heartleaf repo README)"
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
echo "Run it: $stable <replay.json>"
