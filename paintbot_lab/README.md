# Paintbot lab

The lab contains Stencil, a native Nim direct-input policy, analysis/viewer tools,
and an experimental learned-policy pipeline. Read [the lab guide](AGENTS.md),
[game reference](docs/paintbot-gameplay.md), and [documentation index](docs/README.md).

The public game manifest uses `battle-royale-s2` play-calling control. Stencil's
capture-the-heart/input-mask behavior needs a compatible configuration; do not
assume it can enter that variant unchanged. Resolve active leagues and memberships
live instead of treating a document as a leaderboard.

## Layout

- `paintbot/stencil_nim/`: Stencil implementation.
- `paintbot/rl/`: learned-policy data, training and evaluation tools.
- `tools/`: build, replay, navigation, comparison and campaign instruments.
- `docs/`: game, analysis, communication and evaluation references.
- `WORKING_CONTEXT.md`: active objective and unresolved decisions.
- `TENTATIVE_LESSONS.md`: candidate guidance awaiting stronger evidence.

## Quick commands

```sh
paintbot_lab/tools/build_player.sh stencil           # build the image (amd64)
uv run coworld upload-policy players-stencil:dev --name stencil   # upload (inert)
uv run python paintbot_lab/tools/self_play.py --variant 1v1 --episodes 1  # debug only
```

## Local debugging

Local self-play—including full-seat variants—is not a tournament test because
it does not reproduce the live opponent field and campaign cell contract. Use it to profile, reproduce,
or inspect a mechanism. Use hosted requests that satisfy the
[`tournament-like experience-request contract`](docs/tournament-like-experience-requests.md)
for every gameplay conclusion.

Before every batch, `tools/self_play.py` resolves the live canonical Paintbot
version, fetches its exact commit-pinned `coworld-ctf` source, and builds in a
managed detached worktree under `.cache/`, synchronizing the commit's pinned
Nim dependencies first. It fails without starting episodes
if live resolution, fetching, or source verification fails, so a stale or dirty
local checkout cannot silently contaminate an optimization run. It runs that
Nim simulator and every control seat as native processes;
`--candidate-runtime docker` exercises the release image for the candidate
team. The default avoids Docker/Rosetta and sends Sprite-v1's `0x87`
sprites-off and `0x85` ready packets
after every decision, reducing bot-only traffic and letting the server advance
as soon as every seat has acted instead of sleeping at 24 ticks/s. Every
episode writes `results.json`, replay, events, game log, and
per-seat logs. The harness shortens only the pre-game countdown and post-game
end card; gameplay ticks, observations, decisions, and outcomes use the real
simulator unchanged.

```sh
# Local debug reproduction; current 1v1 itself has 16 seats.
uv run python paintbot_lab/tools/self_play.py \
  --variant 1v1 --episodes 20 --workers 4

# Local mechanism probe. Only the candidate team's processes get this env.
uv run python paintbot_lab/tools/self_play.py \
  --variant 2v2 --episodes 20 --workers 2 \
  --candidate-env STENCIL_TOPOLOGY_MERGE_DEPTH_PX=6

# Full-roster local structural/debug run (still not a tournament verdict).
uv run python paintbot_lab/tools/self_play.py --variant 4ffa8

# Profile online WorldMap construction and first-decision flow fields.
uv run python paintbot_lab/tools/self_play.py \
  --variant 1v1 --map-size giant --episodes 20 --workers 8 \
  --max-ticks 40 --profile-nav-init

# Capture the exact nav grid, cover, posts, anchors, and lazy flow fields, then view them.
# --map-seed pins the generated map (e.g. a live campaign cell's map_seed) —
# 1v1/2v2 maps reproduce hosted terrain bit-exact; 4ffa has a known slight
uv run python paintbot_lab/tools/self_play.py \
  --variant 1v1 --map-seed 386501705 --episodes 1 --max-ticks 40 --visualize-nav
uv run python paintbot_lab/tools/render_nav.py \
  paintbot_lab/self_play/<run>/episode-0000/players/slot-00.trace.jsonl
```

