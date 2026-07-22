# Pre-registered A/B: crewborg-survive:v1 (kill→WIN survival) — written BEFORE launch

> **VERDICT (2026-07-22, appended after the run): REFUTED — DO NOT SHIP.**
> See "Verdict" at the bottom. Headline: the "lies in wait" premise was a
> measurement artifact (meeting-freeze), the flee costs the second kill
> (guard 5 fail), and the meeting deflection fired decisively but didn't
> convert to survival or wins.

**Candidate:** `crewborg-survive:v1` (pv `82c4a42e-5940-4cc8-baf6-f9537dbf9e2b`) — main
(`d0d127c`, = v110's code) + commits `77bc648` (post-kill flee) and `3f8adc7`
(accused-response deflection + imposter first-mover). Upload recipe identical to v110
(LLM meetings recipe + `CREWBORG_HS_SECRET`), so vs the v110 baseline the ONLY delta is
the two survival levers. Design:
`crewrift_lab/docs/designs/2026-07-21-imposter-kill-to-win-design.md`.

**Arms (matched pinned roster — the Thread-1 seven current-champion labels — crewborg
slot 0, natural roles, div_acbde92a):**
- Candidate: 2×100 eps, fresh, paced (fired by this thread; total concurrent across all
  running xreqs kept ≤400).
- Baseline: the existing `/tmp/wh_anchor_base_v110` warehouse (200 v110 eps from Thread 1's
  `xreq_136dd84f` + `xreq_edd0f75e`, same roster/slot/division/recipe, same night) — reused,
  not re-fired. Thread-2's measured baselines on this data are the reference numbers below.

**Criteria (decided before any candidate episode is seen; imposter seats = crewborg
slot-0 seats with role=imposter; ops-dirty episodes dropped first, both arms):**

1. PRIMARY: **ejected-after-witnessed-kill rate DOWN** — of crewborg imposter seats with
   ≥1 witnessed kill, the fraction ejected by vote. Baseline 62.2% (v110-lineage).
   Pass = point estimate down; a drop to ≤ the ~45% midpoint toward the field's 31.6%
   counts as a clear pass, any rise fails.
2. Secondary: **post-kill 60-tick displacement UP** — median distance moved in the 60
   ticks after own kill. Baseline 4px; pass = field-like (≥20px).
3. Secondary: **imposter ejection rate (of seats) DOWN** — baseline 57.1% (v110 pinned arm).
4. Secondary: **imposter win rate UP** — baseline 53.6% (v110 pinned, n=56). The point of
   it all, but small-n noisy; directional evidence suffices if 1–3 move.
5. GUARD: **kills/seat not down** — baseline 1.61; fleeing must not cost the second kill
   (allow normal noise; a significant drop fails).
6. GUARD: **crew metrics untouched** — crew win rate (27% pooled baseline), crew
   no_vote_rate (~0), crew self-accusations 0 (the changes are imposter-only; the crew
   first-mover seam is untouched).
7. GUARD: **vote_timeouts flat** (~2/200 baseline) and **ops ~0** crewborg-side.
8. Mechanism checks (else the verdict is "no-fire", not "refuted"):
   - `domain.post_kill_flee` fires in candidate imposter telemetry (lever 1);
   - `domain.meeting_imposter_first_mover` and/or `meeting_decision path=counter_accuse`
     fire in candidate imposter meetings (lever 2).

**Attribution rule:** the levers are separable — lever 1 via the flee trace +
displacement metric, lever 2 via the meeting traces + speaks-first/accused-response
rates. If the primary passes but one lever demonstrably didn't fire or hurt its own
sub-metrics, ship the working lever alone.

**Ship rule:** primary + guards pass → SHIP RECOMMENDED (levers ship inside the next
crewborg version; the probe name is never submitted). Primary fails or a guard fails →
refutation recorded in TENTATIVE_LESSONS + version_log; no ship.

---

## Verdict (2026-07-22): REFUTED — DO NOT SHIP (both levers)

Cand: `xreq_9ec4f8bc` + `xreq_d998c7fb`, 200/200 eps completed, 0 ops-fail
(warehouse `/tmp/wh_survive_cand`). Baseline: v110-lineage pool = v110 100 eps
(`/tmp/wh_anchor_base_v110`) + anchor 200 eps (`/tmp/wh_anchor_cand`; identical
imposter code — the anchor change was crew-only). Same pinned roster/slot/night.
Analysis scripts: `/tmp/survive_ab/*.py`.

| # | Criterion | cand (survive) | base (v110-lineage) | prereg pass? |
|---|---|---|---|---|
| 1 | PRIMARY eject%-after-witnessed-kill DOWN | **53.5%** (23/43) | 51.6% (32/62) | **FAIL** (up, z=+0.19 p=0.85) |
| 2 | post-kill 60t displacement ≥20px | **3px** | 4px | **FAIL** (see artifact note) |
| 3 | imposter ejected% of seats DOWN | **49.1%** | 43.0% | FAIL (up, p=0.49) |
| 4 | imposter win% UP | **60.0%** | 63.3% | FAIL (down, p=0.70) |
| 5 | GUARD kills/seat not down | **1.38** | 1.81 | **FAIL** (p=0.065; 3+-kill seats 5.5% vs 21.5% p=0.010; 1st→2nd-kill conversion 43.1% vs 57.9%) |
| 6 | GUARD crew untouched | win 26.2% vs 27.6% (p=0.77), tasks 6.48 vs 6.32, self-accusations 0 | — | PASS |
| 7 | GUARD vote/no-vote + ops | no-vote-meetings 7.8% vs 10.6%; ops 0 vs 0 | — | PASS |
| 8 | Mechanisms fired | `post_kill_flee` 134 ev/50 eps (dest med 339px); `meeting_imposter_first_mover` 102/32 eps; `counter_accuse` 30/12 eps | — | PASS (so this is a real refutation, not a no-fire) |

**Why (the load-bearing findings):**

1. **The "lies in wait, 4px" premise was mostly a MEETING-FREEZE artifact.** Median
   kill→next-meeting latency is 77–91 ticks (crewborg AND field); at +60t most
   killers sit in `MeetingCall` phase where positions freeze. Conditional on the
   game still Playing at +60t, baseline v110 already moved **100px** (field 131px,
   cand 90px) — the old Evade was NOT standing on the body when play continued.
   Thread-2's 4-vs-23-40px table compared phase mixes, not behavior. (notsus also
   shows 4px unconditional — same artifact.)
2. **The flee costs the snowball (guard 5).** Kills/seat 1.81→1.38; 3+-kill seats
   21.5%→5.5% (p=0.01). Leaving the kill room for a ≥160px-away room forfeits the
   second kill that the old "stay near the crowd + witnesses-dropped-after-first-kill"
   pairing (hunt.py) was designed to bank. The 2026-06-26 Evade rewrite's logic
   stands re-confirmed.
3. **Lever 2 fired decisively but did not convert.** Spoke-first 0%→23.7% (z=8.7),
   spoke-in-meeting 35.6%→48.9% (p=0.004) — the seams work. But votes-received/
   meeting went UP (1.14→1.28), per-meeting ejection did not improve, and seat
   ejection/win did not move. Fabricated deflections from a seat already under
   heat appear to draw as much fire as they deflect in this field (consistent with
   the counter-accuse being read as heat-escalation, and with HS-veto opponents
   ignoring accusations against trusted members).

**Separability call:** lever 1 is harmful (guard fail) — reverted from any ship list.
Lever 2 is neutral-negative on outcomes despite a clean mechanism — not shippable on
this evidence; if retried, decouple from parity/bandwagon fabrication and test
counter-accuse-only with a real-evidence requirement.
