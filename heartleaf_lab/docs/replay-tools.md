# Heartleaf replay debugging tools

Two tools turn a recorded episode replay into navigation/behaviour debugging
data: a **replay expander** (re-simulates the replay into per-tick positions +
events) and a **travel-line renderer** (draws those onto the baked map).

```
replay.json ──expand_replay──▶ expanded.jsonl ──viz_replay──▶ paths.png
 (episode artifact)            (positions+events)             (debug image)
```

## 1. `expand_replay` — replay → JSONL

A Nim tool that lives in the game repo (`Metta-AI/coworld-heartleaf`,
`tools/expand_replay.nim`, added in PR #15). It re-simulates the recorded inputs
through the real game sim and dumps JSONL. Because playback re-simulates, the
binary must be built from the **same game version that recorded the replay**; a
per-tick hash validates that and reports any mismatch in the trailing `summary`
row (`hash_failed`).

### Build it

```sh
heartleaf_lab/tools/build_expand_replay.sh          # -> heartleaf_lab/tools/bin/expand_replay
```

Host-native build (no Docker); fetches the pinned game source tarball, runs
`nimby sync`, and compiles. The pinned ref is `HEARTLEAF_REF` in the script —
currently the PR branch; bump it to the merge commit once PR #15 lands, and
again if the deployed league game advances and hashes start mismatching. The
binary is cached per ref; re-run with `--force` to rebuild, or `--run REPLAY`
to build-then-run.

### Run it

```sh
heartleaf_lab/tools/bin/expand_replay [--format jsonl|text] \
    [--snapshot-every N] <replay.json>
```

`--snapshot-every N` subsamples **position** rows (default 1 = every tick);
events always fire at their exact tick. Output rows (`type`):

- **`meta`** (first): `schema`, `seed`, `day_ticks`, `max_tick`, `food_names`.
- **`tick`**: `tick`, `day`, and `players[]` — each with foot-centre map pixels
  (`x`,`y`), `map` (0 = main map, 1..9 = a home), `house`, `dir`, `inv`, `score`.
- **`event`**: player-tagged (`slot`, `name`, `user`), one of:
  - `join` / `leave` — `home` (own house index)
  - `harvest` — `amount`, `total`, `foods` (each veggie **named**)
  - `enter_house` / `exit_house` — `house` index, `own` (their own home?)
  - `chat` — `text`, plus `heard_count` and `heard_by[]` (see hearing range below)
  - `score` — `amount`, `total`
  - `dinner` — `host`, `was_host`, `guests`, `food`, `score`
- **`summary`** (last): `ticks`, `hash_failed`, `hash_mismatch_tick`.

> **Chat hearing range.** Heartleaf has no explicit chat radius. A player
> *hears* a message when the speaker's speech bubble lands inside their
> 320×200 viewport (the camera follows each viewer, clamped at map edges) on
> the **same map** — so a house wall blocks it. Each `chat` event therefore
> carries `heard_by` (the other players in range, `{slot, name}`) and
> `heard_count`, computed from the game's real render geometry at the tick the
> line is spoken. (The bubble then lingers ~5 s, so a late arrival can still
> see it; the event captures the audience at the moment of speaking.) In
> practice a creek-side cluster yields ~3–6 hearers of 8, not the whole map.

> **Coordinate frame.** Player `x`,`y` are foot-centre pixels in the current
> map's frame — the **same frame as the baked walk grid** (`cady/mapdata.py`)
> and Cady's `self_xy`. So a position drops straight onto `WALK_GRID[y, x]`.

## 2. `viz_replay.py` — JSONL → travel-line image

Draws each main-map player's path over the baked walkability map, with gardens
(green) and houses (blue) outlined, start (circle) / end (square) markers, and
per-event markers. The path breaks wherever a player left the main map (a house
visit), so it never draws a misleading straight line across a house trip.

```sh
# pipe straight through:
heartleaf_lab/tools/bin/expand_replay replay.json \
    | uv run python heartleaf_lab/tools/viz_replay.py - --player Cady --out paths.png

# or from a saved JSONL:
uv run python heartleaf_lab/tools/viz_replay.py expanded.jsonl --out paths.png
```

- `--player NAME` — spotlight one player (its path bright, the rest dimmed).
  Use the **display name** (e.g. `Cady`), not the connection username.
- `--no-events` — travel lines only.
- `--scale N` — integer nearest-neighbour upscale of the output.

Requires `pillow` (a project dependency) and the baked map data in
`heartleaf_lab/cady/mapdata/`.

## What it's for

Debugging Cady's navigation: does her path hug the walkable corridors, reach
gardens, and land on harvest spots — or does it wander / stall? A spotlighted
path that follows the corridors and dots gardens with `harvest` markers is
working nav; one that clips walls or never reaches a garden is a routing bug.
The event stream also answers behavioural questions across *all* players (who
hosted, who attended, how much food, who chatted) for strategy work.
