# Paintbot tentative lessons — session buffer

**Session started:** 2026-08-03 (lab bootstrap session). This is THIS SESSION's
lesson buffer. Write candidate lessons here **as you go** — eagerly and
noisily; most will be noise and that's fine. At the next session start, a hook
archives this file automatically and creates a fresh
[`../TENTATIVE_LESSONS.md`](../TENTATIVE_LESSONS.md).

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`paintbot_lab/tools/rotate_lessons.sh`) → periodic human+agent review that
clusters RECURRING lessons across archived sessions and graduates the keepers
to `best_practices.md` (Paintbot-specific) or the root `../best_practices.md`
(game-agnostic). Recurrence across sessions is the graduation signal.

---

### Paintbot is a manifest, not a codebase
Expected a separate paintbot game repo; it's the SAME coworld-ctf repo/binary
with a second manifest (`coworld_manifest_paintbot.json`) — zero paintbot
mentions in the Nim source. When recon-ing a "new" Coworld game, check whether
it's a variant registration of an existing engine before hunting for a repo.

### The live league is the ground truth for variants, not the manifest prose
The manifest describes clean 4-policy seating; live episodes showed 7+7+1+1 and
7+7+2 splits with named fillers, and a rotation dominated by `default` (the
FIXED arena) — none of which the docs state. `coworld episodes -r <round> --json`
on a completed round answered in minutes what the docs couldn't.

### "All maps are procgen" was half-true — verify premises against live data
The task brief said all paintbot maps are procedurally generated; the live
rotation runs the fixed classic arena ~half the time (`default` variant). The
architectural conclusion (online nav) survived, but scoring-mix conclusions
would not have.

### Beacon's mapdata API was the port seam
The entire beacon→stencil port hinged on one observation from the coupling
inventory: every map consumer went through mapdata.py's 8 functions. Rebuilding
that seam as an episode-scoped object (WorldMap) let ~5k lines of
nav/fight/belief/action port nearly unchanged. When forking a policy across
games, find the narrowest seam first and preserve its shape.

### Module-level lru_caches on world state are a procgen time bomb
Beacon cached map arrays in `functools.lru_cache` at module level — invisible
on a fixed map, silent cross-episode corruption under per-episode maps. The
stencil rule (no module-level map caches; belief owns the WorldMap) should be
checked in review whenever new map-derived state appears.

### The SDK TraceSink is `.record(TraceEvent)`, not a callable
Wrote the tracer against an imagined `sink(name, dict)` API; the real protocol
is `sink.record(TraceEvent(tick=, name=, data=))` (pydantic, extra=forbid).
Check `players/player_sdk/trace.py` before wiring telemetry.

### Campaign rounds stamp purpose:"ladder" — round metadata cannot distinguish the two
Misread the live Paintbot league as a variant-rotation ladder because campaign
rounds create ordinary Rounds with purpose "ladder" (campaign/episodes.py) and
the CLI leaderboard renders territory as a bare "Score" column. The tell that
cracked it: standings summed to exactly 100 (the cell count), and the odd
7+7+1+1 seatings matched the campaign's 2v2 captain+ally rosters. Check
`GET /v2/leagues/{id}/campaign` (enabled flag) before classifying any league
as ladder-run.

### Under the campaign, terrain is per-cell PINNED — map prep is viable again
Each cell carries a permanent map_seed/map_size injected into episodes as
mapSeed/mapSize overrides (target cell's map; deployed paintbot manifest
declares both knobs). All 100 triples are API-public and the generator is
deterministic public code — every board map can be regenerated offline. The
online WorldMap stays necessary (the wire still carries no seed), but a
per-cell knowledge layer (recognize the map by signature, load precomputed
data) is a legitimate future iteration.

### A stale Coworld CLI can hide current platform capabilities
Our 0.1.34 pin lacked `coworld campaign ...`; the API + softmax token filled the
gap during recon. Version 0.1.35 now ships those commands and is pinned locally.
Freshness preflight for campaign work should include a CLI-version check before
building an API workaround.

### Sprite-v1 ready pacing is the local self-play unlock
Paintbot already supports the one-byte `0x85` player-ready packet and defaults
`fastMode=true`, but the shared Python Sprite bridge never sends it. Opting
stencil into ready-after-decision took a native 300-tick 1v1 from 13.75s to
2.38s (22.2 to 129 ticks/s) without changing simulator ticks or actions.

### Native game plus host players beats the generic Docker runner for iteration
The generic runner starts one amd64 container per seat plus an amd64 game under
Rosetta on this arm64 Mac. A small command mistake (`--run` omitted) also made
it invoke the manifest's `/bin/baseline` inside the stencil image and wait until
timeout. Running the exact source-built Nim server natively and stencil from the
uv environment avoids both costs while retaining results, replay, events, and
per-seat logs.

### Local self-play is a high-throughput screen, not the field verdict
Four workers completed eight full 5,000-tick 1v1s in about 39s wall time, and a
16-seat 2v2 resolved in 16.17s. That makes matched knob screening cheap, but the
opponent is still stencil and campaign rosters/third-party dynamics differ;
rotate candidate teams locally, then use a smaller hosted field check to promote.

### Resolve the deployed game before every optimization batch
"Latest" for self-play means the live canonical Paintbot manifest, not local
`main`. Resolve its commit-pinned source URL, fetch that exact commit, and build
from a clean managed worktree. If resolution or verification fails, abort; a
fast batch against the wrong simulator creates confidently misleading signal.

### Freeze startup metrics before first-tick gameplay branches
The first navigation trace initially included item-routing flow fields on some
medium maps but not on slower giant maps, making cross-size timings incomparable.
Freeze the metric immediately after invariant startup work. In the corrected
100-game profile every seat built exactly two startup Dijkstra fields; giant
p95 was 419 ms under 16-process contention, with Dijkstra ~82% of the cost.
