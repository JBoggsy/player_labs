# CTF tentative lessons — session buffer

**Session started:** 2026-07-21 15:19. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---
### The deployed game ref lives in the coworld manifest — `coworld show <cow_id> --json` → `game.runnable.source_url`
Evidence: replay expansion hash-failed on all fresh league replays (league moved 0.7.4 → 0.7.49 silently). The episode's `tags.coworld_id` → `coworld show` gave the exact source ref (c76e0c75) on the first try; no guessing commits. Faster and surer than "try newer commits until a fresh replay expands".

### League episodes carry identity as `policy_results` (agents[].agent_id = slot), not xreq-style `participants`
Evidence: warehouse built 0 participants from league fetches until `_load_episode_meta` learned the `policy_results` shape. Any tool written against xreq episode.json will silently produce empty identity tables on league data.

### Enrich replay events with sim state at emission time — position-less events can't answer strategy questions
Evidence: rewrote expand_replay_json to run its own re-sim loop and attach x/y/aim to kills/shots/steals plus periodic pos/flag_pos snapshots. Every load-bearing recon experiment (phase profiles, escort distance, enemies-alive-at-steal, kill depth) needed those fields; the upstream human-timeline API doesn't expose them, and re-fetching later costs a full rebuild anyway. When re-simming, emit state-of-the-world rows (periodic snapshots), not just deltas.

### Fetching the same league episodes under multiple policies' batches duplicates rows — dedup by episode_id before any aggregate
Evidence: 144 fetched episode dirs → 95 unique episodes (focusfire-vs-Picasso games arrived under both policies' fetches). Raw GROUP BYs double-counted until q.py added ROW_NUMBER()-dedup views (eps/parts/ev).

### High-level stat pairs can invert under mechanism queries — always decompose before narrating
Evidence: Picasso "steals a lot" (88, most in field) reads as strong flag offense; the carry anatomy shows median carry = 23 ticks, 0px progress, 5.7% conversion — its steals are near-worthless. Conversely focusfire's low steal count hides a hard gate (0 steals before tick 3000) that is the *strategy*, not a weakness. Correlation checks need the reverse-causality control (steal↔win vanished once pre-steal kill margin was conditioned on).

### A "focus fire" claim is testable from replay events alone: count distinct same-team shooters whose aim ray intersects the victim within a lookback window
Evidence: ray-attribution (bearing vs aim ≤7 brads, 72-tick window) separated focusfire (28% multi-shooter kills) from Picasso (18%) on the same episodes with the same estimator. No policy internals needed.
### The player observation wire is back to 1x map pixels since ctf 0.7.8 — the "3x render scale" era is over
Evidence: v6-v9 perception divided coords by 3 (correct for 0.6-0.7.7); at 0.7.49+ the POV stream is 1x (global.nim: boardScale=1 for player streams; RenderScale=2 is spectator-only), the aim-dot indicator is retired (self sprite id 5100+rot IS the aim readback, 16-step), and flags are labeled `<color> flag [planted]` not hearts. beacon v6 was effectively blind on the live game and sank to rank 6. Wire-format regressions across redeploys are silent — a policy that connects and idles looks "alive"; check the RULES.md + global.nim POV branch at the deployed ref after EVERY redeploy.

### The deployed game version moves mid-session — pin the replay reader per batch, read the ref from each xreq's coworld
Evidence: 0.7.49 → 0.7.51 between the recon fetch and the v10 measurement (2 hours). Each xreq reports its `coworld`; `coworld show <cow_id> --json` → manifest game.runnable.source_url gives the exact ref for expand_replay.

### Accuracy is a fire-discipline metric, not an aim metric: gate on range before improving prediction
Evidence: v10 lead-aim alone left acc at 0.234 because beacon fired 7,804 shots (~5x opponents' volume) — most beyond where the 5-brad aim quantization can hit the 14px corridor. A hold-fire gate at 350px (v11) moved acc to 0.333 with no aim change and IMPROVED wins (first-ever 7-3 Picasso, 8-2 autoresearch). Shot-volume parity matters more than per-shot cleverness.

### The fire windup releases from the shooter's CURRENT position — strafing through it displaces your own shot
Evidence: sim.nim applyFire uses the shooter's position at release (5 ticks after pull) with the ANGLE locked at the pull; a strafing shooter moves ~2.75px/tick → ~14px lateral displacement = one full hit-corridor. v12 freezes movement for FIRE_WINDUP_TICKS after each trigger pull (carrier exempt).

### Items activate via deterministic seat-claims with zero radio: assignment as a pure function of (seat) is enough
Evidence: v10's single-claimant table (seat 2→shield, 3/4→corner grenades) produced 20% shield alive-time (89% on the assigned seat) and real grenade throws in the first measured batch, with no coordination protocol — every agent computes the same table, so no two rush one pickup.
### Glass windows (GameVersion 15/16) break the "visible = shootable" assumption — fire gates need a bullet-LoS check
Evidence: windows pass vision but block bullets/plasma. beacon fired through them at guaranteed-miss rate until v14 added `mapdata.ray_clear` to the fire gate (windows stay in the wall mask since it models the BULLET question). Combined with boundary-crossing aim calibration this took acc 0.312 → 0.657 in one step.

### The 16-step aim readback yields an exact fix at step boundaries — calibrate on the CHANGE tick, not the value
Evidence: the self sprite's rotation quantizes aim to ±8 brads, too coarse to resync against directly; but the tick the observed step CHANGES while rotating, the true aim is at the boundary between steps (±rate/2 = ±2.5 brads). v14's boundary-crossing calibration was the biggest single accuracy lever.

### An A/B regression can be a MAP-truth signal, not a code signal — check the arena/geometry pins before reverting
Evidence: v12 (mechanically sound windup freeze) REGRESSED vs v11; the real cause was the arena changing under us (GameVersion 16 moved/removed obstacles; nav.npz was stale, agents pathed into ghosts). Reverting v12 would have been wrong; rebaking nav (v13) then v14 vindicated it. When a clean change regresses, verify the baked world model against the deployed ref first.
