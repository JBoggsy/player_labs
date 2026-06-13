# Suspicion — Bayesian P(imposter)

**Status:** living document. This is the canonical, durable home for crewborg's
suspicion model and especially its **per-event log-LR functions** (§3) — the place
where we record, justify, and improve the evidence weights as we learn them from
games.

> **Since 2026-06-12 the production posterior is the FITTED model** — weights
> learned from scraped league replays (pipeline + design:
> [`suspicion-learning.md`](suspicion-learning.md); weights vendored at
> `data/suspicion_weights.json`). Under it, evidence **instances are summed**
> (deduped per context — per body, per victim, per vent visit), **exculpatory
> evidence exists** (negative weights — e.g. real-task dwell time), an **exposure
> feature** weighs evidence against opportunity, and the crewmate vote fires only
> at calibrated near-certainty (`WEIGHTS_VOTE_PROBABILITY = 0.9`, **no clear-leader
> rule** — it was the mis-vote engine; held-out decision sim: ~100% imposter
> precision at this bar). An imposter *deflecting* keeps the legacy clear-leader
> logic (mis-ejections are its goal, not a risk). Witnessed kill/vent stays a
> definitional near-certainty floor on both paths. The hand-written model below is
> the **fallback** when no weights load (`CREWBORG_SUSPICION_WEIGHTS=0` forces it)
> and remains the conceptual reference for what each cue means.

- **Code:** [`strategy/suspicion.py`](../../strategy/suspicion.py) — the `_*_log_lr`
  functions + `WITNESSED_LOG_LR`; the update is `update_suspicion(belief)`.
- **Spec summary:** [`design.md` §10.1](../../design.md).
- **Inputs:** the perception tape (§5.1) and per-player event log (§5.2), both in
  `design.md`.

If a value here and in the code ever disagree, **the code is what runs** — but **a
change should land in both**, with the rationale recorded here.

---

## 1. What we compute

For a **crewmate** observer, for every *other* player, the posterior probability
they are an imposter:

```
belief.suspicion[color] = P(imposter | everything we have observed)   ∈ [0, 1]
```

The posterior drives two crewmate actions (both crewmate-only — an imposter accrues
no suspicion, a ghost neither flees nor votes):

- **the meeting vote** — `top_suspect` votes the clear leading suspect (§4).
- **Accuse** — `active_tail_suspect` (a live tail over `ACCUSE_THRESHOLD`) makes us
  drop tasks and go call a meeting to accuse them (the renamed Flee mode; §4).

`believed_imposters` is every **alive** player at or above `FLEE_PROBABILITY` (0.9) —
the near-certain set, still exposed as belief state (e.g. it seeds the meeting vote),
though it no longer gates a reactive *run-away* mode (Accuse replaced Flee).

This is a real probability with units, so each threshold means something concrete —
"call a meeting on a tail once we're ≥60% sure" — rather than an arbitrary score.

---

## 2. The model

### 2.1 Prior — combinatorics

With `P` players total and `K` imposters, a crewmate knows all `K` imposters are
among the other `P − 1` players. By symmetry, each other player's marginal prior
is:

```
prior = K / (P − 1)
```

- `P` = `belief.total_player_count` (estimated early from distinct colors seen;
  authoritative once the meeting census arrives, §4.3).
- `K` = `belief.imposter_count` if set, else **derived** from the player count via
  Crewrift's own auto-imposter formula `(P − 3) // 2` (`sim.nim` `ratioImposterCount`
  / `effectiveImposterCount`; default `autoImposterCount = true`). Override
  `belief.imposter_count` if a game is known to use a fixed count.

The prior is clamped to `[PRIOR_MIN, PRIOR_MAX]` = `[1e-3, 0.99]` so its log-odds
stays finite.

### 2.2 Update — log-odds Bayes

Each piece of evidence is incorporated by a **likelihood ratio**

```
LR_e = P(observe e | player is imposter) / P(observe e | player is crewmate)
```

In log-odds form, evidence is additive (this is just Bayes' rule for independent
evidence):

```
logit(P) = logit(prior) + Σ_e log(LR_e)
P        = sigmoid(logit(P))
```

where `logit(p) = ln(p / (1 − p))` and `sigmoid(x) = 1 / (1 + e^−x)`.

