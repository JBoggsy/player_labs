# Pre-meeting suspicion warming: a social-evidence anchor-eligibility rule (W2)

**Status:** implemented on this branch; to be A/B'd as `crewborg-warm:v1` (probe
upload, never submitted). Parent lever: the first-mover anchor
(`2026-07-21-first-mover-anchor-design.md`, SAFE-POSITIVE, shipped in v111) —
rate-limited at ~0.19/ep by how rarely `top_suspect()` clears the 0.9 fitted bar
at meeting start. This change adds a second, independently-measured eligibility
route so the anchor fires more often.

## The measurement first (2026-07-22, /tmp/warm_gap/*.py)

Corpora: 399 version-verified episodes with `CREWBORG_TRACE_SUSPICION_FEATURES=1`
— 199 v110 (`/tmp/hs_on_baseline_eps`) + 200 `crewborg-anchor:v1`
(`/tmp/wh_anchor_cand_episodes`); identical suspicion code and recipe. Unit of
analysis: the 791 crewmate `suspicion_snapshot` events (one per meeting start —
exactly the anchor decision point), joined to ground-truth imposter colors from
results.json (slot IS color).

1. **The live bar is 0.9.** The v110/v111 recipes set no
   `CREWBORG_VOTE_PROBABILITY`, so `WEIGHTS_VOTE_PROBABILITY` = default 0.9, no
   lead. (The `vote_bar: 0.8` in v110's own traces is a stale label — the
   snapshot reported the legacy constant; fixed on main in `b2cbefe`, not in
   v110's image. The briefing's "0.9 bar" was correct.)
2. **The fitted posterior is bimodal — the orchestrator's leading design
   (a softer 0.7+lead bar) is REFUTED.** All 71 currently-eligible anchors
   (p ≥ 0.9 + citable) are witnessed kill/vent catches (100%), saturated to
   p ≈ 1 by the definitional floor. Non-witnessed top-1 posteriors **max out at
   p = 0.74** (2 of 720 above 0.73). There is nothing in [0.74, 0.9) to unlock:
   a 0.65 bar adds 0.018/ep at 57% precision; 0.7 adds 0.008/ep at 67%. Below
   that, the p-bands are ~45% precise — coin flips. The graded evidence simply
   cannot push the fitted logit high enough without a witnessed event (max
   achievable non-witnessed logit ≈ +6.1 requires an absurd feature stack;
   observed play never approaches it).
3. **The warming headroom is real but lives in the SOCIAL features, not the
   posterior.** The true imposter is top-1-but-below-bar in 39.6% of crewmate
   meetings (top-2-below-bar in 64.2%) — base rate 43.5% among below-bar
   citable top-1s. An ML ceiling check (5-fold OOF logistic/GBM over all traced
   features) puts AUC at 0.80–0.82 with ~0.19/ep available at 90% precision —
   so high-precision warming IS learnable, but a fitted second model is the
   suspicion-v5 refit (out of scope). The interpretable rule that captures most
   of it, measured on the top-1 (by posterior) suspect at meeting start:

   | rule (all conditions ANDed on the top-1 suspect) | fires/ep | precision | split-half |
   |---|---|---|---|
   | tail_max_run ≥ 72 ticks + times_accused ≥ 1 + votes_cast ≥ 1 + clean³ | 0.143 | 84.2% | 88% / 79% |
   | **same with tail_max_run ≥ 96 ticks (shipped)** | **0.118** | **89.4%** | **92% / 86%** |

   clean³ = `button_calls_made == 0 AND reported_bodies == 0 AND
   tasks_completed_watched == 0` (the exculpatory social counters; buttons are
   the strongest single exonerator — 4.8% imposter rate among below-bar
   button-pressers). All counters are the caller-attribution / social-evidence
   features verified firing since v96.
4. **Expected effect: anchor rate 0.178 → ~0.30/ep (+66%), pooled anchored
   precision ≥95%.** Mis-anchor cost model: wrong warm anchors ≈ 0.013/ep ×
   21.7% wrong-target conversion ≈ 0.003 crew mis-ejections/ep added, vs
   ≈ 0.039 imposter ejections/ep added — a ~14:1 favorable trade on the
   Thread-3 premise numbers.
