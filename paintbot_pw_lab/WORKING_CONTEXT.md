# paintbot_pw_lab working context

Use the current user request to establish the objective, scope and next decision.
Resolve the active game configuration, policy identity and roster through the platform
before evaluating or changing live participation. Source code and current API responses
define behavior; this file must not substitute for a live-state query.

Maintain only the active objective, unresolved constraints and next action here.
Replace completed or superseded context in place.

## Objective

None chosen yet. The lab is stood up and fully instrumented (2026-09-29): source-verified
references (docs at `570174a2`, coworld-v0.3.78), the tools of the
[tooling plan](docs/designs/2026-09-29-tooling-plan.html) T0-T15 with one agent entry point
(`uv run python paintbot_pw_lab/tools/pw.py doctor|tools|<subcommand> --json`), and seven lab
skills including the autonomous [paintbot-pw-loop](.claude/skills/paintbot-pw-loop/SKILL.md).
No policy of ours has been written or uploaded.

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

- Account players: "James Botts" (default) and "Games Bond". Neither has a policy,
  membership or submission in any paintbot-pw league. Confirm `uv run coworld player list`
  marks the intended player (●) as active; `softmax status` shows only the user before the first upload (`coworld-player-swap` skill).
- The active player session (James Botts, `ply_53fb05a6-…`) expired 2026-09-16 (`pw.py doctor` → `result.player`); refresh with `uv run coworld player use` before any upload, or uploads bind to the user's default player.
- Credits: 20,000 balance at the cap, refilling ~1,429/day (2026-09-28). A league-like
  episode costs ~0.3 credits.

## Decisions for James

1. **Target league.** Recommended: the main teams ladder (`league_b9458ff8-…`), which has a
   real field (Aaron L, David B, Richard H). Heartland is now its own coworld.
2. **Player identity** for this game (James Botts, Games Bond, or a new one).
3. **Starting policy lane:** plain BASIC from `base.bas`, the Jev LLM advisor (`jev.bas`;
   needs the league to grant seats an LLM budget — locally, with no oracle, it plays exactly
   like base.bas), or the neural ZIP lane (David's `daveey-pw-neural` is #2).
4. **The loop charter** above, if the loop should run unattended.
5. Defaults taken while building the tools (change any): A/B design = paired against a common
   opponent on the Elo outcome score (the measurements below argue for unpaired `field` as the
   default: pairing costs one request per seed and barely reduced variance); paired/SPRT statistics added to the shared `coworld-ab`
   engine; the intent-telemetry knob defaults on; rerun.io not added.

## Next step (proposed)

Upload `base.bas` unchanged as our baseline, evaluate it against each current champion with a
`field` request (`pw.py ab-requests --design field --baseline X --candidate X ...`), then run
`paintbot-pw-diagnose` on that batch to choose the first change.

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

## Open constraints

- The docs are verified at `d0728ab1` (coworld-v0.3.79); the league moved to 0.3.80 (`c8dd1def`,
  viewer-only change, rule-bearing files identical) the same evening and the tools pin it.
  Releases ship several times a day: `pw.py deployed-ref --json` lists rule-file changes since
  `PW_DOCS_SHA`; record `coworld_version` per episode and never pool rules versions.
- Hosted seat logs for our own policy in our experience requests: expected, not exercised
  (needs our first upload; required for intent telemetry and VM-error detection).
- The Observatory replay wrapper does not forward a tick (`t=`); only the game's own viewer URL
  honors `?t=`. Match reports link episodes without a tick.
- The league sets no LLM spend cap; whether the oracle's model passes the platform allowlist and
  Beta's oracle asks succeed in league play is unverified (needs a seat log).
- MMRs across the ladder dropped sharply on 2026-09-29 (top ~2,370 → ~1,820), probably a re-rating
  after `margin_scale` was set; unconfirmed.
- Thresholds in `pw_flags`, `pw_fights`, `pw_metrics` and `pw_intent` are uncalibrated
  defaults; calibrate them on the first 100+ episode batch of our own policy.
