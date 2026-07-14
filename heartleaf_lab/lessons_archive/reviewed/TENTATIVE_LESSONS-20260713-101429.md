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

### Heartleaf failure signal is NOT -100 (that's Crewrift-specific) — use failed_policy_index, and don't ops-filter score<=0
Evidence: heartleaf results_schema scores are `integer, minimum: 0` (0.1.0 AND deployed 0.1.10);
`heartleaf.nim:2565` score = food×guests, only hosts score. The metta coworld runner has NO -100
anywhere in source — on a player container failing/timing out it raises RunnerEpisodeError(
error_type="player_error"|"episode_timeout", failed_policy_index=slot) and fails the episode
(runner.py:765-792). So a non-connecting gnome scores 0, identical to a working-but-non-hosting
gnome. → Detect cady failures via episode status / failed_policy_index, NOT score<=0; a completed
0-score is a gameplay signal (never hosted), not an ops failure. Crewrift's "-100 = disconnect,
filter it" rule does NOT transfer to heartleaf.

### Deployed heartleaf (0.1.10) is AHEAD of the public repo (master 0.1.0) — 0.1.10 is deployment-only
Evidence: `coworld list` shows heartleaf 0.1.10 canonical; public Metta-AI/coworld-heartleaf master
= 0.1.0, no 0.1.10 tag/branch. `coworld download heartleaf` gives the deployed PACKAGE (manifest +
coworld_images.json + AGENTS.md), NOT Nim source. Manifest scoring/protocol identical to 0.1.0;
only roster change is an added base `villager` player. So we can't `git checkout` 0.1.10 — the
manifest is the authoritative deployed artifact; 0.1.0 source is the closest readable source.

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

### Replay re-sim: build in an ISOLATED dir (stale ../bitworld sibling shadows the pinned dep)
Evidence: compiling `tools/expand_replay.nim` in the coworld-heartleaf clone failed —
`bitworld/aseprite.nim: cannot open file: server`. Cause: the clone's `config.nims` adds
`RootDir/../bitworld/src` to the Nim path, and the sibling `~/coding/bitworld` (a stale checkout
for other games, only ais/aseprite/clients/tiled) SHADOWS the correct pinned bitworld in
`~/.nimby/pkgs`. Fix = what `build_expand_replay.sh` already does: extract the game source to an
isolated cache dir with no `../bitworld` sibling, so only the nimby-global dep resolves. Also:
`initSimServer` reads `data/*.aseprite` at runtime — the isolated build dir MUST include `data/`.

### Version-coupled replay re-sim: `hash_failed:false` is the empirical version-match proof
Evidence: heartleaf replays pin gameVersion "0.1.0" and re-simulate via `stepReplay` with a lenient
per-tick hash check. Building `expand_replay` from clone HEAD and expanding all 8 cady_v6 league
replays gave `hash_failed:false` end-to-end — i.e. that source ref reproduces the DEPLOYED game
exactly, dissolving the "deployed 0.1.10 vs internal 0.1.0" worry. Rule: don't guess about version
skew for replay tooling — expand a real replay and read the summary's `hash_failed`. If it flips
true, bump the build ref (per-game seed/dayTicks come from the replay header via `replaySimConfig`,
not a guess).

### Monolithic game module + private fields → add a small read-only snapshot API, don't widen core types
Evidence: `heartleaf.nim` is one 3800-line module; `Player`/`SimServer`/`Garden` fields have no `*`
(module-private), so an external `tools/` file can't read positions. Clean PR pattern (coworld-
heartleaf#15): add exported `ReplayPlayerSnapshot`/`snapshotReplayPlayers`/`replaySimConfig` helpers
that read the private state internally and return a purpose-built value — leaves the game's core
types untouched, keeps the tool's event-diffing + CLI + json coupling entirely in `tools/`.

### Player foot pixels == baked walk-grid frame (viz drops straight onto the map)
Evidence: sim `Player.x/y` is sprite-top-left in map pixels; `footXAt=+16, footYAt=+26` — identical
to cady perception's `FOOT_OFFSET=(16,26)`. So the expander's emitted foot `x,y` index directly into
`WALK_GRID[y,x]`; `viz_replay.py` needs no transform, and spotlighted paths visibly hug the walkable
corridors (confirming both the expander coords AND cady's own self-position math).

### Heartleaf chat "hearing range" = the speaker's bubble in your viewport (no explicit radius)
Evidence: `heartleaf.nim` gates chat delivery per-viewer — `addSpeechBubble` only emits the chat
object if `rectVisible(bubbleRect, ViewportWidth=320, ViewportHeight=200)` in THAT viewer's screen
frame, where the camera (`cameraXFor`, clamped at map edges) follows the viewer. So B hears A iff A's
speech bubble falls on B's 320×200 screen AND same `mapIndex` (a house wall blocks it — cross-map is
never heard). There is no distance constant; range = viewport visibility, slightly text-dependent
(wider bubble = marginally wider range). The bubble lingers `ChatLifetimeTicks=5*24`, so a late
arrival can still see it. Implication for cady's proximity-gated chat: "in range to be heard" ≈ target
within ~½ viewport (±160x/±100y from you) on your map — reuse `replayChatAudience`-style geometry, not
a radius. The expander now emits `heard_by` per chat by reusing the game's exact render geometry.