5. Because `times_accused` and `votes_cast` need a *prior meeting* to be
   non-zero, warm anchors fire from **meeting 2 onward** by construction — the
   witnessed hard-bar route keeps covering meeting 1.

## The chat/vote coupling question (the risk fork, answered)

The existing anchor **couples chat and vote**: it sets `_tentative_vote`, and at
the hard bar the target passes `_vote_target_corroborated` by construction
(`top_suspect == target`), so the early-submit/deadline vote lands on the
accused. Naively reusing that coupling at a soft eligibility rule would fire
~89%-precise VOTES — below the hard bar's 97–100% and a direct parity gift on
every miss.

It turns out the v88/v89 vote-gate machinery already decouples for free: a
warm-anchored target is *not* `top_suspect`, not witnessed, and not (yet)
LLM-submitted, so `_vote_target_corroborated` fails → the deadline vote is
converted to SKIP (and early-submit holds). We keep that, and add exactly one
escalation path:

> **Warm anchor = CHAT on the first meeting tick (evidence-cited, tentative vote
> set). The VOTE fires only if one of the existing corroborations arrives (the
> posterior rises to the hard bar, a witnessed catch, or the LLM itself
> `submit_vote`s the target) — or if the PILE actually forms:** at vote time, at
> least one *other* player has cast a vote against the warm target
> (`votes_against`) or accused them in chat (`chat_accusers`).

Rationale for the pile clause: the anchoring premise is that the first-named
target collects the pile; if others joined, our ballot is pivotal exactly when
it converts, and if nobody joined, a lone uncorroborated ballot converts almost
nothing while carrying the full mis-vote risk. The clause reuses the existing
`votes_against` + `chat_evidence.chat_accusers` helpers (the imposter bandwagon
heat signals) and is scoped to the warm-anchored target only — every other vote
path is byte-identical.

Note the accusation text still closes with ". vote <color>" while we may end up
voting skip (a mild behavioral tell in the no-pile case). Accepted: the
alternative (suppressing the vote call in warm accusations) would fork the
accusation format — the measured persuasion lever — for a corner case.

## The change (minimal)

- `strategy/suspicion.py` — new `warm_anchor_suspect(belief)`: returns the
  top-posterior non-self alive suspect iff they satisfy the social warm rule
  (constants `WARM_TAIL_MAX_RUN_TICKS = 96` etc. documented at the definition);
  `None` otherwise. Sits beside `top_suspect`/`chat_suspect` as a third,
  softer-still eligibility surface that is **never used to vote directly**.
- `modes/attend_meeting.py` — `_first_mover_accusation_intent` consults
  `top_suspect` first (unchanged hard path; vote coupled as before), then
  `warm_anchor_suspect` (env kill switch `CREWBORG_WARM_ANCHOR=0`, default on).
  A warm fire records `_warm_anchor_target`; `_vote_target_corroborated` gains
  the pile clause for exactly that target. Trace: the existing
  `meeting_first_mover_accusation` event carries `warm: bool`, plus a
  `meeting_warm_anchor` counter and `path="first_mover_accuse_warm"` in
  `meeting_decision`, so the A/B can split hard vs warm fires.
- Honor-Society vote veto, self-guard, dead-mute, imposter path, LLM-off path:
  all unchanged (the warm branch runs inside the same crew+alive+LLM-enabled
  guards as the hard anchor and requires `build_accusation` citable evidence —
  the ≥96-tick tail always cites).

## A/B (pre-registered: `2026-07-22-warm-anchor-ab-prereg.md`)

Candidate `crewborg-warm:v1` (this branch, v111 recipe + HS seed) vs an
anchor-bearing v111 baseline (W1's confirmatory arms — same pinned Thread-1
roster, slot 0, natural roles), ~200 eps/arm, paced ≤400 total concurrent.
PRIMARY: total first-mover fire rate up (~0.19 → ≥0.26/ep) with conversion
not-worse. HARD GUARDS: crew mis-ejections (after OUR accusation) not up, crew
win not down, our crew player-vote precision ≥75%, vote_timeouts flat.
Mechanism: warm fires ≥0.06/ep with ≥70% accuracy (measured floor 86%).
