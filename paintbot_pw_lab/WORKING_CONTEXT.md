# Paintbot PW working context

## Current objective and boundary

The optimizer loop is authorized by `tmp/collab/optimizer/BRIEF.md`, subsequent verdicts,
and James's local-first iteration-2 direction. Iteration 1 selected and uploaded range+HP
as `jb-pw-opt:v2` (61662d47-c26e-4873-ac13-333f70d6b341), build `32ed3f70-1`.
Its hosted confirmation is still downloading under shared API throttling. Iteration 2
uses 24 recorded local games (seeds101–112, both sides) to select grenade charge continuity:
173 teammate grenade HP exceeds gun129 and spray46; short throws account for98 teammate
and154 self HP. Strategy source now specifies committed charging with per-throw telemetry.
See `tmp/collab/optimizer/REPORT-2.md` for current build and qualification evidence. The optimizer never submits,
posts publicly or pushes Git. The orchestrator owns submission and its separate upstream
starter stopgap; do not replace that entrant or infer its identity from our upload.
Rank-9 rating archaeology is explicitly dropped by VERDICT-0.

The pipeline remains strategy-as-source: edit `strategy/STRATEGY.md` or authored skills,
commit inputs, then run `pw.py strategy compile`. Compiled builds are immutable. A compiler
infrastructure change may edit runtime templates, generators and contracts; coordinate such
changes at committed build boundaries with parallel compiler work. The maintainer entry point
is [docs/strategy-compiler-maintainers.md](docs/strategy-compiler-maintainers.md).

## Active baseline and qualification

- Release: `coworld-v0.3.123`, engine `28030de6`, simulation rules 49. Both tools and native
  library rebuilt; 30 current public replays hash-verified. Live ranking settings: OpenSkill,
  `margin_scale: 600`, `round_scoring_rule: mean`. Refresh live state before evaluation.
- Policy: **`jb-pw-opt:v1`**, version **`bac0d7d0-60f3-4c76-a1e6-aa947f9958ed`**, James Botts
  (`ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce`). Uploaded with coworld 0.1.57; softmax-cli 0.26.38.
- Build: [`2898e485-1`](strategy/compiled/2898e485-1/report.md), from committed foundation
  strategy port. All G1–G5 passed first round; 33 artifact hashes verified. Upload provenance
  is in `strategy/compiled/uploads.jsonl`. Hosted performance is not yet measured.
- G2: 16 enabled seats. G3: sampled peak 10,241 instructions / 17,329 work units.
  Static telemetry bound 313 bytes / 51 events. G4: 56 full matches, no bad seats, 22 wins /
  34 losses; side-balanced local outcome 0.450357, 95% interval [0.384288, 0.516426].
- G5: 3,477 lines from 16 candidate-seat recordings, all required fields and both message
  types exercised, no failures. This is transport/coverage, not a semantic or competitive pass.
- G4 reference is upstream's ported starter copied verbatim at `28030de6` into
  `reference/base-bassy-28030de6.bas`. It also changes targeting range, HP/pickup handling,
  and support behavior. Exact identity is therefore not claimed. The regression screen passed;
  the wide interval does not establish statistical non-inferiority or equality.