### SDK SpriteV1 players silently disconnect ~20-40s in — websockets default keepalive vs a sync decide
Evidence: Cady scored 0 in v1-v7 not from bad nav but because she disconnected ~20-48s into
EVERY game (tick ~456-1152, absent ~97%). `run_sprite_bridge` connects with the `websockets`
default keepalive (ping 20s/timeout 20s); the per-frame `decide` runs SYNCHRONOUSLY in the async
loop, delaying pong handling past the timeout so `websockets` tears the connection down. The SDK's
`exit_zero_on_unclean_close` prints "game over: server closed the connection" for ANY ConnectionClosed,
so a keepalive teardown looks identical to a normal end; heartleaf's `except CatchableError: removePlayer`
swallows it server-side too — NO error either side. Fix: `run_sprite_bridge(..., ping_interval=None)`
(the continuous frame stream is the liveness signal). Confirmed via `coworld-local-run`: all 9 self-play
instances dropped at tick ~800 before, all 9 survived to game end after. Debugging keys: (1) a tiny
policy_agent log (17KB vs 1.2MB) = the player that died early; (2) expand the replay and check each
player's LAST-SEEN tick — an early-leaver with no clean leave event is a disconnect, not gameplay;
(3) local self-play repro proves it's code, not infra. This likely affects ANY Python SpriteV1 SDK
player with a non-trivial sync decide — candidate SDK fix in coworld-tools.

### Know the game's EXACT rules/timing before building rule-gated behavior — write them down, sourced to code
Evidence: three consecutive "0 score" social evals (v12/v14) looked like invite-logic bugs; the real
cause was the CLOCK reading None every frame, which silently disabled every clock-gated phase
(invite/host never fired). Root cause was working from an APPROXIMATE timing model: (1) I assumed the
clock string was "3:00pm" but the game emits "<Weekday> 3:00pm" (one glyph/char) so the parse regex
rejected it; (2) I repeatedly miscalculated the dinner tick and assumed dinner = 6:00pm when it
actually RESOLVES at 6:55pm (DinnerTallyMinutes = DinnerMinutes+55); (3) I got a FALSE POSITIVE
"host floor verified" because everyone is teleported home at the end-of-day score screen — "home at
the day boundary" is not hosting. Fixes: strip weekday prefix in read_clock_string; wrote an
authoritative "Exact timing" table in docs/heartleaf-gameplay.md (every phase boundary, quantized
minute<->tick mapping, league dayTicks=2400+240 score screen=2640/day, resolve-vs-display times) all
sourced to game constants. LESSON: for any rule/time-gated agent behavior, extract the EXACT rules
from the game source FIRST and write them down (constants + minute<->tick math + resolve-vs-display
distinctions), and add a diagnostic for the actual sensed value (time_minutes) so a dead sensor is
visible immediately — don't infer from an approximate mental model. A wrong model fails silently.

### Add a diagnostic for every input a gated decision depends on
Evidence: SocialStrategy gates on last_time_minutes, but CADY_DIAG didn't log it — so a clock that
read None for the ENTIRE game was invisible across multiple evals; I inferred the bug indirectly for
hours. The moment I added time_minutes to the diag, one 3-episode eval showed None on every frame and
the root cause was instant. LESSON: when a decision is gated on a sensed value (time, self position,
inventory, map), log that exact value in the telemetry. A silent None/0 in a gate is the highest-cost,
lowest-visibility failure class.

### The deterministic floor alone scored 12/15 (mean 109) — build/verify the non-LLM strategy FIRST
Evidence: Cady's first-ever points came from the deterministic social floor with NO LLM: seek-crowd
invite → villagers hear a house-naming invite → their own commitment logic locks them to attend →
host at own house at the 6:55 resolve → score = food × guests (v16, 12/15 games, mean 109, max 239,
multi-guest dinners like 2×96=192). The villager's whole attend/host strategy is deterministic and
its commitment lock is exploitable by a plain templated chat — no model needed to be competitive.
LESSON: when the reference opponent is deterministic, the fastest path to points is to replicate +
exploit its determinism first, and reserve the LLM for the marginal gains (smart target selection,
persuasion) on top of a floor that already works. Don't gate first-points on the LLM.

### Only-hosts-score makes "get guests" the entire lever once you can host
Evidence: v11-v14 hosted reliably but scored 0 for want of guests; v16 added working invites and
immediately scored. The scoring function is food × guests and guests come only from being heard +
their commitment triggering. LESSON: for Heartleaf, gathering/hosting are necessary-but-worthless
without recruiting; prioritize guest-acquisition reliability over more food (harvest was already
125-150/game, plenty — the swing was entirely guest count).
