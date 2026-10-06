# M3 communications qualification

Status: **M3 implementation and milestone acceptance complete, 2026-10-05.**
The hosted performance comparison is inconclusive; two strategy truth checks fail.
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
The full suite passes 443 tests after the lifecycle corrections. The M2 hosted recording still audits to 17 pass, nine
unmeasurable and zero failures.

Final local build `18e0aa1f-1` reuses every component and runtime unit byte-for-byte.
It passed all gates and 56 identical-play matches against the first M3 build. Its G5 sample
parsed 7,550 lines from 16 seats, with D/U not exercised. Sampled work peaked at 31,833 units
(instructions remained 21,185). All 43 artifact hashes match. Four full
recordings (seeds 1–2, both sides) plus two G5 tapes cover 48 candidate-seat recordings.
All 16,326 eligible teammate messages decoded; there were no capacity exclusions or
transport failures. All nine types were exercised somewhere in this set. The audit reports
18 pass, 38 unmeasurable and two failing checks. Enemy reports include 62/5,793 reports
of disguised teammates. Grenade claims fail in 61/82 measurable cases: 32 charges never started and 29 landed
elsewhere; 54 superseded warnings, five unfinished lifecycles and two landings beyond
episode end remain unmeasurable.
This is mechanism evidence, not field performance.

Qualification exposed an evaluator error: its deadline of release estimate plus three ticks
was not in the accepted landing check. The evaluator now follows the actual charge, including
continuous commands held while radar or mister effects prevent charging. Tests cover delayed
start/release, mid-charge warnings, cancellations, missing states, superseded warnings and the
final episode step. Landing claims require the matching recorded grenade blast, rather than
the projected target of a grenade still airborne at episode end. The 150 cm criterion is
unchanged. Actual warnings while disarmed
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

## Hosted results

All 64 requests completed on release 0.3.115 with the exact intended versions, sides and
seeds. All 64 replays hash-verify, and all 32 pairs have matching engine seeds. There are
no excluded games, unmatched pairs, load failures or policy-attributed operational failures.
Creation previews total 32 XP credits; actual credit charges were not available. The live
pre-upload doctor passed. Hosted CLI: coworld 0.1.56; softmax-cli 0.26.38. No engine or
policy changes were made during the fixed sample.

The [machine-readable evidence](2026-10-05-m3-qualification-data.json) retains all 64 request
and episode IDs, policy identities, seeds, result scores, replay final hashes, metadata/result
hashes, comparison statistics, audit summaries and the final evaluator hash. Full artifacts
are in `episode_data/m3-18e0aa1f-ab/`; the comparison is `ab.json` there.

| Metric | Baseline | M3 | Verdict |
| --- | ---: | ---: | --- |
| Score outcome, margin 600 | 0.797552 | 0.781094 | Inconclusive |
| Wins | 26/32 | 25/32 | Inconclusive |
| Operational failures | 0/32 | 0/32 | None observed |

The paired score difference is −0.016458 (unadjusted 95% paired t interval
[−0.229000, +0.196083]). Raw paired-t p = 0.875535; Wilcoxon p = 0.903146; BY-adjusted
p = 1.0. The fixed sample provides no evidence of improvement or regression, and does not
establish equivalence. Six pairs were candidate-only wins and seven baseline-only wins.
Side/opponent subgroups have 16 pairs each and remain descriptive. The computed SPRT was
ignored as preregistered; the sample was not extended.

All 256 candidate-seat logs pass G5: 416,062 lines, zero failures, peak 270 bytes per tick.
All nine message types appear somewhere in the hosted set. API 429 responses caused partial
downloads; paced retries recovered the original episodes without creating additional games.
The dashboard reads downloaded evidence to avoid competing for API requests.

The dense audit uses seed 1801 against both opponents on both sides: four verified episodes,
32 candidate seats, 84,762 living decision ticks. All runtime reconstructions pass, and
13,126/13,126 eligible teammate deliveries decode, with no capacity exclusions. All 61 audit
input hashes verify. It reports 17 passing checks, 36 unmeasurable, three not exercised and
two failing checks:

- Enemy truth: 87/5,661 reports describe a disguised teammate.
- Grenade truth: 80/94 measurable claims fail: 37 charges never start and 43 land elsewhere.
  Fifty superseded warnings remain unmeasurable.