- `logLR > 0` ⇒ evidence raises suspicion; `= 0` ⇒ neutral; `< 0` ⇒ lowers it (we
  have no `< 0` evidence yet — see §5, positive-evidence-only).
- Each graded cue's `logLR` is a **function of the event's features** (duration,
  distance), not a flat constant — see §3. We aggregate **per evidence type with
  `max`** (a player's most-suspicious instance of that type), so repeated logging of
  the same behaviour can't inflate the posterior and an unbounded event log (§5.2)
  is safe.
- Because a player's role is a **fixed latent variable**, evidence does not decay in
  time: observing someone vent at minute 1 is permanent evidence about their
  (unchanging) role. There is no time-decay term, by design. (Note this is distinct
  from the *body-proximity* function decreasing with *dwell duration* — that's about
  the within-event shape, not about forgetting over wall-clock time.)

### 2.3 Worked example

8 players ⇒ `K = (8 − 3) // 2 = 2`, so `prior = 2 / 7 ≈ 0.286`, `logit ≈ −0.916`.

| Evidence observed | logLR | logit | P(imposter) | near-certain (≥0.9)? |
|---|---|---|---|---|
| none (the prior) | — | −0.916 | 0.286 | no |
| brief `body proximity` (LR≈3) | +1.10 | 0.18 | 0.545 | no |
| sustained `tailing_self` (LR≈6.5) | +1.87 | 0.96 | 0.722 | no (but ≥ `ACCUSE_THRESHOLD`) |
| `vent dwell` (LR 8) | +2.08 | 1.16 | 0.762 | no |
| `vent dwell` + `follow-to-death` (LR 6) | +2.08 +1.79 | 2.96 | 0.950 | **yes** |
| `witnessed vent` (LR 1e6) | +13.8 | 12.9 | 0.99999 | **yes** |

So a single graded cue is suspicious but not near-certain; corroboration crosses the
near-certain bar; a witnessed catch is effectively certain regardless of the prior.

---

## 3. The evidence catalogue + per-event log-LR functions

This is the load-bearing part of the model. **The functions and their constants are
the learnable surface** — hand-written initial cuts (no games analysed yet), meant
to be (re)fit from replays (§6). Record every change in the provenance log (§7).

### 3.1 Why functions, not flat ratios

A flat LR per evidence type is wrong because the relationship between an event's
*features* and guilt is not flat — and is sometimes **inverted**. A skilled imposter
**flees** a kill instantly; they do not loiter. So:

- A long dwell next to a body is **reporter** behaviour (innocent); a *brief*
  presence is the only window on a fleeing killer. ⇒ body-proximity log-LR should
  **decrease** with dwell.
- Following someone for a sustained stretch right up to their death is stalking. ⇒
  follow log-LR should **increase** with dwell.
- Someone shadowing *us* over time is a likely stalker lining up its target — and we
  read our own position perfectly, so it's a high-quality signal that needs no death.
  ⇒ being-tailed log-LR should **increase** with dwell (a smooth logistic: a brief
  brush ≈ nothing, a sustained tail ≈ near-certain).
- Standing on a vent is weak either way (a real venter *teleports* — caught by the
  near-certain transition detector). ⇒ ~flat past a pure pass-through.

So each graded cue gets a small **`_*_log_lr(event[, belief]) -> float`** function
(`suspicion.py`). The form + its constants are the parameterization; there is no
learning machinery yet (and deliberately nothing neural). A type's contribution is
the **max** over that player's events of that type (§2.2).

### 3.2 Near-certain (definitional, constant)

| Evidence | Source | Detected when | log-LR |
|---|---|---|---|
| witnessed kill | tape transition (§5.1) | victim alive last frame, body now, exactly **one** other player within `KILL_RANGE_SQ` of the victim last frame | `WITNESSED_LOG_LR` = ln 1e6 |
| witnessed vent | tape transition (§5.1) | *emergence* (vent + `VENT_WALK_MARGIN` in line of sight & clear last frame, occupied now) or *submersion* (player in the vent last frame, gone while it stays in sight); LoS via the `shadow` mask (§4.4) | `WITNESSED_LOG_LR` |

These are definitional (we *saw* it) and not learned. A detection is recorded as a
`kill` / `vent_use` **point event on the perpetrator's event log** (not a separate
`confirmed` set), so every signal — graded or near-certain — flows through the one
posterior; `_evidence_log_lr` maps the presence of any such event to `WITNESSED_LOG_LR`.
`witnessed_imposters(belief)` derives the set of colors with such an event for
tracing/forensics.

