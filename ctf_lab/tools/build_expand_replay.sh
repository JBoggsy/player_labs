#!/usr/bin/env bash
# Build a version-matched `expand_replay` binary for reading CTF replays.
#
# Usage: ctf_lab/tools/build_expand_replay.sh [--ref SHA] [--force] [--run REPLAY]
#   --ref SHA    coworld-ctf game ref to build against
#                (default: CTF_REF below — the version our replays use)
#   --force      re-fetch source and rebuild even if a cached binary exists
#   --run REPLAY build if needed, then run the binary on REPLAY (a .bitreplay)
#
# `expand_replay` re-simulates a recorded replay through the CTF sim and validates
# a per-tick hash, so it expands a replay faithfully only when built from the SAME
# game version that recorded it. This builds at a matching source ref.
#
# It is a HOST analysis tool (run locally to read a replay), so it builds native
# to this host's arch — no Docker, no amd64. The CTF game source + its bitworld
# dep are public, so the fetch and `nimby sync` need no credentials.
set -euo pipefail

# The CTF source ref to build the tool from. It must contain tools/expand_replay.nim
# and be the same game version that recorded the replays (re-sim validates a per-tick
# hash). DELIBERATELY PINNED — it must match the game version the LEAGUE actually runs
# (the last *deployed* game), not `main`, which can run ahead of what's deployed.
#   How you'll know to bump: build_expand_replay starts hash-failing on FRESH replays
#   — that's the signal the league redeployed; try a newer commit until a fresh replay
#   expands cleanly, and update this.
# Current value (761c098) is coworld-ctf HEAD as of 2026-07-10 (lab creation); the
# CTF league is brand-new, so confirm against a real league replay when one exists.
CTF_REF="${CTF_REF:-761c098}"
GAME_REPO_SLUG="Metta-AI/coworld-ctf"

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # ctf_lab/
BIN_DIR="$LAB_DIR/tools/bin"
CACHE_ROOT="$LAB_DIR/.cache/ctf-src"

die() { echo "build_expand_replay.sh: $*" >&2; exit 1; }

ref="$CTF_REF"
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
# CTF builds against Nim 2.2.4 (see the game repo's Dockerfile / nimby.lock).
export PATH="$HOME/.local/bin:$HOME/.nimby/nim/bin:$PATH"
command -v nim   >/dev/null 2>&1 || die "nim not found (install via nimby; see the CTF repo README)"
command -v nimby >/dev/null 2>&1 || die "nimby not found (https://github.com/treeform/nimby)"

out_bin="$BIN_DIR/expand_replay-$ref"
stable="$BIN_DIR/expand_replay"
# The JSONL emitter (for the event warehouse) is a sibling built from the same ref.
json_bin="$BIN_DIR/expand_replay_json-$ref"
json_stable="$BIN_DIR/expand_replay_json"
# This lab's own emitter source, staged into the fetched game tools/ dir at build time.
LAB_JSON_SRC="$LAB_DIR/tools/expand_replay_json.nim"

link_stable() {
  mkdir -p "$BIN_DIR"
  ln -sf "expand_replay-$ref" "$stable"
  ln -sf "expand_replay_json-$ref" "$json_stable"
}

# Fast path: already built for this ref (both binaries present).
if [[ -x "$out_bin" && -x "$json_bin" && $force -eq 0 ]]; then
  echo "build_expand_replay.sh: cached binaries up to date: $out_bin, $json_bin"
  link_stable
  [[ -n "$run_replay" ]] && exec "$out_bin" "$run_replay"
  echo "Run it:  $stable <replay.bitreplay>   |   $json_stable <replay.bitreplay>  (JSONL)"
  exit 0
fi

# --- Fetch source for the ref (a tarball snapshot — never a clone) ----------------
# coworld-ctf is PRIVATE, so fetch via the authenticated `gh api` tarball endpoint
# (falls back to a plain curl for the public case / if gh is absent).
src_dir="$CACHE_ROOT/$ref"
if [[ ! -f "$src_dir/tools/expand_replay.nim" || $force -eq 1 ]]; then
  echo "==> fetching $GAME_REPO_SLUG @ $ref (tarball, no clone)"
  rm -rf "$src_dir"; mkdir -p "$src_dir"
  tgz="$(mktemp)"; trap 'rm -f "$tgz"' EXIT
  if command -v gh >/dev/null 2>&1 && gh api "repos/$GAME_REPO_SLUG/tarball/$ref" > "$tgz" 2>/dev/null; then
    :
  elif curl -fsSL "https://github.com/$GAME_REPO_SLUG/archive/$ref.tar.gz" -o "$tgz"; then
    :
  else
    die "could not download $GAME_REPO_SLUG @ $ref — check the ref, and that \`gh auth\` has access (the repo is private)."
  fi
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

# Stage this lab's JSONL emitter into the fetched game tools/ dir so its
# `./expand_replay` + `../src/ctf/replays` imports resolve, then compile it.
echo "==> compiling expand_replay_json (host-native) -> $json_bin"
[[ -f "$LAB_JSON_SRC" ]] || die "missing emitter source: $LAB_JSON_SRC"
cp "$LAB_JSON_SRC" "$src_dir/tools/expand_replay_json.nim"
( cd "$src_dir" && nim c -d:release --opt:speed \
    --nimcache:"$(mktemp -d)" \
    --out:"$json_bin" \
    tools/expand_replay_json.nim )
link_stable

echo ""
echo "Built: $out_bin  and  $json_bin  (host-native; ref $ref)"
echo "Stable symlinks: $stable , $json_stable"
if [[ -n "$run_replay" ]]; then
  echo "==> $stable $run_replay"
  exec "$out_bin" "$run_replay"
fi
echo "Run it:  $stable <replay.bitreplay>   (human timeline)"
echo "         $json_stable <replay.bitreplay>   (JSONL for the event warehouse)"
