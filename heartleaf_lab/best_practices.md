# Heartleaf best practices

Heartleaf-specific practices for the improvement loop — layered on top of the
**game-agnostic** [`../best_practices.md`](../best_practices.md) (read that first;
these are additions, not replacements). Distilled from real work in this lab; treat
as defaults and **warn the human if a request would contravene one** before
proceeding. Add to this file as we learn more about *this game's* failure modes.

The graduation pipeline fills this in: candidate lessons accumulate in
[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md), and `/lessons-review` promotes the
ones that recur across sessions into durable practices here. The live, evolving
game knowledge lives in [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md), [`docs/`](docs/),
and the buffer.

## Scoring and strategy — guests are the entire lever

- **Only hosts score, and `score = hosted food × guests`.** Gathering and hosting
  are necessary but worthless without recruiting: cady's v11–v14 hosted reliably
  with 125–150 food and scored 0 for want of guests; v16 added working invites and
  immediately scored (12/15 games, mean 109). Prioritize guest-acquisition
  reliability over more food — with 9 gnomes, every guest at your table is also
  denied to a rival host, so the game is coordination/recruiting, not gathering.
- **Exploit the deterministic villager before reaching for the LLM.** The bundled
  villager's attend/host logic is deterministic and its commitment lock is
  triggered by a plain templated house-naming invite it can hear. The no-LLM
  social floor alone earned cady's first points; reserve the LLM for marginal
  gains (target selection, persuasion) on top of a floor that already works.
  Don't gate first points on the model.

## Game rules and timing — extract exact rules from source before gating behavior on them

- **Write down the exact rules, sourced to game constants, before building
  rule/time-gated behavior.** Three consecutive 0-score evals were caused by an
  *approximate* timing model, not bad strategy: the clock emits
  `"<Weekday> 3:00pm"` (a weekday prefix the parser rejected), and dinner
  *resolves* at 6:55pm (`DinnerMinutes + 55`), not the 6:00pm display time. The
  authoritative table lives in [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md)
  ("Exact timing") — trust it, and extend it from source when a new rule matters.
  Beware the end-of-day false positive: everyone teleports home for the score
  screen, so "at home at the day boundary" is not evidence of hosting.
- **Log every sensed value a gated decision depends on.** The clock read `None`
  every frame for multiple whole evals and was invisible because the diagnostic
  didn't include `time_minutes`; adding it exposed the dead sensor in one
  3-episode eval. A silent `None`/0 in a gate is the highest-cost,
  lowest-visibility failure class — instrument the gate inputs, not just the
  decisions.

## Operations — connection health and failure signals

- **Pass `ping_interval=None` to `run_sprite_bridge`.** The `websockets` default
  keepalive (20s ping / 20s timeout) tears down the connection when a synchronous
  `decide` delays pong handling — cady silently disconnected ~20–48s into *every*
  game for v1–v7, with no error on either side (the SDK exits 0 on any close;
  the server swallows it). The continuous frame stream is the liveness signal.
  Verified by local self-play: all 9 instances died at ~tick 800 before the fix,
  all 9 survived to game end after. Any non-trivial sync `decide` on the SpriteV1
  bridge is at risk.
- **Detect player failures via episode status / `failed_policy_index`, never via
  score.** Heartleaf scores are `integer, minimum: 0` — there is no Crewrift-style
  −100 disconnect sentinel. A container failure fails the episode with
  `RunnerEpisodeError` and a `failed_policy_index`; a *completed* 0-score episode
  is a gameplay signal (never hosted / no guests), not an ops failure. Do not
  ops-filter `score <= 0`.
- **Early-disconnect triage:** a suspiciously small `policy_agent` log (~17KB vs
  ~1.2MB) marks the player that died early; expanding the replay and checking each
  player's last-seen tick separates a disconnect (early leaver, no clean leave
  event) from gameplay; a local self-play repro proves it's code, not infra.

## Perception — labels, calibrated geometry, viewport-gated chat

- **Everything cady needs is in sprite labels — never decode pixels.** Gnomes are
  `"gnome <index> <dir>"`, gardens `"garden marker"`, and the clock is per-glyph
  objects (`"clock <char>"`, base 7000) read by sorting on x and joining. Raw
  `SpriteDef.data` stays untouched except for the baked walk grid.
- **Geometry is calibrated, not in the protocol.** Self-position is
  camera-centre + offset (same pattern as crewborg), and foot pixels are
  sprite-top-left + `FOOT_OFFSET=(16,26)` — identical in the sim and in cady's
  perception, so expander foot coordinates index directly into `WALK_GRID[y,x]`.
  Calibrate any new geometric assumption against a real capture/replay before
  trusting nav on it.
- **Chat "hearing range" is viewport visibility, not a radius.** B hears A iff
  A's speech bubble falls inside B's 320×200 camera-clamped screen on the same
  map (house walls block; cross-map is never heard). "In range to invite" ≈
  target within ~½ viewport (±160x/±100y) — reuse the
  `replayChatAudience`-style render geometry, and note the bubble lingers
  `ChatLifetimeTicks = 5×24`, so late arrivals can still see it.

## Version skew and replay tooling

- **The deployed manifest is the authoritative game artifact; the public repo can
  lag it.** Deployed heartleaf 0.1.10 has no public tag — `coworld download
  heartleaf` yields the manifest, not Nim source, and 0.1.0 source is the closest
  readable reference. Don't `git checkout` a deployed version that doesn't exist.
- **Prove version match empirically with `hash_failed:false`, don't guess.**
  Replays pin the game version and re-simulate via `stepReplay` with a per-tick
  hash check; expanding real league replays and reading the summary's
  `hash_failed` is the test of whether a source ref reproduces the deployed game
  (it dissolved the 0.1.10-vs-0.1.0 worry). If it flips true, bump the build ref —
  seed/dayTicks come from the replay header, never a guess.
- **Build replay tools in an isolated dir** (what `build_expand_replay.sh` does):
  the clone's `config.nims` puts `../bitworld` on the Nim path, so a stale sibling
  checkout shadows the pinned nimby dep. The isolated build dir must include
  `data/` — `initSimServer` reads `data/*.aseprite` at runtime. Details in
  [`docs/replay-tools.md`](docs/replay-tools.md).