Bassy changed `/` to fixed-point division, comparisons to -1, and logical operators to bitwise.
The foundation port preserves integer division using `\`, explicit 0/1 outputs, and legacy
host calls still supported by Bassy. Source strategy/thresholds are unchanged. A release change
now invalidates component reuse. Compiler unit validation rejects fixed-point `/` under the
integer strategy contract. Existing runtime lib/main required no semantic edits. Inactive M3
codec runtime and units have **not** been ported or requalified.

M3 remains an inactive lever: source recoverable at `2184fc64`, immutable build `18e0aa1f-1`,
protocol and limitations in [strategy/comms.md](strategy/comms.md). Its 0.3.115 hosted A/B was
inconclusive. Do not substitute it for the current baseline.

## Evidence limits and next experiment

The current public scout (`episode_data/optimizer-task0/scout.json`) found near-total
inactivity and zero shots for zhar, finist, relh and our old jb-pw-base. Xolod was active.
Both the frozen starter and old foundation disabled all 16 seats in direct 0.3.123 diagnostics.
Do not interpret old-runtime wins or wins against inactive opponents as current field strength.
Re-resolve opponents before evaluation; the useful field may change as policies are ported.
The scout report's historical margin-1000 Elo column is not the current ladder score.

The foundation still targets to 52.5 m despite ordinary gun reach about 21 m, retains old
3-HP strategic thresholds despite 10 HP / one life, and can abandon grenade charges.
These are separate candidate changes, not part of the Bassy port. Every new or re-gated
behavior must include activation tracing. Report hypotheses to the orchestrator.

Five inherited compiler guesses remain open (four low, one medium); none is new to the port.
Private motor state and several source check thresholds remain unlogged/unspecified, so G5
cannot establish all five audit levels. Never promote an unmeasurable or unexercised check to
pass. The 0.3.115 M2/M3 audit evidence does not requalify the audit engine at 0.3.123.
`PW_DOCS_SHA` remains `118e1619` for unreverified neural/oracle references; current raw-BASIC
facts have explicit currency blocks in mechanics, policy-surface and evidence docs.

## Loop charter

Set 2026-10-06 by the orchestrator (Claude Opus 5.5 session) under James's delegation: James
gave that session full control of Paintbot PW, including league submission. The optimizer
reports to the orchestrator, not to James; see `tmp/collab/optimizer/` for briefs and verdicts.

- objective: raise mean `score_outcome` (`--target score_outcome --margin-scale 600`, recheck the
  live margin) of our policy against currently active league opponents, then climb the
  paintbot-pw league standings with a submitted improvement.
- policy_file: `paintbot_pw_lab/strategy/STRATEGY.md` plus authored `strategy/skills/*/skill.bas`,
  compiled with `pw.py strategy compile`. Never hand-edit compiled policy BASIC; compiler-owned runtime templates are editable infrastructure. Working source starts
  from the foundation build `3d0f8a4f-1` (baseline play, compact telemetry), not M3 comms.
- policy_name / player: `jb-pw-opt` on James Botts (`ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce`).
- baseline: `jb-pw-opt:v1`, version `bac0d7d0-60f3-4c76-a1e6-aa947f9958ed`, build `2898e485-1`.
- candidate: `jb-pw-opt:v2`, version `61662d47-c26e-4873-ac13-333f70d6b341`, build
  `32ed3f70-1` (real gun range plus spawn-HP supply thresholds). Working source matches it.
  Support/follow experiments are retained in builds `28ad2e2a-1` and `faf2ea88-1`, but local
  selection favored the HP build. Hosted A/B against deployed `jb-pw-base:v2` is pending.
- opponents: refresh the current leaderboard plus recent public 0.3.123 episodes every iteration;
  keep real opponents with shots or kills above zero in scout. Current round-834 sample:
  `xolod:v14`, `paintbot-pw-basic-v22:v1`, `daveey-pw-league-smoke-l17c-s41u150-hc:v1`.
  Exclude our own policies and inactive unported leaders. Evidence: `tmp/collab/optimizer/iteration1-scout/`.
- local benchmark: `reference/base-bassy-28030de6.bas`, 28 seeds × both sides with
  `pw.py local screen` for every candidate before credits; also screen against build
  `2898e485-1`. Local evidence is not field evidence.
- iteration 1: range clamp, spawn-HP thresholds, support pickups, disarmed following,
  each in a separate source commit/build with activation tracing. VERDICT-1 permits stacking
  locally passing changes into one uploaded bundle and one hosted A/B.
- allowed_changes: any single attributable change to the strategy source or a skill, including
  targeting/range, grenade use, pickups, movement/routing, thresholds and constants, roles. A
  new win strategy or comms protocol needs an orchestrator PROCEED first.
- credit_budget: 300 credits per iteration, 1,000 per day (budget 0.5 credits per episode).
- max_iterations: 20. Stop rules in the loop skill mean "report to the orchestrator and wait
  for PROCEED", not "stop working".

## Identity, roster and budget

James Botts was verified active immediately before upload. Confirm again for future uploads.
Eight copies of our policy face eight copies of one pinned real opponent, matching this league.
No hosted self-play. Budget 0.5 credits per episode and ledger estimates from request previews;
the ordinary player session gets 403 from the credit endpoint. Task 0 spent zero XP credits.
Heartland memberships and the orchestrator's stopgap are outside this optimizer's scope.