### 3.3 Graded functions (over the event log, §5.2)

| Function | Event | Form (log-LR) | Constants | Shape / rationale |
|---|---|---|---|---|
| `_vent_dwell_log_lr` | `vent` | `VENT_DWELL_LOG_LR` if `duration > VENT_CROSS_TICKS` else `0` | `VENT_CROSS_TICKS=3`, `VENT_DWELL_LOG_LR=ln 8` | ~flat once it's more than crossing the tile; weak (the transition detector owns real venting). |
| `_body_proximity_log_lr` | `near_body` | `0` if `min_dist > BODY_NEAR_DIST`, else `BODY_NEAR_LOG_LR · max(0, 1 − duration/BODY_FADE_TICKS)` | `BODY_NEAR_DIST=16 px`, `BODY_NEAR_LOG_LR=ln 3`, `BODY_FADE_TICKS=48` | **decreasing** in dwell: full at first sight, fades to 0 by ~2 s (a long camp ⇒ reporter ⇒ neutral). |
| `_follow_log_lr` | `proximity` | `0` unless target now dead and `\|death_seen − end\| ≤ FOLLOW_DEATH_WINDOW_TICKS`, else `FOLLOW_LOG_LR · min(1, duration/FOLLOW_FULL_TICKS)` | `FOLLOW_FULL_TICKS=48`, `FOLLOW_DEATH_WINDOW_TICKS=72`, `FOLLOW_LOG_LR=ln 6` | **increasing** (saturating) in dwell: longer shadowing of a now-dead victim ⇒ more. |
| `_tailing_self_log_lr` | `tailing_self` | `TAIL_SELF_LOG_LR_MAX / (1 + exp(−TAIL_SELF_STEEPNESS·(duration − TAIL_SELF_MIDPOINT_TICKS)))` | `TAIL_SELF_LOG_LR_MAX=ln 6.5`, `TAIL_SELF_MIDPOINT_TICKS=30`, `TAIL_SELF_STEEPNESS=0.2` | **logistic** in how long they shadowed *us*: a brief brush ⇒ ~0, leaves zero ~15 t, half at 30 t, saturates at a **moderate P ≈ 0.72** by ~50 t (deliberately *not* near-certain — lots of crew move together). Needs **no death** (unlike third-party follow). Crossing `ACCUSE_THRESHOLD` (~34 t of live tailing) triggers Accuse: go call a meeting. |

`VENT_WALK_MARGIN` (3 px, one tick of walking) is a perception guard for the
vent-emergence detector, not a scoring parameter.

### 3.4 How to parameterize / change a function

