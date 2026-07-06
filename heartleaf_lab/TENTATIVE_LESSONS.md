# Heartleaf tentative lessons — session buffer

**Session started:** 2026-07-06 (lab created). This is THIS SESSION's lesson buffer.
Write candidate lessons here **as you go** — eagerly and noisily; most will be noise
and that's fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you write here
is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`heartleaf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Heartleaf-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Heartleaf ships a full behavior engine (`talking_villager`); "build a player" ≠ raw Sprite-v1 here
Evidence: `players/talking_villager/` (~3000 lines) already does perception → pathfinding
→ 8-verb semantic action layer → Bedrock LLM → chat; the 4 league players are that same
engine + different `soul.md`. Cheapest player path is a better prompt or a deterministic
decision layer, not a crewborg-style protocol build. Unlike Crewrift where crewborg decodes
Sprite-v1 itself.

### Heartleaf scoring makes guests a rivalrous shared resource — the game is coordination, not just gathering
Evidence: `score = hosted food × guests`; only hosts score, visitors score 0. With 9
gnomes, each guest at your table is denied to a rival host and is themselves not hosting.
Efficient gathering is necessary but the differentiator is recruiting a full table over chat.

### The heartleaf game repo is `coworld-incomplete` (certify not passing) — verify game version/league before relying
Evidence: README badge "coworld verify: failed"; repo topic `coworld-incomplete`;
COWORLD-REPO-STATUS note says certification blocked. Mirrors the freshness-preflight rule.
Status: league reported to exist but not confirmed via Observatory API this session.

### [SUPERSEDED 2026-07-06] "SDK ships no Sprite-v1" was true only of the STALE pin
Evidence: our pinned SDK (`6dcd022`, in the venv) had no sprite bridge, so the first Explore
concluded the SDK lacks Sprite-v1 and we'd vendor from crewborg. WRONG for current main:
coworld-tools PR #20 (merged `e8921a6`) adds `players.player_sdk.sprite_bridge`
(`run_sprite_bridge`, `SpriteWorld`, `Button`, exported from `__init__`). Lesson: **check
coworld-tools `main`, not just the pinned venv copy, before concluding the SDK lacks a feature** —
a stale tarball pin hides new SDK capabilities. (Freshness-preflight applies to the SDK pin too.)

### Heartleaf player rides the SDK SpriteV1 bridge — no vendored wire; compose runtime via a `decide` adapter
Evidence: `run_sprite_bridge(url, decide, ...)` owns transport + raw decode into `SpriteWorld`
(objects + sprites-with-labels; does NOT decode pixels) + exit-0-on-close. `decide(world, ctx)
-> mask|(mask,chat)|None`. To keep the AgentRuntime/Modes cyborg shape, a thin `decide.py` wraps
SpriteWorld in Observation → `runtime.step()` → unpack Command → (mask, chat). Bump pin
`6dcd022→e8921a6`; crewborg shares the SDK so run its tests after.

### Codex per-phase delegation worked well with a strong high-level plan + interface contracts up front
Evidence: cady v1 built in 6 phases; Phases 2–6 via `codex exec resume --last` (single thread for
type-continuity), each plan→review→implement→verify→commit. Codex caught a real SDK detail I
couldn't verify from outside (AgentRuntime calls `perceive(obs, tick)`, 2-arg, vs our 1-arg — it
added an adapter). Keys that made it smooth: (1) the plan's shared interface-contract block (the six
types, decide sig) kept phases consistent; (2) pointing Codex at crewborg as a working reference
in-repo; (3) I did the env-sensitive Phase 1 (uv pin bump, shared with crewborg) myself. Gotcha:
`codex exec` first line is the thread_id — do NOT `tail` the initial call's output or you lose it;
use `resume --last`. Codex's sandbox couldn't reach `~/.cache/uv` on first pytest run (it retried
with cache access) — ran Codex in the MAIN repo (not a worktree) so it used the synced venv.

### Heartleaf v1 needs NO pixel decode — everything is in sprite LABELS
Evidence: `heartleaf.nim` builds labels carrying the values: gnomes `"gnome <index> <dir>"`,
gardens `"garden marker"`, and the clock as per-glyph objects `"clock <char>"` (base 7000) —
read the time by sorting clock-glyph objects by x and joining their one-char labels, then
`parseClockMinutes`. So perception reads `world.objects` + `world.sprites[id].label` only; the
bridge's raw `SpriteDef.data` (pixels) stays untouched until A* over walkability is needed.

### Heartleaf's protocol.nim gives a clean object-id/label scheme — raw decode is tractable, but geometry isn't in it
Evidence: `src/heartleaf/protocol.nim` — stable bases (gnomes 1000, gardens 4000 w/ "garden marker",
clock 7000, inventory 5000/6000, chat 3000). BUT self-position (camera-centre + offset) and
house/garden trigger distances are NOT in the scheme — must be calibrated from a real stream
(a capture probe) before nav is trusted. Same self=camera pattern as crewborg.
