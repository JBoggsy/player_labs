# paintbot_pw_lab working context

Use the current user request to establish the objective, scope and next decision.
Resolve the active game configuration, policy identity and roster through the platform
before evaluating or changing live participation. Source code and current API responses
define behavior; this file must not substitute for a live-state query.

Maintain only the active objective, unresolved constraints and next action here.
Replace completed or superseded context in place.

## Objective

**Build the strategy-as-source pipeline, then write the policy in it.** Both designs were
accepted on 2026-09-30 (James):

- [Strategy file format](docs/designs/2026-09-30-strategy-file-format.md): `strategy/STRATEGY.md`
  is the load-bearing source of truth (structured Markdown in Simplified Technical English;
  Knowledge, Situations, Skills, Capabilities, prioritized rules, Adaptations, Communication;
  five-level checks; telemetry v2). Compiled BASIC is never edited by hand; Skills carry authored
  `skill.bas`.
- [Compilation](docs/designs/2026-09-30-strategy-compilation.md): a Python driver
  (`pw.py strategy compile --agent claude|codex`) around one LLM step; one unit per component;
  `version.json` + compile report; gates G1-G5; the local screen never vetoes an intended
  behavior change.
- [Comms v1](strategy/comms.md): 9 scrambled 20-digit message types (focus calls, disguise
  friend/foe, sightings, grenades, glory hearts, pickups). Three engine questions to verify first
  (its §11).

**Next:** milestone M0 (tooling: `pw.py strategy lint|prepare|assemble|verify|compile|trace`, the
runtime skeleton, `AGENT.md` and wrappers), then M1: the first `STRATEGY.md` is a faithful
description of `base.bas` and must compile to base-equivalent play in a local screen. Our only
uploaded policy is still the unchanged starter `jb-pw-base:v1`. The lab is fully instrumented:
docs verified at `118e1619` (0.3.89), tools pinned to the same build with a shared terrain cache,
one agent entry point (`uv run python paintbot_pw_lab/tools/pw.py doctor|tools|<subcommand>
--json`), and seven lab skills including [paintbot-pw-loop](.claude/skills/paintbot-pw-loop/SKILL.md).

Inputs the policy (`STRATEGY.md`) should build on:

- What wins and how it is scored: [mechanics.md §1](docs/mechanics.md) (glory, margin-scaled Elo:
  speed and survival dominate; a win at t seconds is worth ~600 − t).
