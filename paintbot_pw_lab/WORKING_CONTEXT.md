# Paintbot PW working context

## Current objective and boundary

Continue the authorized optimizer loop on submitted jb-pw-opt:v10, build7faadaa4-1,
UUID8c4947c7-0679-4826-a653-9de20c62ffa3, submission
sub_1616ba24-8791-47aa-9f13-51931d9a42db (orchestrator authorization).
I18 Richard confirmation: +.0981375,95%CI[+.0172507,+.1790243],200/arm;
xolod -.0062674,95%CI[-.0225313,+.0099966],48/arm. Finish remaining guards and
report any regression. Existing i19-i22 v8-control cohorts remain immutable.
I23 frontier pairs on v10 passed as a5c28ea4-1. Current i24 source rebases supported
focus attack independently onto v10. Both get fresh full-roster controls against v10.
I17 retreat eligibility regressed and is excluded from combinations.

No daily cap; balance floor10,000 and per-iteration approximately600 credits. Respect pending
request capacity and120s minimum polling. Every watcher exits on cohort completion.
No hosted self-play, league submissions, public posts or git pushes by the optimizer.

## Foundation qualification (v1 reference)

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
- baseline: submitted `jb-pw-opt:v10`, version `8c4947c7-0679-4826-a653-9de20c62ffa3`, build `7faadaa4-1`.
- candidate: i23 frontier pairs on v10, followed by i24 supported focus attack on v10.
- opponents: every top-8 leaderboard entrant except us, plus all explicitly named targets:
  Richard (primary, heavy), xolod (substantial guard), and small matched samples against
  finist, zhar, relh, basic-v22, daveey/Alpha, and Rohit. Refresh exact versions every iteration.
  Include frozen leaders for port detection; flag verified new activity in STATUS and increase
  their allocation in subsequent preregistered batches. Never use our policies as hosted opponents.
- local benchmark: upstream and own builds for runtime health, activation and mechanisms only.
  Local outcomes never rank, park or reject candidates. Every clean compiled candidate proceeds
  to hosted A/B against the real field.
- iteration 1: range clamp, spawn-HP thresholds, support pickups, disarmed following,
  each in a separate source commit/build with activation tracing. VERDICT-1 permits stacking
  locally passing changes into one uploaded bundle and one hosted A/B.
- allowed_changes: any single attributable change to the strategy source or a skill, including
  targeting/range, grenade use, pickups, movement/routing, thresholds and constants, roles. A
  new win strategy or comms protocol needs an orchestrator PROCEED first.
- credit_budget: no daily cap; keep the account balance above 10,000 credits (cap 20,000, refill
  ~1,429/day; unspent refill at the cap is lost). Up to ~600 credits per iteration.
- max_iterations: none (continuous; the orchestrator stops the loop). Stop rules in the loop skill mean "report to the orchestrator and wait
  for PROCEED", not "stop working".

## Identity, roster and budget

James Botts was verified active immediately before upload. Confirm again for future uploads.
Eight copies of our policy face eight copies of one pinned real opponent, matching this league.
No hosted self-play. Budget 0.5 credits per episode and ledger estimates from request previews;
the user-authenticated credits command now gives actual balance. Task 0 spent zero XP credits.
Heartland memberships and the orchestrator's stopgap are outside this optimizer's scope.

## Current pipeline source

Parent is submitted v10/build7faadaa4-1, UUID8c4947c7-0679-4826-a653-9de20c62ffa3.
I13–i16 completed inconclusively against Richard. V10 spray distance and v12 gun corridor
have positive point estimates; VERDICT-17 authorizes testing their combination without
requiring individual significance. I18 confirms v10 on Richard; remaining guards are pending. No optimizer league submission.

I17 v13/buildd68b2194-2 COMPLETE1192/1192: Richard−.063002,95%CI[−.116387,−.009617].
Regressed; exclude from combinations.596 creation previews, health coverage in REPORT-17.
I18 unchanged v10 independent confirmation: resized before admission to584games/292credits,
Richard200/arm, other opponents unchanged. Discovery plus confirmation440 estimated credits.
I19 v14/build482cacdc-1: structural teammate regroup/local retreat, original v8 eligibility.
Uploaded UUID3386f34a-2c42-43c3-b521-e06a37189540;136 regroup ticks,704 local retreat ticks,
3811 valid telemetry lines,0 failures. REPORT-18 ranks three structural hypotheses.
I20 v15/buildb9128d79-1: v10 spray distance plus v12 gun corridor on v8.
Uploaded UUID58ba5750-7d7c-4416-8785-6e62fe3721d5;both counters exercised,0 validation failures.
I19/i20 each584games/292credits, Richard200/arm, full roster; exact designs/manifests own IDs.
New uploads passed G1–G5. No local performance conclusions or performance vetoes.

## Current operating limit

No daily cap. Keep balance above10000; approximately600 per iteration. Live credits command:
`uv run python .claude/skills/coworld-experience-requests/scripts/experience_request.py credits`.
Latest admission snapshot18442.10002, cap20000, refill1428.57143/day. Record snapshots and account
net movements separately from previews; concurrent work/refills prevent per-cohort attribution.
Admission conservatively reserves full previews for every incomplete queued design plus
the floor; completed cohorts are excluded from that future reserve. Shared round-robin admission avoids waiting for another cohort's results.
At least120s between API polling/retries; every worker exits on admission completion or cohort
terminal status. Dashboard8810 stays stopped. New finite port check uses cached cohort metadata.
Round859 opponent identities unchanged. Source release0.3.123/28030de6; project CLIcoworld0.1.57
and softmax-cli0.26.38 match current releases. Clone main fetched/current; lab branch ahead
contains authorized local experiments. No changes to the main metta checkout.

No iteration limit: max_iterations is none (continuous). Keep building structural siblings
and queuing hosted cohorts while earlier cohorts run. A supported result is a submission
candidate for orchestrator.

I21 four frontier pairs passed as8e26035f-1 and uploaded v16, UUID969f9847-8e01-4c3a-a128-b49a42093789.
Activation7575,3682 valid lines,0 failures. REPORT-21 owns hypothesis/risks.
I22 frozen source: supported focus attack on v8. Shared target choice and a priority250
approach/hold capability form one structural combat behavior; retreat, supply and active
capture guards remain. REPORT-22 records the narrow ranking-only falsification and risks.

I22 supported focus passed as9a90e9dc-1 and uploaded v17,
UUIDfa6dc4e1-638b-4571-bba2-24ea271ea6f2. Activation182 changed targets and351 supported-attack
ticks,4480 valid lines,0 failures. Both i21/i22 have frozen584game/292credit designs.
Current workers:admit_continuous.py and continuous_results_queue.py, driven by
active-cohorts.json. They admit round-robin under capacity and poll at least120s apart.
They exit after all registered admissions/results are terminal; restart when adding a cohort
if the finite worker has already exited. Old per-cohort pipeline scripts are inactive.
