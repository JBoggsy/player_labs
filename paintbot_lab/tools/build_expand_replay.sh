#!/usr/bin/env bash
# Build a version-matched `expand_replay` binary for reading PAINTBOT replays.
#
# Moved here from ctf_lab on 2026-08-07 when that lab was archived; paintbot is a
# second manifest over the same coworld-ctf engine, so the reader is the same tool.
#
# Usage: paintbot_lab/tools/build_expand_replay.sh [--ref SHA] [--force] [--run REPLAY]
#   --ref SHA    coworld-ctf game ref to build against
#                (default: PAINTBOT_GAME_REF from tools/versions.env)
#   --force      re-fetch source and rebuild even if a cached binary exists
#   --run REPLAY build if needed, then run the binary on REPLAY (a .bitreplay)
#
# `expand_replay` re-simulates a recorded replay through the sim and validates a
# per-tick hash, so it expands a replay faithfully only when built from the SAME
# game version that recorded it. This builds at a matching source ref.
#
# `expand_replay_json <replay> [pos_every] [walkability]` — the optional third arg
# emits the exact startup wall map as `wall-runs-v1`, which `viewer_bundle.py`
# requires to draw generated Paintbot terrain.
#
# It is a HOST analysis tool (run locally to read a replay), so it builds native
# to this host's arch — no Docker, no amd64. The CTF game source + its bitworld
# dep are public, so the fetch and `nimby sync` need no credentials.
set -euo pipefail

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # paintbot_lab/
BIN_DIR="$LAB_DIR/tools/bin"
CACHE_ROOT="$LAB_DIR/.cache/coworld-ctf"

# The game source ref to build the tool from. It must contain tools/expand_replay.nim
# and be the same game version that recorded the replays (re-sim validates a per-tick
# hash). The default is this lab's single source of truth — versions.env's
# PAINTBOT_GAME_REF, which is also the game-sync ledger and the ref the player builds
# against. Bump it there, not here.
#   How you'll know to bump: this starts hash-failing on FRESH replays — that's the
#   signal the league redeployed. Resolve the deployed ref by grepping a 40-hex sha
#   out of `coworld show <cow_id> --json`; the parsed game.runnable.source_url field
#   reads None, but the sha is in the raw payload.
#
# READERS ARE MUTUALLY EXCLUSIVE BY ERA: a GV40 binary REFUSES a GV36 replay and vice
# versa ("Replay game version does not match"). The stable symlink tracks whatever was
# built LAST, so analysing an OLDER batch means building that era with --ref and then
# naming that era's binary explicitly:
#   viewer_bundle.py <episode-dir> --expand-replay tools/bin/expand_replay_json-<sha>
# Paintbot era pins: 6c7a4c0 = 0.7.215 (GV41); 9dedac0 = 0.7.211 (GV41);
# 871ace1 = 0.7.208 (GV40); 352d0e5 = 0.7.184 (GV36). Same-GV refs read each
# other's replays — the era gate is the GameVersion, not the ref.
# shellcheck source=/dev/null
source "$LAB_DIR/tools/versions.env"
: "${PAINTBOT_GAME_REF:?versions.env did not define PAINTBOT_GAME_REF}"
CTF_REF="${CTF_REF:-$PAINTBOT_GAME_REF}"
GAME_REPO_SLUG="Metta-AI/coworld-ctf"

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
if [[ -x "$out_bin" && -x "$json_bin" && "$json_bin" -nt "$LAB_JSON_SRC" && $force -eq 0 ]]; then
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