- How the field plays and who leads: [field.md](docs/field.md#how-the-field-plays-80-league-episodes-2026-09-29)
  and [the 80-episode analysis](docs/reports/2026-09-29-league-field-analysis.md) (elimination in
  78/80, champion lineages and styles, the Aaron `FIRE22`/`ITEM23` shout protocol, friendly fire,
  uniforms).
- Candidate levers with their evidence: [TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md) (abandoned
  grenade charges self-kill, uniforms are a liability or an infiltration tool, win by killing fast,
  lives decide matches, targeting disguised teammates).
- What a policy can do and afford: [policy-surface.md](docs/policy-surface.md) (BASIC surface,
  budgets: base.bas uses 18% of instructions, the neural lane).
- How we will test it: [paintbot-pw-ab](.claude/skills/paintbot-pw-ab/SKILL.md) and the loop charter below.

## Loop charter

Not set. The [paintbot-pw-loop](.claude/skills/paintbot-pw-loop/SKILL.md) skill runs only when
James fills this in; until then an agent proposes a charter and stops.

- objective: (e.g. raise the mean Elo outcome score vs the top 3 champions)
- policy_file: (e.g. paintbot_pw_lab/policy/dist/<name>.bas)
- policy_name / player: (upload name; player identity as shown by `uv run coworld player list`)
- baseline: (accepted version `name:vN`; the loop updates this line)
- opponents: (explicit `policy_ref`s)
- allowed_changes: (classes of change the loop may make without asking)
- credit_budget: (credits per iteration / per day; ~0.3 credits per episode)
- max_iterations:

## Identity and presence

- Account players: "James Botts" (default) and "Games Bond". James Botts runs `jb-pw-base:v1`
  (unchanged `base.bas`, uploaded and submitted 2026-09-30, champion in the paintbot-pw league and,
  by `entrants_from_league_id` chaining, auto-entered into Heartland and Heartland Big; see
  [field.md § Our account](docs/field.md#our-account)). Confirm `uv run coworld player list`
  marks the intended player (●) as active before any upload; `softmax status` shows only the user.
- Player session refreshed 2026-09-30 00:11 UTC; it expires 2026-10-01 00:11 UTC (`pw.py doctor` → `result.player`). Refresh with `uv run coworld player use ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce` before uploads.
- Credits: 20,000 balance at the cap, refilling ~1,429/day (2026-09-28). A league-like
  episode costs ~0.3 credits.

## Decisions for James

1. ~~Starting policy lane~~ **Decided 2026-09-30: plain BASIC**, compiled from `STRATEGY.md`
   (not the Jev advisor, not the neural ZIP lane).
2. **Player identity** for the real policy (James Botts, which already runs `jb-pw-base:v1`, or
   Games Bond / a new player). Ratings belong to the player.
3. **Heartland memberships:** submitting to the paintbot-pw league auto-entered `jb-pw-base:v1`
   into Heartland and Heartland Big (FFA-kin, out of scope). Retire them, or leave them?
4. **Evaluation roster:** `user_preferences.md` says hosted requests carry one copy of our policy
   (stated for Gods of the Arena's 10 seats). The paintbot-pw league seats one policy on all 8 seats
   of a team, so mirroring the league means 8 copies vs 8 pinned opponent seats (used so far).
   Confirm this exception for paintbot-pw.
5. **A/B default design:** paired on the Elo outcome score (built) vs unpaired `field` (the
   measurements argue for `field`: pairing needs one request per seed and barely reduced variance).
6. **The loop charter** above, if the loop should run unattended.
7. Defaults already taken (change any): paired/SPRT statistics added to the shared `coworld-ab`
   engine; the intent-telemetry knob defaults on; rerun.io not added.

## Next step (proposed)

Build milestone M0 of the [compilation design](docs/designs/2026-09-30-strategy-compilation.md)
(§11), then M1 (the `base.bas` description). Alongside it, get a baseline measurement: read
`jb-pw-base:v1`'s free league episodes as they accumulate (`pw.py scout fetch` / `pw.py episodes`)
or run an unseeded `field` request against each current champion (`pw.py leaders`; about 80
episodes, ~24 credits), then `paintbot-pw-diagnose`. The 4-episode seed pilot (2026-09-30) already
shows `aaron-paintbot-pw:v42` beating it from both sides.

## Measured findings (2026-09-29)

League facts (80 hash-verified 0.3.79 episodes; [field.md](docs/field.md#how-the-field-plays-80-league-episodes-2026-09-29),
[field analysis](docs/reports/2026-09-29-league-field-analysis.md)):

- 78 of 80 matches end by elimination (median 82 s); winning glory median 544, of which the
  countdown (−88) dominates and all awards add +42. Speed and survival decide rank.
- No side advantage in the league (odd seats 43/80, Wilson 43-64%). The local base-vs-base
  71% odd-side rate is a mirror-match effect, so keep local screens side-balanced anyway.
- Every league episode has its own engine seed (`crc32("<division>:<round_index>") + job
  index`); the API's `game_config.seed: 2026` is a placeholder. Live configs carry
  `behind_lives: 5, behind_cogs: 10`.
- Uniforms are a net liability: a disguised cog is hit ~31× as often per tick, mostly by its
  own team; 7.1% of all hits are friendly. Grenades: 100 self-kills vs 164 enemy kills.
- Top policies: the Aaron pair (flank opening, grenade-heavy, `FIRE22`/`ITEM23` shout
  protocol) and daveey-pw-neural (silent, gun-only, wins by killing, 74 s median win).

Tooling facts:

- Hosted tapes built with Nim 2.2.10 re-simulate hash-exactly under local Nim 2.2.6 (80/80
  0.3.79 episodes). Teams tapes carry header rules 48; the teams game plays rules 47.
- `pw_local` runs about 1.5 matches/s on 14 cores; `jev.bas` without an oracle plays
  move-for-move like `base.bas` (`local screen` reports `identical_play`).
- Seed pairing barely reduced outcome-score variance locally (per-pair SD 0.40 vs ~0.44
  unpaired); about 330 pairs detect +0.05 on the Elo outcome. An explicit request seed makes
  every episode of that request the same world, so a paired design needs one single-episode
  request per (arm, opponent, side, seed). Given the small variance gain, consider the unpaired
  `field` design the default (decision 5 below).
- `base.bas` peaks at 9,116 instructions and 15,538 work units per decision (18% / 12% of the
  budget); it aims at disguised teammates on ~1% of target lines and hits them in about half of
  those cases.

## Answered 2026-09-30

- The ladder-wide MMR drop (top ~2,370 → ~1,820) is Elo settling at a tighter spread under
  `margin_scale` (a win is worth ~0.77, not 1.0; max spread ~210 points), not a re-rating.
- The Jev oracle's model is allowed (platform allowlist null; the league setting is schema-only)
  and Beta very probably gets answers (its answer-triggered relay shouts appear in 20/20 episodes).
- Hearts ignore disguises: capture, credit and contest use the true team, and public heart state
  reveals a disguised capturer's real team ([mechanics.md, Disguise](docs/mechanics.md)).
- Explicit XP seeds fix the world (pilot: identical final hashes per request), and hosted seat logs
  come back for our own policy ([field.md § Seeds](docs/field.md#seeds-what-actually-reaches-the-engine)).

## Open constraints

- The docs are verified at, and the tools pinned to, `118e1619` (coworld-v0.3.89, the league's
  build on 2026-09-30; `tools/release.env` moved from 0.3.80 the same day). From 0.3.80 no teams
  rule changed (same hashes, same BASIC peaks), but 0.3.89 added `rnd(n)` (now a reserved host
  name: `pw.py local compile` accepts `x = rnd(10)` and rejects `rnd = 3`), moved BASIC perception
  into `seat_view.nim`, and retired every earlier neural contract. `pw_trace.nim` and `pw_map.nim`
  now define the wading test locally (0.3.89 removed `neural_contract.inWater`), and
  `deployed-ref` also diffs `seat_view.nim`, `neural_contract.nim` and `guide.md`. Record
  `coworld_version` per episode and never pool rules versions.
- 0.3.89's `-d:pwTraining` terrain table fills whole 64 × 64 blocks on first touch (upstream
  #183), which made every fresh lab process pay ~20 s. The tools now share one terrain file
  instead (`tools/.cache/terrain/<tag>/island-f2047.pwterrain`, 621 MB). It is built once per
  release in ~27 s, and later runs take `pw_trace` ~0.3 s per tape, `pw_map` 0.08 s, and a
  16-match screen 10.6 s. Results are identical. Disk is bounded: one file per release and
  terrain flag set, other releases' files deleted, LRU cap 2 GB (`PW_TERRAIN_CACHE_MAX_GB`),
  off with `PW_TERRAIN_CACHE=0`, inspect with `pw.py terrain-cache status`
  ([pw_release.md § Terrain cache](docs/tools/pw_release.md#terrain-cache)). This Mac's disk was
  99% full (4.6 GB free) on 2026-09-30, so the file is a real share of what is left.
- A seat that fails host staging now fails the whole hosted episode on the platform (no scores,
  no replay; round 2510, 2026-09-30), like a compile error. Findings about Alpha
  (`daveey-pw-neural`) from before 2026-09-30 describe a policy on the retired neural contracts.
- The Observatory replay wrapper does not forward a tick (`t=`); only the game's own viewer URL
  honors `?t=`. Match reports link episodes without a tick.
- Thresholds in `pw_flags`, `pw_fights`, `pw_metrics` and `pw_intent` are uncalibrated
  defaults; calibrate them on the first 100+ episode batch of our own policy.
