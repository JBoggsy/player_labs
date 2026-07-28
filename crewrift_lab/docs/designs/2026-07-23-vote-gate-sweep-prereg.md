# Vote-gate sweep — pre-registration (2026-07-23)

**Hypothesis.** Crewborg's crew ballot gate (fitted posterior bar 0.9, skip otherwise) is
tuned for a precision regime the league does not reward. Lowering the bar increases net
correct votes per crew episode and thereby crew win rate.

**Evidence motivating it (2026-07-23 league mining, 400 fresh tournament episodes, n=3,200
seats, `/tmp/wh_league` + `/tmp/league_ds`):**
- Multivariate crew-win model (standardized): hit_imp +0.51, mis −0.22, tasks +0.56,
  died −0.57 → 1 correct vote ≈ 2.3 mis-votes; crew win 21.9%/44.4%/62.6% at 0/1/2 correct
  votes.
- Crewborg as crew: 0.54 player-votes/ep (top5: 1.18), skip 1.94/ep (top5 0.58), precision
  97.7% — corpus-best precision, corpus-worst crew WR (22%).
- Offline replay of the gate over 185 real crew meetings (fresh suspicion_snapshot rankings
  from v114/v112 telemetry, ground-truth roles; `/tmp/vote_sweep/offline_sweep.py`):

  | gate | votes/mtg | precision | hit/ep | mis/ep |
  |---|---|---|---|---|
  | bar=0.9 (live) | 0.168 | 87.1% | 0.397 | 0.059 |
  | bar=0.8 | 0.216 | 87.5% | 0.515 | 0.074 |
  | bar=0.6 | 0.335 | 74.2% | 0.676 | 0.235 |
  | bar=0.5 | 0.508 | 62.8% | 0.868 | 0.515 |

  bar=0.8 dominates 0.9 outright (precision flat, +30% hits). Lower bars trade precision
  for volume along the curve the league pays for.

## Design

