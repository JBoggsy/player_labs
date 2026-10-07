# Paintbot PW working context

## Current objective and boundary

VERDICT-28 changes the objective to top-bracket margin against xolod:v14. Keep submitted
jb-pw-opt:v10, UUID8c4947c7-0679-4826-a653-9de20c62ffa3, build7faadaa4-1 as parent.
Orchestrator reports rounds871–876 paired us with xolod five times and finist twice, all wins.
V22 remains a Richard reserve, not submitted: Richard+.060 but xolod-.01323
95%CI[-.02610,-.00036]. V23 neutral rush rejected: xolod-.009583[-.022956,+.003789],
48/arm, both48wins. Mean win time130.341s baseline vs125.445s candidate; faster did not
improve score. Median129.438s vs127.083s. Old cohorts i19–i28 are complete.

I29/v24 post-capture pursuit is uploaded as UUIDfebf78e0-a9d8-4f62-995e-549c9f91e41d,
build6121c0a2-1. Its664-game cohort is queued;213pursuit ticks in6of32 targeted recordings.
I29 diagnosis and design are in tmp/collab/optimizer/REPORT-29.md. Eight selected v10-xolod
wins finish on the heart meter with2–5 enemies alive. All hearts are owned well before
completion. Investigate post-capture pursuit without changing earlier capture decisions.
I30/v25 is an independent v10 child for short visible glory-heart detours,
build66386cde-1, UUID98763b00-5e58-4957-917d-13f55244ca8e. Its664-game cohort is queued
while i29 runs.149actual detour ticks in8of32targeted recordings, no validation failures.
REPORT-30 records mechanism, visibility bounds and unknown opportunity rate.
No unsupported causal time-saving estimate or optimizer league submission.

## Loop charter

- objective: improve mean score_outcome against xolod:v14 at margin_scale600; secondary median win time and our glory. Finist is the secondary opponent, Richard the strength guard.
- policy_file: paintbot_pw_lab/strategy/STRATEGY.md
- policy_name / player: jb-pw-opt on James Botts, ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce.
- baseline: jb-pw-opt:v10, UUID8c4947c7-0679-4826-a653-9de20c62ffa3, build7faadaa4-1.
- opponents: xolod:v14 primary, at least200episodes/arm; finist:v2 secondary48/arm; co-gas-paintbot-bassy-richard:v1 guard48/arm; small matched guards against zhar:v55, relh-paintbot-pw:v56, paintbot-pw-basic-v22:v1, daveey-pw-league-smoke-l17c-s41u150-hc:v1, paintbot-heartwick-starter:v2. Refresh identities before admission; flag frozen leaders that resume acting.
- allowed_changes: one attributable strategy or authored skill change with activation tracing; compile committed inputs, never hand-edit generated BASIC. VERDICT-28 authorizes proposing and building the largest diagnosed time-saving change.
- credit_budget: no daily cap; keep actual account balance above10000, approximately600credits per iteration.
- max_iterations: none (continuous, stopped by orchestrator).
- submission_gate: xolod delta>=+.02 with95%CI lower bound>0; no finist regression (CI entirely below0 blocks); Richard point delta>=-.05. Report Richard CI explicitly: this guard is not proof of noninferiority. Other small guards remain regression sentinels. All fixed games complete, no episode failures or verified bad candidate seats. Only recommend; orchestrator submits.

## Current environment and operating rules

Freshness check found teams release0.3.124/7a29ed7a; release pin and tools updated.
Diff from0.3.123/28030de6 adds training-map registration, without hosted rules/BASIC changes.
Historical results retain their original game version; new cohorts use fresh v10 controls on0.3.124.
Project coworld0.1.57 and softmax-cli0.26.38 match current PyPI releases. Source clone
fast-forwarded to7a29ed7a; lab origin/main merged without conflicts, preserving local work.
Latest credits16393.82823 before new cohort; previews and net account movements recorded
separately because concurrent requests and refill prevent per-cohort spend attribution.

No hosted self-play: eight own seats against eight seats of one pinned real opponent.
Local runs measure runtime, activation and mechanisms only; never rank or reject candidates.
Canonical finite workers: tmp/collab/optimizer/admit_continuous.py and
continuous_results_queue.py, driven by active-cohorts.json. Poll/retry at least120s apart;
exit after all admissions/results terminal. Dashboard8810 stays stopped. Restart finite
workers when adding a cohort only if they have exited. No optimizer league submission,
public writing, git push or changes to the main metta checkout.

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