Each function is plain Python over the event's fields (`duration_ticks`, `min_dist`,
`target_color`) plus `belief` (for the target's life status). To re-shape a cue:
edit its constants (magnitude `*_LOG_LR`, scale `*_TICKS`, distance gate) or its
closed form. Keep three things aligned: the **function**, this **table**, and the
**provenance log** (§7). Tests assert *relational* behaviour (evidence raises P; one
cue stays below the near-certain bar; corroboration crosses it; body-proximity brief > long),
so they survive re-tuning unless the qualitative shape changes.

### 3.5 Deliberately excluded (too noisy to score)

- **Brief proximity** to a *living* player — crew constantly pass within kill range.
- **Distant near-body** — beyond `BODY_NEAR_DIST` is just passing through.
- **`task` dwell as exculpation** — would lower suspicion for "looking busy", but
  imposters fake tasks (Pretend does exactly this), so it isn't reliable innocence.

These are still in the event log and are serialized for the opt-in meeting LLM;
they just map to a `0` log-LR in the deterministic Bayesian model.

---

## 4. Thresholds & tuning knobs

| Knob | Value | Effect |
|---|---|---|
| `FLEE_PROBABILITY` | 0.9 | the near-certain bar: `believed_imposters` = alive players at/above it. Still computed as belief state (it seeds the vote) but no longer gates a reactive *run-away* mode. |
| `ACCUSE_THRESHOLD` | 0.6 | the "sketched out" bar: an **active tail** whose posterior is at/above this triggers **Accuse** (drop tasks, go call a meeting). ~34 t of live tailing. |
| `ACCUSE_TAIL_RECENCY_TICKS` | 6 | how recently a `tailing_self` interval must have been extended to count as *active* (robust to a brief occlusion). |
| `VOTE_PROBABILITY` | 0.8 | posterior at/above which a player is **voted** out on its own — near-certainty (a witnessed catch) regardless of the field. A touch below the near-certain bar, as a vote is a deliberate one-shot decision. |
| `VOTE_LEAD_MIN_P` / `VOTE_LEAD_MARGIN` | 0.5 / 0.2 | the *clear leading suspect* rule (below near-certainty): vote the top suspect when P ≥ `VOTE_LEAD_MIN_P` **and** it leads the runner-up by ≥ `VOTE_LEAD_MARGIN`. A flat/low field names no one ⇒ skip. |
| `PRIOR_MIN` / `PRIOR_MAX` | 1e-3 / 0.99 | clamp the prior so log-odds is finite. |
| `WITNESSED_LOG_LR` | ln 1e6 | how strong a witnessed kill/vent is (definitional). |
| `TAIL_SELF_*` (`LOG_LR_MAX=ln 6.5`, `MIDPOINT_TICKS=30`, `STEEPNESS=0.2`) | §3.3 | the being-tailed logistic: saturated strength (≈ P 0.72), its half-way duration, and ramp slope. |
| the per-event log-LR functions + their constants | §3.3 | how much each graded cue moves belief, *and its shape* vs. duration/distance. **The main thing to fit.** |

**Consumers of the posterior.** `active_tail_suspect(belief)` — the most-suspicious
player currently tailing us with P ≥ `ACCUSE_THRESHOLD` — gates **Accuse mode**: the
selector commits to that target, walks to the emergency button, and calls a meeting
(a one-shot per game; see design §7.1, §10). `top_suspect(belief)` — the **clear
leading suspect**: near-certain on its own (P ≥
`VOTE_PROBABILITY`) *or* a clear lead short of that (P ≥ `VOTE_LEAD_MIN_P` and ahead
of the runner-up by `VOTE_LEAD_MARGIN`), else `None` (skip a flat field) — is the
Attend Meeting vote target (design §7.1); the action layer maps that color → its
candidate-grid slot and steps the cursor onto it (§4.3), falling back to skip if the
target can't be resolved. The deterministic meeting path **accuses then votes** that
suspect (`build_accusation` → `"<color> sus: <reasons>"`, the ranked event-log cues),
and stays silent when there is no clear leader.

---

## 5. Assumptions and their consequences

These are v1 simplifications. Each is sound enough to ship and clearly documented so
we know what to revisit.

1. **Naive Bayes (conditional independence).** We treat evidence types as
   independent given role and sum their `log(LR)`. Correlated evidence (e.g. two
   cues that tend to co-occur) is over-counted → over-confidence. Mitigated for now
   by counting each *type* once and by conservative weights. A joint model is the
   eventual fix.
2. **Positive-evidence-only.** We only have `LR ≥ 1` evidence; absence of suspicious
   behaviour never lowers a player below the prior. A true model would also use
   exculpatory/absence likelihoods (e.g. "watched them a long time, never vented").
   Until then the prior is the floor.
3. **Static prior.** We use `K / (P − 1)` and don't redistribute the imposter
   "budget" as players are caught or die (e.g. with `K = 1`, catching the imposter
   should drop everyone else toward 0; it doesn't). A caught player still reads ≈1 via
   its overwhelming witnessed LR, so the vote is unaffected; the gap is in the *other*
   players' calibration. A proper joint/sequential model is a refinement.
4. **Observer-relative evidence.** Suspicion is built only from what *this* agent
   saw. Two crewmates can hold different posteriors about the same player. That is
   correct (it mirrors real play) but matters for learning (§6): LRs must be
   estimated from an observer's vantage, not from global ground truth of what
   happened.

---

## 6. Fitting the log-LR functions from replays

This is the durable process by which the functions improve. The agent never learns
at runtime — we (offline) fit each graded cue's function from labelled replays and
update §3 + §7.

The quantity each function approximates, **as a function of the event's features**:

```
logLR(e) = ln[ P(e's features | imposter) / P(e's features | crewmate) ]
```

For a feature like dwell duration, estimate the ratio **per bin** and read off the
*shape* (this is exactly how we found body-proximity should *decrease*):

```
                  fraction of imposter near-body events in this duration bin
ratio(bin) ≈  ───────────────────────────────────────────────────────────────
                  fraction of crewmate near-body events in this duration bin
```

Procedure:

1. **Replays give ground truth.** A replay records every player's true role. Load it
   with the viewer recipe in the lab's
   [`docs/crewrift-replays.md`](../../../../docs/crewrift-replays.md).
2. **Reconstruct observations from an observer's POV.** Evidence is what a crewmate
   *saw*, so re-run the event log + tape detectors as if crewborg were a particular
   crewmate in that game — using that player's line-of-sight/visibility, not the
   global state. Do this per (observer, game). Record each event with its features
   (duration, distance, target role) and the subject's true role.
3. **Bin by feature and estimate the ratio per bin** (with an *opportunity*
   denominator — players the observer could have caught, not all players).
4. **Smooth** (Laplace/add-k) so rare bins don't give 0/∞.
5. **Fit a simple closed form** to the binned ratios — keep the family in §3.3 (flat,
   linear-fade, saturating-ramp) unless the data clearly wants another simple shape.
   Update the function's constants (and the form if needed).
6. **Sanity-check independence.** Highly correlated cues are double-counted by naive
   Bayes — prefer merging or down-weighting.
7. **Update §3.3 + the provenance log (§7), then mirror into `suspicion.py`.** Re-run
   the suspicion tests; they assert *relational* properties (evidence raises P, one
   cue stays below the near-certain bar, corroboration crosses it, body-proximity brief >
   long), so they survive re-tuning unless the qualitative shape changed.

The witnessed-kill/vent log-LR is **definitional** (we saw it happen) and stays at
the near-certainty value; it is not fit.

The replay-analysis tooling itself is not built yet. The end-to-end design for it —
corpus scraping, the upgraded expander's JSONL/visibility output, per-observer
dataset construction, logistic-regression fitting (instance-summed, with
exculpatory evidence), and runtime weight loading — is proposed in
[`suspicion-learning.md`](suspicion-learning.md); this section's per-bin ratio
procedure survives there as the shape-via-binned-features part of the linear model.

---

## 7. Provenance log

One row per value-setting event. Keep this honest — it is how we know whether a
weight is a guess or earned.

| Date | Cue | Peak LR / shape | Source | Games | Notes |
|---|---|---|---|---|---|
| 2026-06-01 | witnessed kill/vent | 1e6, constant | definitional | — | we saw it; not fit |
| 2026-06-01 | `vent_dwell` | 15, flat ≥24 ticks | hand estimate | 0 | initial guess (superseded) |
| 2026-06-01 | `body_linger` | 3, flat ≥24 ticks | hand estimate | 0 | initial guess (superseded — gate inverted the signal) |
| 2026-06-01 | `follow_to_death` | 6, flat ≥48 ticks | hand estimate | 0 | initial guess (superseded) |
| 2026-06-01 | `vent_dwell` | LR 8, flat past 3-tick crossing | hand estimate | 0 | dwell is weak (transition detector owns real venting) |
| 2026-06-01 | `body_proximity` | LR 3 at first sight → 0 by 48 ticks (**decreasing**) | hand estimate | 0 | a skilled imposter flees; long camp ⇒ reporter ⇒ neutral |
| 2026-06-01 | `follow_to_death` | LR 6, ramp to full by 48 ticks (**increasing**) | hand estimate | 0 | sustained shadowing of a now-dead victim |
| 2026-06-10 | `tailing_self` | LR logistic, peak ln 40, half at 30 ticks, slope 0.2 (**increasing**) | hand estimate | 0 | someone shadowing *us*; brief ≈ 0, ~50 ticks ⇒ P ≈ 0.94 (over the flee bar); needs no death (superseded same day) |
| 2026-06-10 | `tailing_self` | LR logistic, peak **ln 6.5**, half at 30 ticks, slope 0.2 (**increasing**) | hand estimate | 0 | lowered the ceiling so a sustained tail saturates at a *moderate* P ≈ 0.72 — enough to call a meeting + accuse (drives Accuse mode over `ACCUSE_THRESHOLD`), not enough to flee/auto-vote |
| 2026-06-12 | **all cues — FITTED** (`data/suspicion_weights.json`, v1-runtime) | L1 logistic regression: follow-to-death the strongest graded cue (+2.4/+2.7 binned); task-site dwell **exculpatory** (−2.1/−2.9); tailing ~10× weaker than the hand estimate (+0.49 at heavy exposure); witnessed-kill feature +3.96 (floor still ln 1e6) | **fitted from replays** (suspicion_lab, grouped CV AUC 0.704; full-feature ceiling 0.811) | 341 | first earned weights; instance-summed + exposure feature; crewmate vote bar 0.9, no lead rule (~100% held-out imposter precision). Superseded same day by v2-runtime |
| 2026-06-12 | **v2-runtime — full corpus + social detectors** (`data/suspicion_weights.json`) | adds the `strategy/social_evidence.py` counters: `tasks_completed_watched` **−10.9** (counter-decrement + dwell-gated; imposters can't produce one), chat stances (`accusations_made` +1.15, `times_accused` −0.72), attributed vote dots (`vote_agreement_with_observer` +0.82, `voted_against_observer` +0.37, `votes_skipped` −0.38) | fitted (grouped CV **AUC 0.801** vs full-feature ceiling 0.812; only the meeting-caller features remain offline-only — observable since game `4b9297d`'s MeetingCall interstitial, perception parse pending) | 1,857 | held-out decision sim @ P≥0.9: 94% imposter precision, net +17.3/100 vs always-skip (3× v1). Calibration 0.9–1.0 bucket → 0.92 actual |
| 2026-06-12 | **v3-runtime — meeting-caller parse: the FULL catalogue** (`data/suspicion_weights.json`) | adds the MeetingCall-interstitial caller (perception `MEETING_CALL_TEXT` → `reported_bodies`, `button_calls_made` **−1.59**); `task_site_dwell__gt20` flips ~neutral (+0.04) now that completions carry the exculpation — bare long dwell reads Pretend-like | fitted (grouped CV **AUC 0.812 = the full-feature ceiling**) | 1,857 | decision sim @ P≥0.9: 94% precision, net +19.1/100. Every offline feature is now runtime-observable |

---

## 8. Adding a new evidence type

1. **Make it observable.** Either way it becomes a `PlayerEvent` on the subject's log:
   a durative interaction adds a `PlayerEvent` kind in the event log (§5.2); a frame
   transition adds a detector on the tape (§5.1) that records a point event (e.g.
   `kill` / `vent_use`) on the perpetrator's log via `_log_witnessed`.
2. **Write its `_<cue>_log_lr(event[, belief]) -> float`** — a small closed-form
   function of the event's features (think about the *shape*: does the cue get more
   or less suspicious with duration/distance?), with named constants.
3. **Aggregate it** in `_graded_log_lr` (`max` over the player's events of that kind).
4. **Document** it in §3.3 + add a provenance entry (§7) — initially a hand estimate,
   flagged for fitting.
5. **Test** the relational behaviour (raises P; alone below the near-certain bar unless it's
   near-certain; and its feature shape, e.g. brief > long if decreasing).

---

## 9. Roadmap

- ~~Suspicion-aware voting~~ — **done**: Attend Meeting votes the highest-`P` live
  player when `P ≥ VOTE_PROBABILITY`, else skips (`top_suspect`; §4 consumers).
- **Exculpatory evidence** (`LR < 1`) and an absence model.
- **Dynamic/joint prior** (imposter-budget redistribution; §5.3).
- **More evidence types** from the event log + `chat_log` (§4.3) and `voting.dots`.
- **The offline LR-learning pipeline** (§6).
- ~~LLM meeting consumer~~ — **done**: the opt-in Attend Meeting LLM consumes the
  per-player view (identity + life + events + posterior), chat transcript, and
  vote tally for chat/voting reasoning.
