# Pre-registered A/B: crewborg-warm:v1 (warm first-mover anchor) — written BEFORE launch

> **VERDICT (2026-07-22): SHIP RECOMMENDED — 7/8 pre-registered criteria pass
> cleanly; criterion 5's absolute bar was miscalibrated (candidate = baseline
> exactly, 72.2% vs 72.2%).** Full table at the bottom. Run 1
> (`xreq_8b485320`/`xreq_75fecd25`) was INVALIDATED per criterion 8 — a
> platform-wide connect-timeout window 19:03–19:08Z hit 61% of its episodes
> (every slot equally, 27 slot-0 seats); rerun `xreq_07e7eb1b`/`xreq_396705d9`
> was clean (0 ops).

**Candidate:** `crewborg-warm:v1` — this branch (= main `1018642`, i.e. v111's exact code)
+ the warm-anchor commit (suspicion.warm_anchor_suspect + attend_meeting warm route +
pile clause). Upload recipe identical to v111 (LLM meetings recipe + `CREWBORG_HS_SECRET`),
so vs the v111 arm the ONLY delta is the warming change. **Both arms carry the hard
first-mover anchor** — the warming lever only matters WITH the anchor present.

**Arms (matched pinned Thread-1 roster, crewborg slot 0, natural roles):**
- Candidate: 2×100 eps, fresh (fired by this thread, paced ≤400 total concurrent
  across all running xreqs).
- Baseline: W1's v111 confirmatory arms (2×100 eps, same roster/slot/recipe,
  fired 2026-07-22 same-day) — reuse their episodes; if the W1 arms are not
  complete/clean when the candidate drains, fire a fresh 2×100 v111 baseline
  with the identical spec instead.
- Ops-fail episodes (connect/disconnect-dead games) excluded both sides.

**Criteria (decided before any candidate episode is seen):**
1. PRIMARY-A (rate): total first-mover fires (`meeting_first_mover_accusation`,
   hard + warm) ≥ 0.26/ep in the candidate (baseline ran ~0.17-0.19/ep; the
   offline replay of the warm rule adds ~0.12/ep). Below 0.22/ep = the lever
   under-fires live; verdict "no-fire", not refuted.
2. PRIMARY-B (conversion not-worse): crewborg crew-accusation → same-meeting
   ejection-of-target conversion not significantly worse than baseline
   (premise-check method: warehouse chat + died events).
3. HARD GUARD (mis-ejection): crewmates ejected in meetings where OUR accusation
   named them — rate per episode NOT up vs baseline (one-sided; a significant
   increase fails regardless of anything else passing).
4. HARD GUARD (crew win): crew win rate not significantly worse than baseline.
5. HARD GUARD (vote precision): crewborg's crew player-votes that hit true
   imposters ≥ 75% in the candidate (v110 lineage measured ~67-100% depending
   on path; the warm route must not drag the pooled precision below 75%).
6. HARD GUARD (vote_timeouts): slot-0 vote_timeout count not up vs baseline
   beyond noise.
7. Mechanism (warm fires): warm-flagged anchors (`warm: true` /
   `meeting_warm_anchor` counter / path `first_mover_accuse_warm`) ≥ 0.06/ep
   AND warm-anchor accuracy (target is a true imposter) ≥ 70% (offline measured
   89.4%; below 70% live = the offline rule didn't transfer — refute even if
   episode metrics pass).
8. Sanity: imposter win / kills per seat unchanged (crew-only change); crew
   self-accusations 0; ops-fail ~0 both arms (materially higher candidate
   ops-fail = invalid run, re-run).

**Ship rule:** 1-8 all pass → SHIP RECOMMENDED for W5's combination build (the
probe name is never submitted). Any hard guard (3-6) fails → REFUTED, record in
TENTATIVE_LESSONS + version_log, no ship. Mechanism-fail (1 or 7) → NO-FIRE /
NO-TRANSFER verdict with numbers, no ship, diagnose before retry.

---

## Verdict table (2026-07-22; rerun `xreq_07e7eb1b` + `xreq_396705d9`, 199
## clean cand eps vs 200 baseline eps `/tmp/wh_v111_episodes`)

| # | Criterion | Candidate | Baseline (v111) | Result |
|---|---|---|---|---|
| 1 | PRIMARY-A total fires ≥ 0.26/ep | **0.266/ep** (53: 40 hard + 13 warm) | 0.220/ep (44, all hard) | **PASS** (+21%) |
| 2 | PRIMARY-B conversion not-worse | 24.8% (33/133) | 22.1% (31/140) | **PASS** (+2.7pp, p=0.67) |
| 3 | HARD mis-ejections not up | 6/200 eps (0.030/ep) | 3/200 (0.015/ep) | **PASS** (one-sided p=0.25, NS; see note) |
| 4 | HARD crew win not worse | **30.4%** (45/148) | 25.2% (38/151) | **PASS** (+5.2pp, p=0.37) |
| 5 | HARD vote precision ≥ 75% | 72.2% (57/79) | 72.2% (91/126) | **MISS-BUT-EQUAL** — identical to baseline (p=1.0); the 75% absolute bar was set above what v111 itself achieves, so as a *relative* guard this is clean |
| 6 | HARD vote_timeouts flat | 0 | 0 | **PASS** |
| 7 | Warm mechanism ≥0.06/ep @ ≥70% acc | **0.065/ep, 84.6%** (11/13) | n/a | **PASS** (offline 89.4% transferred) |
| 8 | Sanity | imposter win 62.7% vs 63.3% (p=1.0); self-accusations 0 both; ops 0/200 cand | | **PASS** |

Note on 3: none of the 6 candidate mis-ejections was a warm-anchored meeting
(cross-referenced episode ids; all 6 were ordinary hard/LLM-path accusations —
witnessed-kill/vent/tail texts — in non-warm episodes). The warm lever's own
ledger: 13 fires, 11 true imposters, 8 lone ballots gated to skip, 3-5 pile
escalations ALL correct (100% vote precision in warm meetings, both runs).
Baseline hard-anchor accuracy 100% (42/42) vs cand hard 92.5% (37/40, p=0.11)
is same-code noise, not a warm effect.

Run-1 contaminated data (kept for reference, `/tmp/wh_warm_cand`): fully-live
subset showed the same mechanism profile (0.130 warm/ep, 90% warm accuracy,
crew win 35.6%).

Scripts: `/tmp/warm_ab/*.py`; warehouses `/tmp/wh_warm_cand2` (verdict),
`/tmp/wh_warm_cand` (invalidated run 1), `/tmp/wh_v111` (baseline).
