# Supported findings and remaining hypotheses

Current synthesis after i31, on rules 49 / 0.3.123–0.3.124. The orchestrator authorized one fresh v22/v10 comparison (i32), then standby;
these findings do not authorize other experiments. The orchestrator owns field monitoring.
Exact identities and champion lineage are in [WORKING_CONTEXT.md](WORKING_CONTEXT.md).
`REPORT-N` references below are local `tmp/collab/optimizer/REPORT-N.md` evidence.

## What the retained changes bought

- **Complete safe grenade charges before optimizing aim.** V3 preserves charge through
  target loss and blocks disarmed starts. Its field improvement versus v2 was directional,
  +0.0262 [-0.0151, +0.0675], not significant. It was retained under the earlier explicit
  operational gate. Local reductions in self/friendly grenade damage explain the mechanism,
  not proof of field superiority (REPORT-2).
- **Track geometry during a committed throw.** In 28 selected v3 losses, grenade enemy-HP
  deficit accounted for 399 HP while the overall damage deficit was 362 HP; median
  landing-to-aim error was 208 cm versus Richard's 51 cm. V6's live safe aim/charge updates
  improved Richard score +0.1976 [+0.0724, +0.3227] over v3 (REPORT-6). Selected losses
  locate a mechanism; the fresh A/B, not those conditioned counts, estimates the benefit.
- **Avoid undoing our own capture.** Own capture progress cleared idle eligibility and sent
  cover cogs back outside the ring. Keeping them in the ring eliminated the diagnosed
  cover-post reset pattern locally (263 to 0 in matched recordings), and v8 beat v6 against
  Richard by +0.1331 [+0.0099, +0.2562] (REPORT-10). More total captures alone is misleading
  when match duration differs; use fixed-time ownership and explicit reset causes.
- **Use geometry for weapon reach, ranking cost for target choice.** HP-weighted contact
  cost incorrectly suppressed in-range spray. V10 changes the two spray distance gates only.
  Its independent confirmation gained +0.0981 [+0.0173, +0.1790] against Richard over v8;
  xolod was inconclusive (REPORT-18). Do not generalize this success to every decision that
  uses the same ranking cost: resupply/retreat have different tradeoffs.

## Dead levers for this campaign, with limits

“Dead” means no supported reason to replace v10 from these studies, not proof that every
implementation or future opponent would fail. Intervals are nominal, generally normal
approximations; many candidates/opponents were examined.

| Lever | Supported conclusion |
| --- | --- |
| Wider gun teammate corridor, 95 to 195 cm | Local ordinary-gun friendly damage fell, but hosted gains were inconclusive on v3 (+0.0072 [-0.0053, +0.0197], REPORT-3) and v8 versus Richard (+0.0079 [-0.1177, +0.1335], REPORT-16). Avoided damage trades against offense. |
| Spray teammate cone veto | Richard -0.0037 [-0.1233, +0.1159] on v8 (REPORT-15). Its nominal positive xolod secondary result is not an independently confirmed v10 improvement. |
| Early neutral-capture resupply deferral | No supported Richard gain in hosted i13. Earlier local-only parked route/resupply ideas were never field-refuted; current rules prohibit ranking candidates by local self-play. |
| Restrict retreat eligibility to nearby foes | Harmful against Richard: -0.0630 [-0.1164, -0.0096], 480/arm (REPORT-17). Distant contacts still carry useful retreat information under this policy. |
| Local regrouping, four frontier pairs, supported focus attack | Individual studies and v10 rebases did not demonstrate incremental benefit (REPORT-19,21–25). Do not convert loss-corpus correlations about teammate proximity into a causal prediction. |
| Spray plus wider gun corridor | Beat v8 +0.0945 [+0.0166, +0.1724] (REPORT-20), but control lacked v10 spray fix. This does not establish any added corridor gain over v10. |
| Direct capture staffing | Alone +0.0322 [-0.0380, +0.1024] vs Richard (REPORT-26); unsupported. With frontier pairs, v22 improved Richard +0.0599 [+0.0091, +0.1106] but regressed xolod -0.0132 [-0.0261, -0.0004] (REPORT-27). Conditional reserve, not champion. |
| Full-speed neutral approach | Xolod -0.0096 [-0.0230, +0.0038] despite about 4.9 s lower mean win duration (REPORT-28). Faster is not necessarily better rated margin. |
| Post-capture pursuit | Xolod +0.0039 [-0.0098, +0.0177], 200/arm (REPORT-29); no supported gain. Excluded from v26. |
| Nearby glory collection | Finist +0.0143 [+0.0054, +0.0232] in i30, but xolod +0.0015 [-0.0054, +0.0084] and Richard +0.1615 [-0.0063, +0.3294] remain inconclusive. Inactive-finist speed/award gain is not active-combat strength. |
| Robust frontier/direct-capture/glory bundle v26 | I31 did not reproduce a significant gain: xolod +0.000372 [-0.005255, +0.006000]; finist +0.003725 [-0.002304, +0.009754]; Richard +0.019763 [-0.051979, +0.091504]. Individual positives are not additive; rejected. |

