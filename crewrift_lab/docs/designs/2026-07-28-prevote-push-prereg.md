# Pre-vote chat push during the retime hold — pre-registration (2026-07-28, loop-alpha L1)

**Registered BEFORE any arm fired.** Loop-1 of the improvement-loop alpha run
(`2026-07-28-improvement-loop-alpha.md`); evidence from the loop's step-1 batch
(4×100 matched xreqs vs the Thread-1 pinned roster, crewborg:v116 slot 0, natural
roles: `xreq_f42ce4c9`, `xreq_83cae9d4`, `xreq_fd660882`, `xreq_c48a86c2`;
warehouse `/tmp/loop1/wh`, 397 eps, belief log + divergence scan run).

## Hypothesis

**Crewborg's retime-expire ballots convert at ~0% because they are lone ballots cast
into an already-locked field, and the fix is to send the persuasion push DURING the
retime hold (pre-vote), not after the ballot.**

Mechanism, pinned: `modes/attend_meeting.py:_ballot_retime_intent` — the hold branch
returns a bare `idle` (no persuasion while holding), and
`_post_vote_chat_push_intent` (the validated push) fires only **after** our ballot is
confirmed — which on the retime path means at/after the early-submit cast, too late to
move anyone (the 2026-07-24 combo failure, now decomposed).

## Evidence (step-1 batch, crew meetings, `belief_meeting_vote_selected` reasons)

| ballot path | ballots | on-imposter | converted | conv \| imposter |
|---|---|---|---|---|
| `retime: joining pile on our target` | 125 | 113 | 60 | **53.1%** |
| `retime: no pile formed, casting` (expire) | 169 | 124 | 1 | **0.8%** |
| deadline/first-tick deterministic cast | 56 | 39 | 15 | 38.5% |

- Votes are **locked once cast** (no re-vote — `crewrift-gameplay.md` §Voting). Field
  ballots land at dt p10=251 / p50=312 / p75=988 from meeting start; our expire cast
  lands at median dt **601** (the 0.5 early-submit fraction) — by then a median 5.3
  other ballots are committed and only ~2.0 arrive later; just 31/169 expire meetings
  saw ANY later vote on our target.
- So 124 correct (on-imposter) ballots per ~400 eps take the near-worthless expire
  path — 52% of our on-imposter retime ballots.
- Chat-push as a mechanism is already validated solo (conv 32.5%, p=0.009,
  `2026-07-24-vote-coordination-prereg.md`) but as-built fires post-ballot; the combo
  A/B showed pushes landing too late when retime holds the ballot (47 fires, 27 joins).
- Hold-longer and switch-to-existing-pile were both checked and rejected: late votes
  on our target are rare (31/169), and the offline pile-switch sim nets only ~+4 imp
  ejections vs +2 mis-ejections per 294 crew eps at the best gate.

## The change (one lever)

New env flag **`CREWBORG_VOTE_CHAT_PUSH_PREVOTE`** (code default OFF). While
`_ballot_retime_intent` is holding the ballot (retime enabled, tentative non-skip
target, pile not yet formed): once the meeting has aged ≥ `PREVOTE_PUSH_DELAY_TICKS`
(240 — after our first-tick accusation has been read, before the field's median vote
at ~312) and the chat cooldown is ready, send ONE `vote <target>. <cues>` push, then
keep holding. Also fixes the duplicated-text defect: the push strips the accusation's
own trailing ". vote X" so the text reads `vote X. X sus: <cues>` (not
"…vote X … vote X").

Retime's join/expire/deadline logic is untouched; imposter path untouched; the push
fires at most once per meeting.

## Design

- **Probe:** `crewborg-coord:v5` (probe lineage — NEVER submitted) = v116's exact code
  (main `565a1ea`) + the new flag's implementation; recipe = v116's recipe
  (deterministic meetings, bar 0.5, chat evidence + floor, HS secret, full traces,
  `CREWBORG_VOTE_BALLOT_RETIME=1`) **+ `CREWBORG_VOTE_CHAT_PUSH_PREVOTE=1`**.
- **Cand arms:** 2×100 eps, Thread-1 pinned roster, slot 0, natural roles — fired
  sequentially (one drained before the next; ≤400 total concurrent with anything else).
- **Baseline:** the loop's step-1 batch (397 eps, same day, same roster/slot/recipe,
  v116) — re-used per the loop's matched-baseline discipline. Ops profiles compared
  first (step-1 ops ≈ 0; if the cand arms' ops profile differs materially — >10pp
  ops-dirty — fire a fresh 100-ep v116 baseline arm instead).
- Ops-fail episodes excluded at the GAME level both sides.

## Pre-registered verdict criteria

**PRIMARY (both must hold):**
1. Correct-ballot→ejection conversion (our on-imposter ballots whose target is ejected
   within 1400 ticks, measured identically both arms from the warehouse) **up** vs
   baseline's 27.5% — one-sided Fisher p < 0.05 on converted/not-converted.
2. Imposter-ejected-in-episode rate per crew episode **not down** (baseline 39.1%).

**MECHANISM (must fire):**
3. `meeting_chat_push_prevote` counter > 0 in ≥ 25% of retime-hold meetings whose
   target drew no early pile (offline expectation: most of the 169-per-400-eps expire
   meetings should see a push).
4. The join share of on-imposter retime ballots rises (baseline 113/237 = 47.7%) — the
   push exists to convert expires into joins.

**GUARDS (any failure disqualifies):**
5. Crew win rate not worse beyond noise (2-sided p < 0.05 vs baseline 28.9%).
6. Slot-0 vote_timeouts = 0 (the hold must still respect early-submit/deadline).
7. Mis-ballot rate (our ballots on true crew / crew-ep) ≤ 1.5× baseline (0.25/cep).
8. Imposter side untouched (win rate within noise, 2-sided p < 0.05 bar).
9. Chat volume sane: ≤ +1 chat per crew meeting vs baseline (the push is single-fire).

**Decision rule:** all PRIMARY + MECHANISM + GUARDS pass → build `crewborg:v117`
(= v116 recipe + `CREWBORG_VOTE_CHAT_PUSH_PREVOTE=1`), run the confirmatory A/B vs
v116 per the W5 pattern (fresh prereg for the combination gates BEFORE firing), then
STOP AND ASK James for submit approval with the full gate table. Any PRIMARY/GUARD
fail → NO-SHIP, close the lever in the version log, next loop. MECHANISM no-fire with
PRIMARY flat → implementation bug, one diagnose-and-refire allowed.

---

## VERDICT (2026-07-28, filled after the arms ran — see §below)

*(pending at registration)*
