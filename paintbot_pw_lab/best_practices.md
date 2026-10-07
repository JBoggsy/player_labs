# Paintbot PW best practices

Use the [shared practices](../best_practices.md) for experiment design, provenance,
authorization and iteration speed. These constraints are specific to Paintbot PW and were
measured on rules 49, engine 0.3.123–0.3.124, against the 2026-10-06/07 league field.
Campaign evidence (reports, verdicts, request manifests and result JSON) is archived
outside git at `~/coding/personal_labs/paintbot_pw_archives/2026-10-07-optimizer-campaign.tar.zst`;
`REPORT-N` below refers to files in that archive.

## Release and runtime

- Run `pw.py deployed-ref` before any other work and diff the rule-bearing files of every new
  release. 0.3.123 replaced the BASIC runtime with Bassy (fixed-point `/`, integer `\`,
  comparisons return −1, host arguments must be exact int32) and disabled every seat of every
  unported policy. For several hours most of the league, including three of the top four, fired
  no shots; porting first was worth more than any tuning. Not every release matters: 0.3.124
  changed training-map infrastructure only.
- Policy changes go through `strategy/STRATEGY.md` (or a skill's authored `skill.bas`) and
  `pw.py strategy compile`. Compiler-owned runtime templates are infrastructure and may be
  ported; compiled builds and `reference/` policies are never hand-edited.
- Keep the exact-geometry map guard in every build that uses map-specific heart indices, so an
  unknown map falls back to default behavior. BASIC has no map identity; an unseen map that
  matches every checked field is indistinguishable.

## What the ladder rewards

- The rated outcome is `clamp(0.5 + glory_margin / 1200, 0, 1)` (OpenSkill, margin scale 600).
  Only the winner scores glory (about 600 − seconds + awards), so a 520–0 win rates 0.933.
  Raw mean glory and rated score can move in opposite directions; measure `score_outcome`.
- MMR is the per-player ordinal `mu − 3·sigma`. A new champion version widens sigma to at least
  6.0, which costs up to about 3 × (6 − sigma) displayed MMR until rounds accumulate. Submit only
  clear improvements and batch small ones.
- Matchmaking is `elo_softmax` (temperature 100): we play rating neighbours, and the mix shifts
  as ranks move (Richard dominated our games at rank 5; xolod and finist at rank 1; Richard again
  when he climbed to rank 2). Read our recent league pairings before choosing the objective and
  weight the decision metric by the observed mix. Source: metta `bb174d5ffb`,
  `ladders/rankings/openskill.py` and `ladders/updater.py:416-425`; details in
  [mechanics.md](docs/mechanics.md).
- Against xolod we win essentially every game at about 0.93; pursuit, glory detours and faster
  approaches each moved that by ≤ 0.004. Margin there is near its practical ceiling.

## Evaluation design

- Seat our policy on all 8 seats of one team and pin all 8 opponent seats to one real policy.
  Self-play and local screens only check that a build runs and that a behavior activates.
- Size arms per opponent from observed variance: against Richard the 95% interval half-width is
  about ±0.12 at 96 games per arm and about ±0.055 at 400; against xolod it is about ±0.01 at
  100 games per arm. Use about 400 Richard and 100–300 xolod games per arm; one-knob changes
  with true effects of a few hundredths are invisible at 96 per arm.
- Evaluate against the whole top of the field (every top-8 entrant) with small guard samples for
  the rest. Read replay actions before weighting a leader: on 0.3.123/0.3.124 finist, zhar and
  relh only move during the first ~12 ticks and never fire. Guard samples double as port
  detection.
- Report each opponent separately. Changes trade off between opponents: the coordinated central
  opening (v27) cost −0.181 against Richard and gained +0.043 against xolod.

## Changes that bought performance (champion lineage)

| Version | Change | Hosted evidence |
| --- | --- | --- |
| v3 | Real gun range, 10-HP supply thresholds, never abandon a grenade charge (local self-damage 188 → 6 HP) | 72/72 wins vs the active field; vs v2 +0.026, not significant |
| v6 | Track target geometry during a committed throw (landing-to-aim error was 208 cm vs Richard's 51 cm) | Richard +0.198 [+0.072, +0.323] over v3 |
| v8 | Cover cogs stay inside a capture they started (diagnosed reset pattern 263 → 0) | Richard +0.133 [+0.010, +0.256] over v6 |
| v10 | Physical distance, not HP-weighted ranking cost, gates spray | Richard +0.098 [+0.017, +0.179] over v8, replicated |
| v29 | Opponent-adaptive opening: v10 play by default; switch to the coordinated opening when xolod's capture route is seen at 15 s (95% held-out classification) | Richard +0.030 [−0.023, +0.084], xolod +0.020 [+0.012, +0.028] over v10 |

Mechanism evidence from selected losses locates a problem; the fresh matched A/B, not the
conditioned counts, estimates the benefit.

## Refuted or unsupported levers

"Refuted" means no supported reason to replace the parent from these studies, not that every
implementation would fail. Reopen one only with new evidence for a different mechanism.

| Lever | Result |
| --- | --- |
| Refuse the first central fight, counter on enemy splits (v34) | Richard −0.067 [−0.124, −0.011], 400/arm: hands Richard a lasting lead |
| Restrict retreat to nearby foes | Richard −0.063 [−0.116, −0.010] |
| Fixed coordinated central opening for all opponents (v27) | Richard −0.181; keep only as the xolod branch of v29 |
| Wider gun teammate corridor (95 → 195 cm) | Fewer friendly hits locally; hosted ±0.01, not significant |
| Spray teammate-cone veto; teammate-aware dodge; terrain-aware combat movement | Each within ±0.04 against Richard, not significant |
| Regrouping, frontier pairs, supported focus attack, direct capture staffing | Individually not significant; frontier + capture (v22) +0.060 Richard but −0.013 xolod; on a 57/43 pairing mix +0.014 [−0.016, +0.043] |
| Full-speed neutral approach; post-capture pursuit; nearby glory-heart collection | Xolod effects ≤ 0.004; faster wins did not raise the rated margin |
| Bundle of individually positive, non-significant changes (v26) | No significant gain anywhere; noisy positives do not add |