## Margin ceiling and changing pairings

Current recorded league metric is margin scale **600**, not the retired scale-1000 Elo
metric. Score outcome is `clamp(0.5 + glory_margin/1200, 0, 1)`; +10 uncapped winning
glory changes it by 0.00833. Winner glory combines countdown and awards; losers/draws get
zero. A 520–0 win rates 0.9333. Glory above 600 is clamped for a zero-scoring opponent.
Thus raw mean glory and mean rated score need not move together (i28 directly observed this).

V10 wins essentially all sampled xolod games, leaving mainly time/award margin to improve.
Pursuit, glory detours and the larger bundle produced only tiny, uncertain xolod effects.
This supports diminishing returns for tested changes near the observed ~0.93 level;
it does not prove ~0.95 is a hard cap or rule out a new mechanism.

OpenSkill ordinal is `mu - 3*sigma`. New champion versions widen sigma to at least 6,
so small gains must justify a temporary rating cost. Source verification is metta
`bb174d5ffb`, `rankings/openskill.py` and `ladders/updater.py`; canonical explanation and
settings evidence are in [mechanics.md](docs/mechanics.md). Team matchmaking favours
rating neighbours (`elo_softmax`, temperature 100), so use observed pairing frequencies
for the immediate objective and broad field guards for robustness. Richard dominated the
v6 bracket; xolod/finist dominated later observed rounds. Neither mix is permanent. The latest handoff check, rounds 888–893, has Richard 4/7
and xolod 3/7; this clears the one-third Richard trigger for recommending a fresh v22 A/B,
not for submitting v22. Exact local evidence: `tmp/collab/optimizer/standby-pairing-mix.json`.

## Evidence and resumption rules

- Distinguish zero failed episodes, sampled healthy seats, and missing optional health
  artifacts. I31 had all 1,200 scores but only 16 candidate episodes with seat-status checks.
- Preserve fixed cohorts, fresh controls, both sides, exact policy/seat identities and one
  observation per game. Do not pool discovery and confirmation or stop on an attractive CI.
- Read actual replay actions before assigning weight to frozen leaders. Latest i31 scout:
  finist 0/3, zhar 0/6 and relh 0/4 active games; xolod 5/5 and Richard 2/2 active. These
  small dated samples are port-detection evidence, not permanent opponent properties.
- M3 comms, disguise handling and older route/resupply variants remain unproven, not queued.
  A uniform may be acquired by crossing its location; avoiding pickup targets alone cannot
  prevent it. Use current source/trace evidence before reviving these hypotheses.
- On an orchestrator wake-up, verify release and recent pairings before choosing a parent.
  V22 merits a fresh comparison if Richard's share grows materially; no old reserve result
  authorizes submission. No agent watch/polling continues during standby.