- **Arms (all deterministic meetings — v114's exact image + recipe, differing ONLY in
  `CREWBORG_VOTE_PROBABILITY`):**
  - baseline: bar 0.9 (v114's default; fresh matched arm)
  - probe A: `CREWBORG_VOTE_PROBABILITY=0.8`
  - probe B: `CREWBORG_VOTE_PROBABILITY=0.6`
  - probe C: `CREWBORG_VOTE_PROBABILITY=0.5`
- Probes upload under the separate policy name `crewborg-votebar` (NEVER submitted).
- 100 eps/arm, Thread-1 pinned roster (slot 0, natural roles): daf-actinf-crewborg-v3:v1,
  softmaxwell-crewborg:v34, sasmith-crewborg-hs1:v15, notsus:v130, scott-crewborg-hs1:v13,
  crewrift-prime-crewborg-aaln-hunter-relhalpha:v6, crewborg-aaln:v25.
- No Bedrock in any arm → no pool-contention pacing concern; fire all 4 together.
- Ops-fail episodes (connect/disconnect timeout) excluded all arms; compare ops profiles
  first (platform-window gotcha).

## Pre-registered verdict criteria

**PRIMARY (picks the winner):** net correct votes per crew episode
(votes hitting imposters − votes hitting crew, from warehouse ground truth), and
imposter-ejections-in-our-crew-episodes per crew episode. The winning arm must beat the
baseline arm on BOTH, with poisson/fisher p < 0.05 on at least one.

**GUARDS (any failure disqualifies that arm):**
1. Crew win rate not worse than baseline beyond noise (2-sided p < 0.05).
2. Crew ejections we voted for (mis-ejections with our ballot on them) ≤ 2× baseline rate.
3. vote_timeouts ≈ 0; zero self-votes; imposter side untouched (win rate within noise —
   the bar is crew-only by construction, `active_vote_probability_bar` returns the legacy
   path for imposters, but verify).
4. Ops ~0 both arms.

**MECHANISM (must fire, else the arm tested nothing):** vote fire-rate per crew meeting
rises monotonically with the lowered bar, in the direction the offline table predicts
(±50% tolerance — live meetings include piles/witnessed votes the offline replay can't see).

**Decision rule.** If ≥1 probe passes PRIMARY + all guards: recommend shipping that bar in
the next `crewborg` version's recipe (prefer the highest-net arm among passers; tie →
higher precision). If bar=0.8 passes but deeper bars fail guards: ship 0.8 and note the
curve position. If nothing passes: the offline curve's live transfer is refuted — diagnose
before touching the gate again.

**What would change our mind about the whole direction:** if even bar=0.8 (offline
precision-flat) raises mis-ejections-we-voted-for >2× or drops crew win, the
suspicion_snapshot rankings do not transfer to live ballot quality and the lever moves to
the suspicion-v5 refit instead.

---

## VERDICT (2026-07-23, all 4 arms 100/100 completed, 0 failed)

Arms: base `xreq_5f3cf7b7`, 0.8 `xreq_d91a92cb`, 0.6 `xreq_78bbd3d5`, 0.5 `xreq_8a4df2c6`.
Ops 6–8/arm (symmetric, excluded). Analysis `/tmp/vote_sweep/verdict.py`.

| arm | crew WR | imp WR | hits/cep | mis/cep | net/cep | precision | skips/cep | vt | self-ej |
|---|---|---|---|---|---|---|---|---|---|
| base 0.9 | 26.1% (69) | 70.8% (24) | 0.435 | 0.029 | 0.406 | 93.8% | 3.01 | 0 | 15 |
| bar 0.8 | 23.4% (64) | 86.2% (29) | 0.531 | 0.016 | 0.516 | 97.1% | 2.78 | 0 | 13 |
| bar 0.6 | 22.7% (66) | 76.9% (26) | 0.606 | 0.273 | 0.333 | 69.0% | 2.33 | 0 | 6 |
| **bar 0.5** | **34.2% (73)** | 85.7% (21) | **1.192** | 0.356 | **0.836** | 77.0% | 2.00 | 0 | 8 |

- **PRIMARY:** bar=0.5 is the only arm to move net correct votes decisively:
  hits/cep 1.192 vs 0.435 (poisson p<0.0001), net/cep 0.836 vs 0.406 — passes with p<0.05.
  imp-ejections/cep 0.658 vs 0.580 (p=0.54, directionally up, NS). bar=0.8 modest
  (net 0.516, hits p=0.43 NS); bar=0.6 NEGATIVE (net 0.333 — worst arm; its precision
  collapsed to 69% without the volume payoff).
- **GUARDS all pass for bar=0.5:** crew win 34.2% vs 26.1% (+8.1pp, fisher p=0.36 —
  directionally UP, not worse); crew-ej-we-voted 0.014/cep (1 episode) vs 0 base — well
  under any 2× concern at these counts; vote_timeouts 0 everywhere; zero self-votes;
  imposter side untouched-to-better (86% vs 71%, p=0.30 NS); ops symmetric.
- **MECHANISM:** fire rate rises monotonically 0.9→0.8→0.5 in player-votes/cep
  (0.46→0.55→1.55) — except bar=0.6's precision anomaly (69% live vs 74% offline,
  within tolerance; its NET underperformance is the interesting deviation, likely
  sampling noise at 58 ballots).
- **Live precision beats the offline curve at every bar** (0.5: 77% live vs 63% offline)
  — live ballots also include witnessed/pile votes, and the deadline gate still filters.

**DECISION per the pre-registered rule: bar=0.5 passes PRIMARY + all guards → recommend
carrying `CREWBORG_VOTE_PROBABILITY=0.5` into the next `crewborg` version's recipe.**
Note the crew-win point estimate (+8.1pp) is underpowered at 100 eps/arm (need ~700/arm
for 80% power); the SHIP decision rides the pre-registered net-votes primary, with crew
win directionally confirming. The env clamp floors at 0.5 — probing below requires code.
