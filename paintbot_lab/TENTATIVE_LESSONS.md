# Paintbot tentative lessons — session buffer

**Session started:** 2026-08-03 (lab bootstrap session). This is THIS SESSION's
lesson buffer. Write candidate lessons here **as you go** — eagerly and
noisily; most will be noise and that's fine. At the next session start, a hook
archives this file automatically to [`lessons_archive/`](lessons_archive/) and
creates a fresh one.

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