- The three X checks are not exercised in this four-game subset, despite X appearing in the
  broader G5 logs. Receiver-state and causal checks remain unproven where their data is absent.

E heard tracks only steer looking when no fire target is present; a false E report does not
itself create a shooting target. G reports do steer receiver evasion, so an incorrect reported
location can direct movement around the wrong area.

The report is `analysis/strategy_audit/18e0aa1f-1-hosted-final/report.md`; local evidence is
`analysis/strategy_audit/18e0aa1f-1-local-final/`. The M2 hosted regression remains 17 pass,
nine unmeasurable and zero fail. The compiled policy is immutable at source commit
`18e0aa1f6501af95e2c98d5d62cdc1fff6fde9f8`; subsequent changes affect audit evaluation and
qualification/status documentation, not its BASIC or strategy behavior.

## Qualitative replay review

Reviewed three episodes per arm: a loss at the primary score floor, the median primary
outcome, and one largest absolute paired swing. Saturated score ties use deterministic
selection; these games illustrate mechanisms and do not replace the full comparison.

| Arm / selection | Episode request | Opponent, side, seed | Observation |
| --- | --- | --- | --- |
| Baseline / loss | `ereq_3995891b-b572-4712-9da3-bc1888f9b7af` | xolod, blue, 1802 | Eliminated at tick 3,135 despite owning all ten hearts at the end; one friendly grenade kill. |
| Baseline / median | `ereq_06445935-38a0-42fd-96b1-9699101b6938` | zhar, blue, 1806 | Heart-meter win at tick 3,103; seven enemy spray kills, two grenade self-kills and one friendly grenade kill. |
| Baseline / paired swing | `ereq_8995ffed-112e-4a7f-9066-958f78820b9d` | xolod, red, 1801 | Eliminated at tick 1,968 despite eight completed captures. |
| M3 / loss | `ereq_7a7a4ff7-61e7-46c5-89f5-d58e3c9c5856` | xolod, red, 1805 | Eliminated at tick 3,099; one grenade killed its thrower and two teammates at tick 3,009. |
| M3 / median | `ereq_1076ca69-c6d2-4405-8ff9-b94fe261772e` | zhar, red, 1803 | Heart-meter win at tick 3,550 with one life remaining and all ten hearts owned. |
| M3 / paired swing | `ereq_0e068d7e-c1ae-41af-8adb-12cd933b8f7f` | xolod, red, 1801 | Heart-meter win at tick 3,136 with one life remaining; two grenade self-kills still occurred. |

The loss gives a direct message-to-outcome example. Seat 12 warned at decision 2,996;
seats 6, 8 and 10 decoded it at 2,997. It predicted 18 ticks until release. The actual throw
occurred at 2,999, and its recorded blast at 3,009 was 740 cm from the reported cell center.
The blast killed seats 8, 10 and 12. Thus delivery worked, including to both teammate victims,
but the warning described the wrong landing location. This does not prove whether a correct
warning would have saved them. The focused evidence is
`analysis/strategy_audit/18e0aa1f-1-loss-grenade/`.

The favorable paired example changes an elimination loss into a heart-meter win, but the
bundle changes several receiver behaviors and message traffic together (45 baseline shouts
versus 1,877 candidate shouts in that pair). In-range enemies also receive the sender's exact
position, so additional traffic changes information exposure. No individual message type
gets causal credit.
Friendly fire and self-kills also occur in the baseline. The sensible next edit-loop topic is
truthful grenade warnings, with the baseline retained as the competitive reference.

## Final acceptance and limits

M3's defined criteria are met: the codec and receiver components exist, G1–G5 pass, eligible
local decode coverage is 100%, and the fixed hosted A/B against unchanged M1 behavior is
complete. This is not a claim that all strategy checks pass or that communications improve
competitive performance. Failed claims, unmeasurable receiver effects, lack of authentication,
and the two-opponent/small-sample scope remain explicit.

The final suite passes 443 tests. Claude Opus 5.5 reviewed the plan, generated implementation
and audit corrections, and accepted the final evidence against the defined M3 criteria.
Source/print-event headroom is small (127,897/131,072 bytes and
63/64 events). Some generated cooldown memory shares per-unit scratch arrays; peer review
found no clobbering, but future regeneration must preserve those persistent cells.

M4 has not started. No league submission or Git publication was performed.