`--visualize-nav` enables the otherwise off `STENCIL_TRACE_NAVIGATION=1`
payload. The trace contains `navigation_map` once per map (schema v3 since
rooms, chokepoints, directional cover, defense gates, topology knobs,
and a packed dump of the exact clearance field) and a `navigation_flow` event
whenever the policy lazily computes a new Dijkstra goal. `render_nav.py`
accepts either that JSONL trace or a hosted player artifact ZIP and writes a
standalone HTML viewer with toggles and per-cell inspection.

`render_topology.py` (same input trace) goes deeper: it re-runs the exact
topology code on the agent-logged clearance via `topology_debug.nim`,
cross-checks the recomputed rooms/chokes/cover/gates against the agent-traced
finals (hard error on drift), and writes an HTML viewer that *replays the
watershed flood* level-by-level with the merge-decision log, per-cell cover
roses, and the defense-gate scoring table:

```sh
uv run python paintbot_lab/tools/render_topology.py \
  paintbot_lab/self_play/<run>/episode-0000/players/slot-00.trace.jsonl --open
```
Post-front selection overlays the bounded candidates, selected firing cells,
nearby duck cells, score components, and forward firing rays actually computed
by that team-colored agent. Fully traced artifacts also overlay that specific
agent's assigned post, paired duck point, and scored sightline axis.
The opt-in keeps routine multi-seat telemetry from duplicating large grids.

The harness uses `~/coding/coworlds/coworld-ctf` only as a source clone: it
fetches `origin` but never changes that checkout's branch or working tree. Every
summary records the live Coworld ID/version, manifest hash, source URL, and
exact source commit. Local self-play is a debugging instrument, never evidence
against the live opponent field. In campaign `2v2` mode, a normal captain owns
seven seats and an allied entrant owns one seat; local candidate/control
seating does not automatically reproduce that commissioner layout.

## Replay viewers: belief overlay versus navigation knowledge

These are different tools:

- **Agent belief replay overlay** — [`tools/viewer.html`](tools/viewer.html), fed by a
  `viewer_bundle.json` from [`tools/viewer_bundle.py`](tools/viewer_bundle.py). It synchronizes
  ground-truth replay positions with each Stencil agent's tick-by-tick belief,
  objective, tracks, item state, danger field, and heard-event traces. It also
  shows a potential ally gun-coverage heatmap: visible and fresh tracked gun
  carriers' fuzzed 16-step headings projected through the guaranteed 45-degree
  cone, capped at gun range, discounted when track-only, and clipped by
  pixel-wall line of sight. The belief panel reports covered-cell share,
  visible/headed ally counts, heading precision, and danger mean/max at the
  selected snapshot. Ground-truth player and flag colors come from the
  episode's authoritative slot-team configuration, including four-team FFA.
  The exact-version replay reader
  supplies the episode's startup walkability mask; generated Paintbot maps do
  not use Beacon's baked arena. Use this for gameplay diagnosis.
- **Navigation knowledge viewer** — `paintbot_lab/tools/render_nav.py`. It
  renders one agent's static/generated map knowledge, posts, rays, and cached
  flows. It does not replay the agent's changing belief state.

For one fetched, full-seat hosted episode:

```sh
# Builds at versions.env's PAINTBOT_GAME_REF into tools/bin/.
paintbot_lab/tools/build_expand_replay.sh
uv run python paintbot_lab/tools/viewer_bundle.py <episode-dir>
python3 -m http.server -d paintbot_lab/tools 8766
# Open http://localhost:8766/viewer.html and load <episode-dir>/viewer_bundle.json.
```

The reader re-simulates the replay and validates a per-tick hash, so it must be
built from the game version that recorded the episode. The default comes from
this lab's [`tools/versions.env`](tools/versions.env) — bump it there, not in the
script. The bundle needs the fetched replay plus Stencil
`policy_artifact_<slot>.zip` files for overlays.

To expand an **older** episode, build that era and name its binary explicitly —
readers are mutually exclusive by GameVersion, and the stable symlink tracks
whatever was built last:

```sh
paintbot_lab/tools/build_expand_replay.sh --ref <that episode's source commit>
uv run python paintbot_lab/tools/viewer_bundle.py <episode-dir> \
  --expand-replay paintbot_lab/tools/bin/expand_replay_json-<sha>
```
