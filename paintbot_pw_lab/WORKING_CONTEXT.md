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
   opponent on the Elo outcome score; paired/SPRT statistics added to the shared `coworld-ab`
   engine; the intent-telemetry knob defaults on; rerun.io not added.

## Next step (proposed)

Upload `base.bas` unchanged as our baseline, evaluate it against each current champion with a
`field` request (`pw.py ab-requests --design field --baseline X --candidate X ...`), then run
`paintbot-pw-diagnose` on that batch to choose the first change.

## Measured findings (2026-09-29, tool verification runs)

- Hosted tapes built with Nim 2.2.10 re-simulate hash-exactly under local Nim 2.2.6 (2 hosted
  0.3.78 episodes). 0.3.78+ stamps teams tapes with header rules 48; the teams game plays rules 47.
- 38 of 40 public league 0.3.78 episodes (and 57 of 60 local) ended by elimination; in the
  win-probability fit, lives dominate and meter plus hearts alone predicted nothing held-out.
- Local screening: `pw_local` runs about 1.5 matches/s on 14 cores. Base vs base has a large
  side asymmetry locally (odd seats won 10 of 14 on seeds 1-14), so every local screen must
  use both sides.
- Seed pairing barely reduced outcome-score variance locally (per-pair SD 0.40 vs ~0.44
  unpaired; head-to-head per-episode SD 0.29); about 330 pairs detect +0.05 on the Elo outcome.
- `base.bas` aims at its own disguised teammates: a disguise fools teammates too and base.bas
  filters targets by observed seat parity (35 of 4,718 target lines in 6 local matches). Whether
  it fires on them, and the cost, is not measured.

## Open constraints

- The league runs `coworld-v0.3.79` (`d0728ab1`); the docs are verified at `570174a2` (0.3.78).
  0.3.79 changed only the neural lane and training internals. `pw.py deployed-ref --json`
  lists rule-file changes since the docs' commit.
- Not yet observed live: a league episode's `game_config.glory` showing `behind_cogs: 10`
  (source and manifest say so). Check with the first hosted batch.
- Does an explicit `game_config_overrides.seed` also fix the engine seed? This decides whether
  paired A/B pairs identical worlds or only identical requests. Settle with a 2-3 episode
  pilot in the first hosted A/B.
- Hosted seat logs for our own policy in our experience requests: expected, not yet exercised
  (needed for intent telemetry and VM-error detection).
- Whether the Observatory replay wrapper honors a `t=<tick>` parameter (match reports link it
  with a caveat).
- Releases ship several times a day; record `coworld_version` per episode and never pool rules
  versions in one comparison (`compare` refuses).
- Thresholds in `pw_flags`, `pw_fights`, `pw_metrics` and `pw_intent` are uncalibrated
  defaults; calibrate them on the first 100+ episode batch.
