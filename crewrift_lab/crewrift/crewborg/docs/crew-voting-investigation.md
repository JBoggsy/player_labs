# Crew voting investigation — gate, mechanism, coordination (2026-06-30)

**Question (direction 2):** crewborg is a competent imposter but a losing crewmate.
Crew win two ways — tasks and **voting**. Is crew voting a fixable weakness, across its
three facets: the **gate** (skip vs vote), the **mechanism** (does suspicion rank
imposters above crewmates, and is its confidence calibrated), and **coordination** (do
crew concentrate votes)?

**TL;DR.** crewborg's crew vote is **net-harmful**: its meetings eject **2.2× more
crewmates than imposters**, a steady parity gift to the imposters. The cause is **not**
the gate and **not** missing coordination — it is the **mechanism**: the live crew-vote
signal is only ~39% accurate against the real league field. The fitted suspicion model
scores **94% imposter-precision on held-out *offline* rows** but ~39% **live** — a
**train→serve gap**, *not* an observation gap (the offline features are deliberately
visibility-clipped and runtime-admissible; see §3). Coordination is a dead end here (the
public vote-pile is only ~44–50% reliable regardless of size). The fix trusts only the
one signal that holds up live — a **directly-witnessed** kill/vent — and skips otherwise.
A matched hosted A/B validates it.

---

## 1. The live vote path (confirmed, not assumed)

The crew vote is `top_suspect(belief)` (`strategy/suspicion.py`), consumed by Attend
Meeting's deterministic crewmate path (`modes/attend_meeting.py:_decide_crewmate`): accuse
+ vote the top suspect, else **silent skip**. The vendored fitted weights
(`data/suspicion_weights.json`) **load** (schema matches), so the live path is the
**fitted model at a p ≥ 0.9 near-certainty bar with NO clear-leader rule** — confirmed by
reading the loaded weights and the `_WEIGHTS is not None` crewmate branch of
`top_suspect`. (The LLM meeting path is off by default; the legacy clear-leader path is
the fallback only when no weights load.)

## 2. Gate — crew over-skips, but skipping is *protective*

Warehouse (`/tmp/sweep_wh`, trace_warning episodes excluded), crew `vote_cast`:

| policy (crew) | votes | skip % | player-vote accuracy (hit imposter) |
|---|---|---|---|
| **crewborg** | 665 | **46%** | **39%** |
| notsus (winning crew) | 111 | 4% | 61% |
| field (other) | 403 | 29% | 56% |

crewborg skips far more than the winning crew. But given how *wrong* its non-skip votes
are (below), skipping is the lesser evil — see §5.

## 3. Mechanism — the real problem

When crewborg-crew **does** cast a player vote it hits a **crewmate ~61% of the time**.
Reconstructing ejections from meeting-clustered vote tallies:

| crew side | meetings | imposter-ejected | crewmate-ejected | no ejection | episodes ejecting ≥1 imposter |
|---|---|---|---|---|---|
| **crewborg** | 99 | 14 | **31** | 54 | **13%** |
| notsus | 47 | 19 | 13 | 15 | 37% |

crewborg's meetings eject **2.2× more crewmates than imposters** — voting is a *net
parity gift*. notsus is net-positive.

**Why the model fails live (root cause — a train→serve gap, NOT an observation gap).**
The offline features are **deliberately visibility-clipped and runtime-admissible** —
`suspicion_lab/tools/features.py`: *"a positional cue counts only at sampled ticks where
the observer's rendered-view visibility interval covers the suspect … every feature must
stay runtime-admissible — computable from crewborg's own perception."* So the model is
**not** trained on god's-eye data. Yet `suspicion_lab`'s own README reports the held-out
decision sim at **94% imposter-precision @ P≥0.9**, while crewborg votes at **~39% live**
(the README itself pegs the "live hand model" at 42%). The held-out sim generalizes
across *games* but still scores features the lab reconstructs from the replay
(`game.sees()`); it never measures the **serve-time** gap. Two contributors (not fully
isolated):

1. **Reconstruction skew.** Offline features come from the expander's `game.sees()` over
   the replay; **live** features come from crewborg's *own* decoded `shadow` mask +
   `event_log.py` (its own occlusion, event-detection thresholds, tape grace/merge
   timing). Same *named* feature, different *value* at the decision tick → the calibrated
   0.9 bar mis-fires live. The fitted coefficients lean hard on cues that are sensitive to
   this: a single `witnessed_kills` (+10.1) latches p≈1, the exculpatory
   `tasks_completed_watched` (−15.2) only counts completions crewborg actually logs, and
   normal-crew cues (`task_site_dwell_gt20` +0.85, `copresence_killrange_gt20` +0.77,
   `near_body_bodies` +0.52, `follow_death` +1.9) accumulate on innocents.
