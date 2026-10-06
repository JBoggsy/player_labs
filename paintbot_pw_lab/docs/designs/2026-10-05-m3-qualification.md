# M3 communications qualification

Status: implementation and local gates pass; hosted artifacts and final audit are being qualified.
This is the acceptance record for [comms v1](../../strategy/comms.md), under the
[strategy compilation design](2026-09-30-strategy-compilation.md).

## Scope and decisions

Implement nine messages and their receiver effects without retuning the baseline motor,
roles, rule priorities or old HP thresholds. James chose lightweight scrambling, compact
batch telemetry under 512 bytes/64 print events, corroboration before targeting a
teammate-labeled body, and event-based G5 coverage. A rare type is explicitly not exercised;
it is never a semantic pass. The checksum does not authenticate a speaker.

Claude Opus 5.5 reviewed the plan, interfaces, generated units and audit design through the
agent-collab workflow. Inputs are committed before compilation; builds remain immutable.
Uploads and hosted tests are authorized. League entry and Git publication are out of scope.

## Local evidence

The compact-print foundation build, `3d0f8a4f-1`, preserves all 23 baseline component units.
It passed G1–G5 and 56 identical-play matches. This isolates runtime printing changes from
the new communication behavior.

The first M3 build, `c03010be-1`, passed all gates after one repair: its initial 567 globals
exceeded BASIC's 512 limit. The compiler moved temporary values into per-unit arrays.
The resulting policy uses 354 globals, 2,324 array cells, 105 arrays and 127,897 bytes.
Sampled peaks are 21,185 instructions and 31,811 work units per tick. Static telemetry
is 434 bytes and 63 print events; source size and print events have little headroom.

G5 parsed 8,532 lines from 16 candidate-seat logs without failures. D and X were not
exercised. The semantic audit of those two short recordings decoded all 1,420 eligible
teammate deliveries, with no transport or runtime reconstruction failures. It reported
16 passing checks, 35 unmeasurable, six not exercised, and one failing check.

The failure is the grenade landing claim. Two warnings were 530 and 929 cm from the eventual
landing. Replay states show charging stopped after 2 and 8 ticks, before the intended range,
and aim changed at release. The packets accurately described the charge target when sent;
they did not predict the actual early release. The 150 cm truth check remains failed.
No check was weakened and no baseline firing mechanic was changed to hide this finding.

The tooling refinements preserve current authored skills in compiler context, use byte-based
inbox reconstruction, and bind baseline predicates to their source dependency closure.
The full suite passes 441 tests after the lifecycle corrections. The M2 hosted recording still audits to 17 pass, nine
unmeasurable and zero failures.

Final local build `18e0aa1f-1` reuses every component and runtime unit byte-for-byte.
It passed all gates and 56 identical-play matches against the first M3 build. Its G5 sample
parsed 7,550 lines from 16 seats, with D/U not exercised. Sampled work peaked at 31,833 units
(instructions remained 21,185). All 43 artifact hashes match. Four full
recordings (seeds 1–2, both sides) plus two G5 tapes cover 48 candidate-seat recordings.
All 16,326 eligible teammate messages decoded; there were no capacity exclusions or
transport failures. All nine types were exercised somewhere in this set. The audit reports
18 pass, 38 unmeasurable and two failing checks. Enemy reports include 62/5,793 reports
of disguised teammates. Grenade claims fail in 62/84 measurable cases: 32 charges never started and 30 landed
elsewhere; 54 superseded warnings and five unfinished lifecycles remain unmeasurable.
This is mechanism evidence, not field performance.

Qualification exposed an evaluator error: its deadline of release estimate plus three ticks
was not in the accepted landing check. The evaluator now follows the actual charge, including
continuous commands held while radar or mister effects prevent charging. Tests cover delayed
start/release, mid-charge warnings, cancellations, missing states, superseded warnings and the
final episode step. The 150 cm landing criterion is unchanged. Actual warnings while disarmed
and early releases remain policy findings; the uploaded policy was not changed during testing.


## Hosted plan, recorded before creation

- Baseline: `jb-pw-strategy-m2:v1`, immutable version
  `e7cf2caf-3d02-4368-9dcd-2b75b429d15f`, build `567feb38-1`.
- Candidate: `jb-pw-strategy-m3:v1`, immutable version
  `7361ffff-f0d4-4c59-925b-6706331b59d4`, build `18e0aa1f-1`, SHA256
  `07ae328d1b12f57b0f61151e601e4c95c14e71cd516d9df6334e45c4eda87f04`.
  The upload receipt is in `strategy/compiled/uploads.jsonl`.
- Engine: `coworld-v0.3.115`, commit `244dc62b`, rules49,
  coworld `cow_7109be6e-ad0c-4088-991d-060057a33c4e`, variant `1v1`.
- Fixed sample: 64 episodes, 32 matched pairs. Two opponents, seeds 1801–1808, both sides,
  both arms. One episode per request; all eight seats on each team use one pinned version.
- Opponents: `zhar:v55` (`add4ec17-b3ac-43d7-9cce-38f80736455f`) and
  `xolod:v13` (`3e6edc9d-cbcb-482d-aff0-96a94dfd398d`), ranks 1 and 3 in round 684.
  This covers strong opponents only, not the whole field.
- Private requests, alternating which arm is created first within matched pairs, in one
  window. No hosted self-play. A private-consent rejection does not authorize a public run.
- Primary: `score_outcome` with explicit `--margin-scale 600`; secondary:
  `win_rate,ops_fail_rate`. The live league was rechecked: OpenSkill, mean scoring, scale 600.
- Decision: the existing paired test with Wilcoxon agreement and BY correction on primary/all.
  Ignore the computed SPRT for stopping. No optional stopping or sample expansion.
  Side/opponent groups have only 16 pairs and are descriptive/inconclusive.
- This is a small study for anything except a large effect. Inconclusive does not mean
  equivalent, safe, or unchanged. The treatment is the whole M3 bundle, not messages alone.
- Policy-attributed failures follow the comparison tool's forfeit contract. Report
  infrastructure failures, missing pairs and exclusions. Never silently remove policy failures
  or mix exploratory/historical games into either arm.
- Estimate: 32 XP credits at the earlier 0.5-credit episode estimate; retain actual creation
  previews. Ordinary credit lookup returned 403; no elevated access was used.
  Oracle use by the opponent is unknown; retain ordinary platform defaults in both arms.
- Stream artifacts as requests start. Reuse the terrain cache; trace only the chosen audit
  subset densely. Review two or three games per arm, including a large loss, a typical game,
  and the largest paired swing.
- Require near-100% eligible local decode coverage (target at least 99%), while also reporting
  the strict per-message Result check, which fails any eligible miss. Report capacity
  exclusions, missing logs, unexercised types, false claims and unmeasurable checks separately.

Analysis command:

```bash
uv run python paintbot_pw_lab/tools/pw.py compare compare ROOT/episodes \
  --design paired --baseline BASELINE_UUID --candidate CANDIDATE_UUID \
  --target score_outcome --margin-scale 600 \
  --metrics score_outcome,win_rate,ops_fail_rate \
  --requests ROOT/requests/manifest.json --out ROOT/ab.json --json
```

## Final acceptance

Pending: final immutable build identity, full local evidence, upload receipt, request IDs,
hosted operational/semantic evidence, fixed-sample comparison and qualitative findings.
