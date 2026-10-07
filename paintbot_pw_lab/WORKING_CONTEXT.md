# Paintbot PW working context

## Current objective and boundary

VERDICT-30 supersedes continuous candidate pipelining. Build one robust bundle on v10:
exact v22 frontier pairs/direct capture plus exact v25 glory-heart detours. Pursuit v24 is
excluded: i29 was640/664 at source freeze, so its final xolod result was unavailable.
I30 complete664/664 with0failures: xolod+.0015375[-.0053516,+.0084266], finist+.0143403
[+.0054313,+.0232492], Richard+.1615278[-.0062956,+.3293512]. Richard remains inconclusive.

I31 tests the robust bundle against fresh v10 controls:300xolod,100finist,200Richard per arm,
1200games/600estimatedcredits. Recommendation requires xolod lower95%CI>=-.005 AND a
positive lower95%CI on finist or Richard. Complete fixed cohort and no operational failures.
Do not submit; print SUBMIT CANDIDATE for the orchestrator only when this gate passes.
After the bundle decision, enter watch mode: one cohort at a time, no new candidates unless
the field changes. About every2h check engine doctor, leaders and recent public rounds for
new opponent versions or resumed top-four activity. A change triggers a v10 evaluation,
STATUS update and NEED ORCHESTRATOR. Watch does not authorize league or public writes.

Uploaded bundle jb-pw-opt:v26 UUID4faf6330-9863-4b8e-b761-be4f65c2fa64, build c11410ab-1.
See tmp/collab/optimizer/REPORT-31.md and frozen optimizer-i31/requests/manifest.json.
Watch worker field_watch.py waits for the fixed decision, then checks every2h; its PID,
watch-state.json and logs live beside REPORT-31. It never builds or submits a policy.

## Loop charter

- objective: evaluate the robust bundle for xolod non-regression and significant finist or Richard improvement, then watch the field.
- policy_file: paintbot_pw_lab/strategy/STRATEGY.md
- policy_name / player: jb-pw-opt on James Botts, ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce.
- baseline: jb-pw-opt:v10, UUID8c4947c7-0679-4826-a653-9de20c62ffa3, build7faadaa4-1.
- opponents: current bundle xolod:v14 primary300/arm, finist:v2 secondary100/arm, co-gas-paintbot-bassy-richard:v1 secondary200/arm. Watch mode surveys the whole leaderboard and top-four activity; evaluate v10 against changed opponents.
- allowed_changes: the VERDICT-30 robust bundle, preserving source components and activation tracing. Afterwards no new candidates unless the field changes; report the change to the orchestrator.
- credit_budget: no daily cap; keep actual account balance above10000, approximately600credits per iteration.
- max_iterations: one remaining robust bundle, then watch mode under VERDICT-30.
- submission_gate: xolod lower95%CI>=-.005 and finist or Richard lower95%CI>0, full fixed cohort and no operational failures. Only recommend; orchestrator submits.

## Current environment and operating rules

Freshness check found teams release0.3.124/7a29ed7a; release pin and tools updated.
Diff from0.3.123/28030de6 adds training-map registration, without hosted rules/BASIC changes.
Historical results retain their original game version; new cohorts use fresh v10 controls on0.3.124.
Project coworld0.1.57 and softmax-cli0.26.38 match current PyPI releases. Source clone
fast-forwarded to7a29ed7a; lab origin/main merged without conflicts, preserving local work.
Latest credits15930.78275 before the robust bundle; previews and net account movements recorded
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
