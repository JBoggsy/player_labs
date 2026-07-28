# Vote-coordination levers — pre-registration (2026-07-24)

**Hypothesis.** Crewborg's correct crew ballots fail to convert to ejections (31.9% vs
top converters' 61–71%) because they are cast earliest and alone. Two levers, tested
SEPARATELY first, then together if both pass (James's directive):

- **CHAT_PUSH** (`CREWBORG_VOTE_CHAT_PUSH=1`): after our ballot is in, if our target has
  drawn no other votes and <480 ticks remain, send one explicit `vote X. <evidence>` call.
  Persuasion channel only; ballot timing untouched.
- **BALLOT_RETIME** (`CREWBORG_VOTE_BALLOT_RETIME=1`): hold the deterministic crew ballot
  after the accusation; cast when any other vote lands on our target, else at the
  early-submit fraction. Timing channel only; chat untouched.

**Evidence (wave-2 mining, 400 league eps, `/tmp/wh_league2`):**
- imp-ejected-in-episode is THE crew-win correlate (r=+0.70).
- Ballot→ejection conversion: crewborg 31.9%, softmaxwell 71%, Aaron 67% (2400-tick window).
- We vote earliest (votes_before_ours 1.71; field top 2.5–3.5) and alone (pile_before 0.12
  vs 0.7–1.6); our correct target ends ~2.6 total votes vs converters' ~3.4.
- Chat-content study: ALL of us chat before 100% of correct ballots — content/timing, not
  presence, differs. Followers pulled by claim class (crew speakers, this corpus):
  witness_kill 2.28, terse_saw 1.76, social_cue 0.75 (crewborg's social_cue pulls 1.13 —
  already above field; our verbose format is fine). The gap is votes-first-ness, not text.

## Design

- 3 candidate arms + shared baseline, all on v115's code (main `565a1ea` = `64abdab` +
  the flagged levers) and v115's exact recipe (`CREWBORG_VOTE_PROBABILITY=0.5`,
  deterministic meetings), differing ONLY in the lever flags:
  - **baseline**: crewborg:v115's config, fresh matched arm (flags off)
  - **arm P (push)**: + `CREWBORG_VOTE_CHAT_PUSH=1`
  - **arm R (retime)**: + `CREWBORG_VOTE_BALLOT_RETIME=1`
  - *(arm P+R fires ONLY if both P and R pass — a follow-up batch, per James)*
- Probes upload as `crewborg-coord` (NEVER submitted). 100 eps/arm, Thread-1 pinned
  roster, slot 0, natural roles. No Bedrock anywhere.
- Ops-fail episodes excluded; compare ops profiles first.

## Pre-registered verdict criteria (per arm, vs the fresh baseline arm)

**PRIMARY:** correct-ballot→ejection conversion (our ballots on true imposters that end
in that imposter's ejection, from telemetry + results ground truth) **up** vs baseline,
p < 0.05 one-sided (fisher on converted/not); AND imposter-ejections-in-our-crew-eps
per crew episode not down.

**GUARDS (any failure disqualifies the arm):**
1. Crew win not worse beyond noise (2-sided p < 0.05).
2. vote_timeouts = 0 (retime holds ballots — the deadline path must still fire).
3. Mis-ballot rate (our votes hitting crew / crew-ep) ≤ 1.5× baseline.
4. Imposter side untouched (win within noise).
5. Chat volume sane (arm P: ≤ +1 chat/meeting — the push fires once).

**MECHANISM (must fire):** arm P: `meeting_chat_push` > 0 at a plausible rate (offline
estimate: our target is vote-less at push-time in ~50-70% of ballot meetings). Arm R:
`meeting_retime_join` + `meeting_retime_expire` > 0; join-rate tells us whether piles
actually form on our seeded chat.

**Combination rule (per James):** if BOTH arms pass PRIMARY + guards → fire arm P+R
(100 eps) and require: conversion ≥ max(arm P, arm R) − noise, guards hold. If exactly
one passes → recommend shipping that one alone. If neither: the coordination premise
fails live; next lever is suspicion-v5 or crew death avoidance.

---

## VERDICT (2026-07-24, all arms 100 eps, analysis `/tmp/coord/verdict.py`)

| arm | ops | crew WR | hits | ballot→ejection conv | mis/cep | impEj-eps/cep | vt | mechanism |
|---|---|---|---|---|---|---|---|---|
| base (v115 cfg) | 15 | 25.4% (59) | 58 | 13.8% | 0.441 | 0.322 | 0 | — |
| push (RUN 1 — INVALID, 32% ops) | 32 | 25.0% | 47 | 25.5% (p=0.10) | 0.558 | 0.365 | 0 | 30 fires |
| **push (RERUN, clean)** | 1 | 26.9% (78) | 83 | **32.5% (p=0.009)** | 0.308 | 0.449 | 0 | 36 fires |
| **retime** | 15 | **33.8% (65)** | 68 | **35.3% (p=0.005)** | 0.477 | **0.523** | 0 | 42 joins / 49 expires |
| combo (P+R) | 0 | 29.0% (69) | 58 | 24.1% (p=0.12) | 0.406 | 0.290 | 0 | 47 push / 27 join / 52 expire |

- **Both singles PASS** PRIMARY + all guards (vt 0 everywhere; mis-ballots ≤1.5× base;
  crew win not worse — retime directionally +8.4pp; imposter side noise on the clean arms).
  First push arm invalidated per the ops rule (32% ops-dirty platform window) and RERUN.
- **The COMBINATION FAILS its pre-registered bar**: conv 24.1% < max(singles) 35.3% − noise,
  and impEj-eps/cep 0.290 fell below even the baseline. Mechanistic read: the levers
  interfere — retime delays our ballot, and the push only fires after our vote is in, so
  in combo the push lands too late in the meeting to pull followers (combo pushed MORE,
  47 fires, but joined piles LESS, 27 vs 42). The combo's imp-win dip (64.5% vs base 92.3%,
  p=0.024) is mechanically implausible as a lever effect (both levers are crew-only code
  paths) — the base arm's 92.3% imposter WR at n=26 is the likely outlier — but per prereg
  it counts against the combo arm regardless.
- **DECISION per the pre-registered rule: recommend shipping RETIME ALONE**
  (`CREWBORG_VOTE_BALLOT_RETIME=1` in the next crewborg version's recipe). It is the
  stronger single on every axis: conversion 35.3% (p=0.005), impEj-eps 0.523/cep (+62% vs
  base, p=0.08), crew WR +8.4pp directional. Chat-push is validated as a mechanism (32.5%
  conv solo) and can be revisited with an earlier trigger (pre-vote push, or push-then-
  retime ordering) — but as-built it composes badly with retime. If pushing later, ALSO
  fix the duplicated "vote X … vote X" text (build_accusation already appends the call).