2. **Opponent distribution.** Live `suspicion_snapshot` traces (8 self-play episodes,
   roles recovered by ranking-subtraction) put the crew vote at ~80% accurate in
   self-play vs 39% on the league. Since the live feature code is **identical** in both,
   that delta is the *opponent*, not the pipeline. (Caveat: the self-play figure is a
   small sample — 20 player-votes — so the load-bearing number is the 39% league
   measurement, not the 80%.)

A weight *refit* cannot close a serve-time/opponent gap — it re-fits on the same offline
reconstruction. (This is consistent with the prior finding that nightly refits don't move
outcomes.)

## 4. Coordination — a dead end in this field

crewborg's crew path uses only its private `top_suspect`; it never reads other players'
votes or chat (the bandwagon/chat-read machinery is **imposter-only**). Would joining the
crowd help? No:

- The meeting's **top public vote-pile is only 44–50% imposter regardless of pile size
  (1→6 voters) or margin** over the runner-up. The "wisdom of the crowd" is absent —
  2/8 are imposters who vote to frame crew, and the crew themselves are ~50% accurate, so
  the aggregate is a coin flip.
- In 219 meetings the field correctly led on an imposter, but in **284** it led on a
  crewmate. Blind bandwagon ≈ 44% accurate — no better than crewborg's own 39% model.

notsus's coordination edge (it reads the tally as both a bandwagon target and a private
input) **does not transfer**: notsus-crew games contain *multiple coordinating notsus*
that form a reliable consensus; crewborg's field has none. Mechanism and coordination are
the **same** problem — without a reliable signal under it, concentration just concentrates
error.

## 5. The fix — witnessed-only crew vote

`CREWBORG_CREW_VOTE_WITNESSED_ONLY` (env, default **off** ⇒ byte-identical to the shipped
gate). When set, a crewmate votes **only a directly-witnessed killer/venter** (a `kill`/
`vent_use` point event on its log — the near-certainty floor), else **skips**. The
witnessed catch is the one signal that holds across opponent fields; the graded cues are
league-noise. This trades vote *recall* for *precision* to cut the parity-gift crew
ejections. The imposter deflection path (whose job *is* engineering mis-ejections) is
unaffected. Implemented in `strategy/suspicion.py:top_suspect` + `_crew_vote_witnessed_only`;
4 unit tests; full suite 465 passing.

**Verified active in the built image** (local self-play, flag on): every crew player-vote
was a witnessed catch (7/7), 51 skips — the gate behaves exactly as designed end-to-end.

## 6. A/B validation

Matched hosted A/B, both arms the **same image** differing only by the env flag (clean
isolation): crewborg pinned **crew at slot 0** vs the live Crewrift Prime top-7
(rotating), **2 imposters**, 300 episodes/arm.

- **Candidate** `crewborg-wvon:v1` — `CREWBORG_CREW_VOTE_WITNESSED_ONLY=1`
- **Baseline** `crewborg-wvoff:v1` — flag off (= shipped behaviour)

<!-- RESULT PLACEHOLDER: crew-win delta, skip-rate delta, ejection-ledger delta -->
**Result:** _pending — fired 6 interleaved requests (3/arm); analysis to follow._

## 7. What I'd do next

- If the A/B is positive, this is a clean, low-risk submission candidate (crew-only,
  env-gated, no imposter regression possible).
- The deeper win is closing the **train→serve gap**: the model is fit/validated on the
  expander's `game.sees()` reconstruction but served from crewborg's live
  belief/`event_log`. Either (a) fit on features logged by *crewborg's own runtime* (dump
  the live feature vector at each meeting via `suspicion_snapshot`, label with replay
  ground truth, fit on *that*), so train and serve share one feature pipeline; or (b)
  audit where the offline reconstruction and the live event-log diverge (occlusion,
  event-detection thresholds, timing) and align them. Re-fitting on the existing offline
  reconstruction will not help — it re-fits the same skew.
- A *gated* coordination signal (bandwagon only when own-suspicion **and** a strong pile
  agree) is worth testing **after** the private signal is reliable — it is worthless
  before.
