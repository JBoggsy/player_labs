# Suspicion learning — fitting the evidence model from scraped replays

**Status:** proposed design (2026-06-12), not yet built. Companion to
[`suspicion.md`](suspicion.md), which documents the *current* hand-tuned Bayesian
model this pipeline is designed to replace the weights of. Read that first.

**The problem, in one paragraph.** Every suspicion weight in `strategy/suspicion.py`
is a hand-written guess fit from **zero games** (suspicion.md §7). League evidence
says the result is miscalibrated where it matters: 58% of crewborg's crew
player-votes hit *crewmates*, votes ejected an imposter in only 2 of 40 sampled
games, and crew ejections ran 14-in-20-losses vs 4-in-20-wins — mis-votes are
parity gifts (see TENTATIVE_LESSONS, RowDaBoat investigation). Meanwhile the league
generates ~1,200 fully-labelled games per day, and the upgraded replay expander
(coworld-crewrift #57) now emits everything needed to fit the model properly —
including **exact per-observer visibility**. This document proposes the end-to-end
system: scrape → expand → per-observer dataset → fit → ship weights into the agent.

---

## 1. Two structural model changes (requested, land with the fitted weights)

1. **Sum evidence *instances*, not types.** Today a player's most-suspicious event
   *per type* is taken (`max`), so seeing someone near two different bodies counts
   the same as one. Change `_graded_log_lr` to **sum across instances** (per-type
   `max` → per-instance contributions). Naive Bayes justifies this: independent
   observations multiply LRs. Guard against the known dependence failure (one long
   behaviour re-logged as many intervals) by **deduplicating instances on distinct
   context** — near-body events count once per distinct *body*, follows once per
   distinct *(target, death)*, vent dwells once per distinct *vent visit* — not per
   logged interval.
2. **Exculpatory evidence (`LR < 1`).** The current model is positive-only, so the
   prior (0.286) is everyone's floor and the "clear leader" vote rule fires off a
   single weak cue against an otherwise-flat field. With negative-weight evidence,
   innocent-looking players sink *below* the prior and the field separates honestly.
   What it looks like falls out of training data rather than intuition (§5 lists
   candidates — e.g. "watched them complete a task that actually completed", "they
   reported a body", "long co-presence with no kill while killable").

⚠️ **Interaction warning — do not land #1 alone.** Instance-summing with the
*current* hand weights strictly raises posteriors (more evidence ⇒ more sum), which
lowers the effective vote bar and produces **more** mis-votes — the opposite of the
vote-restraint direction. Either land both changes together with **fitted** weights,
or, if shipped early, pair with an interim guard (per-type contribution caps, or the
raised vote thresholds from §7).

---

## 2. System overview

```
            A. SCRAPE                B. EXPAND                  C. DATASET
  league rounds + xreqs    version-matched expand_replay    per-(observer,suspect)
  replays via               --format jsonl                  feature rows at decision
  fetch_artifacts    ───▶   --snapshot-every N        ───▶  points, labelled with
  (~90–135 KB/replay)       (events + states +              ground-truth roles
                            visibility intervals)                 │
                                                                  ▼
            E. DEPLOY                              D. TRAIN
  weights.json vendored into the image   ◀───     logistic regression over the
  suspicion.py loads it; same log-odds            evidence features (= fitted
  runtime, zero ML dependency in-game            additive log-LRs) + calibration
                                                  + decision-level vote simulator
```

The load-bearing simplification: the expander computes **exact rendered-view
visibility for every (observer, target) pair every tick** — so "what did this
player actually see" is *computed*, not modelled. P(evidence seen) dissolves into
set intersection: an observer's evidence is the global event stream clipped to
their visibility intervals. Offline features and runtime features can therefore be
the *same* quantities.

---

## 3. Stage A — scraping games

**Sources.** (a) Daily-league Competition rounds: ~200 episodes/round, a round
every ~10–15 min ⇒ ~1,200 labelled games/day, all reachable via
`coworld rounds → episodes` and `fetch_artifacts.py` (the `coworld-episode-artifacts`
skill). (b) Our own experience-request batches. (c) Backfill: any episode whose
replay is still served (replay URLs are S3 objects; availability window unverified —
measure during build-out).

**What to store per episode:** `replay.json.z` (~90 KB), `results.json`,
`episode.json` (already what `fetch_artifacts.py` produces). 10k games ≈ ~1.5 GB —
trivially affordable; keep everything, dedupe by episode id.

**Layout.** `crewrift_lab/suspicion_lab/` (new):

```
suspicion_lab/
  corpus/                 raw episodes (fetch_artifacts layout, append-only)
  expanded/<episode>.jsonl.zst    cached expander output (or transient, §4)
  dataset/<date>.parquet  per-(observer,suspect,decision-point) feature rows
  models/<run>/           fitted weights + metrics + provenance
  tools/                  scrape_corpus.py, build_dataset.py, fit.py, eval.py
```

A `scrape_corpus.py` cron/loop pulls new completed rounds incrementally (idempotent
by episode id, like fetch_artifacts).

## 4. Stage B — expansion (and the version-match constraint)

The new expander (`tools/build_expand_replay.sh --ref <sha>`, run with
`--format jsonl --snapshot-every 24`) re-simulates the replay and emits one JSON row
per event. **Verified working 2026-06-12:** the master build (`42fed21`) cleanly
expands fresh league replays (no hash fail). Full row catalogue, from reading
`tools/expand_replay.nim` at `42fed21`:

| row key | contents | use |
| --- | --- | --- |
| `episode_metadata` | full game config: `kill_range=20`, `kill_cooldown_ticks=500`, `report_range`, `vent_range`, `task_complete_ticks=72`, `vote_timer_ticks=1200`, `imposter_count`, `tasks_per_player`, `button_calls=1`, `max_ticks` | normalize features across configs |
| `map_geometry` | rooms (named rects), task sites, vents (+groups), button, home | spatial features, room graphs |
| `player_manifest` | per player: slot, label, color, **ground-truth role**, home, assigned tasks | **labels** |
| `player_state` (sampled every N ticks + on every event tick) | x, y, velocity, room, alive, connected, active_task, task_progress, **kill_cooldown**, vent_cooldown, button_calls_used, reward | trajectories, co-movement, "was killable" |
| `body_state` | body positions/rooms | near-body context |
| **`player_visible_interval`** / **`body_visible_interval`** | per (observer → target): tick range, duration, room, position, both roles; `visibility_basis: rendered_view`, exact boundaries | **the observability ground truth** |
| discrete events | `kill` (**true sim attribution** — fixes the old re-sim ambiguity), `body`, `died` (= ejection when not kill-attributed), `revived`, `vote_called_body` (reporter + victim + room), `vote_called_button` (caller), `vote_cast` (voter → target/skip), `chat` (full text), `started_task` / `completed_task` (+`while_dead`), `entered_room`/`left_room`, `phase`, `score` (itemized reason) | evidence events + outcomes |

Output is ~3 MB/game at `--snapshot-every 24` (~1 s cadence) — cache compressed or
treat as a transient stage piped straight into feature extraction.

**Version matching.** The expander only expands replays recorded by the same game
build (per-tick hash). Today master works on live replays. When the league
redeploys: builds hash-fail on *fresh* replays → bump the expander ref (the
existing `versions.env` discipline) and keep **one binary per game version**
(`expand_replay-<sha>`); tag each corpus episode with the game version that
expanded it. Old corpus segments stay expandable by their matching binary. Note the
visibility/JSONL features only exist from `42fed21` onward — if a *pre-#57* game
version needs expanding, the JSONL emitter must be cherry-picked onto that ref (it
is observability-only, so the sim hash is unaffected; verify on one replay).

## 5. Stage C — the per-observer dataset

**Unit of analysis: one (observer, suspect, decision-point) row.** Evidence is
observer-relative (suspicion.md §5.4) — we reconstruct what each *crew* observer
saw, exactly:

- **Visible evidence** = global events ∩ the observer's `player_visible_interval`s
  (e.g. suspect near a body counts only if the observer could see the suspect at
  that tick; a *follow* the observer watched for 30 of its 80 ticks contributes
  duration 30). This is the same clipping the agent's runtime perception performs
  naturally, so offline and runtime features agree by construction.
- **Public evidence** needs no visibility: everything in meetings — votes, chat,
  who reported, who buttoned, the ejection results, plus the census (who is alive).

**Decision points.** Snapshot each observer's cumulative features at each
**meeting's vote moment** (the decision the model actually serves), and at evenly
spaced mid-play ticks (serves the Accuse decision). Label = suspect's true role
from `player_manifest`. ~6 crew observers × ~7 suspects × ~2–4 meetings ⇒ **~100+
rows/game, ~10⁵ rows per 1k games** — ample for logistic regression.

**Candidate evidence features** (the initial catalogue; the model selects what
earns weight). Existing cues, now instance-summed: near-body (per distinct body,
with dwell shape), follow-to-death, tailing-the-observer, vent dwell, witnessed
kill/vent. New incriminating candidates: *last-seen-with-victim* (suspect visible
with victim in the victim's final visible window, then victim found dead),
*co-room-with-kill-site* around kill time, *unseen-traversal* (exited room A,
appeared in far room B implausibly fast — vent inference), *camping/loitering vs
task sites*, *meeting behaviour*: voted against players who turned out crew, voted
in lockstep with one other player (imposter blocs — visible in our 40-game sample),
accused early with no body. Exculpatory candidates: *completed-a-real-task while
watched* (the observed `completed_task` event landed during visibility — fakers
never complete), *reported a body*, *called the button*, *long benign co-presence*
(killable + alone with the observer/others for ≫ kill windows, no kill — absence
evidence), *was visibly elsewhere during a kill* (alibi — visibility interval
overlapping the kill tick in a different room). Each feature must be computable
from runtime perception too (§7) — that constraint is part of the catalogue's
definition of "admissible".

## 6. Stage D — the model (keep it simple: fitted additive log-LRs)

**Logistic regression, L1-regularized, over the feature vector.** This is exactly
"learn the evidence weights": coefficients *are* additive log-LRs, the intercept
absorbs `logit(prior)`, and the in-game architecture (sum log-odds → sigmoid) is
unchanged — the agent just loads different numbers. Negative coefficients are the
exculpatory evidence of §1.2. L1 prunes the candidate catalogue down to evidence
that *actually* improves the model — the "look for any evidence that helps" loop
becomes: add a candidate column, refit, keep it if it survives regularization and
improves held-out decision metrics.

- **Shapes without nonlinearity:** bin graded features (duration/distance) into a
  few buckets, one coefficient each — recovers the §6-of-suspicion.md "fit the
  shape per bin" plan inside one linear model (e.g. near-body dwell 0–12 / 12–48 /
  48+ ticks learns the decreasing shape if it's real).
- **Calibration is the point**, not just ranking: vote thresholds are probabilities.
  Validate with reliability curves; Platt/isotonic only if LR's native calibration
  is off. Group-aware CV (split by *game*, never by row) to avoid leakage.
- **Decision-level evaluation, not just AUC:** replay held-out meetings through the
  fitted posterior + a candidate vote policy and report the metrics that decide
  games: imposter-hit rate of votes cast, crew-mis-vote rate, would-have-skipped
  rate — compared against (a) the current hand model, (b) always-skip (the
  RowDaBoat policy). **A model only ships if it beats always-skip on a
  net-parity-cost metric** (mis-ejections weighted as the −1 crew they cost vs
  imposter ejections as roughly +1); always-skip is the strong league-validated
  baseline, so beating it is a high bar and "ship the thresholds that make us vote
  almost never" is an acceptable outcome.
- **Why not more (yet):** per-cue binned-ratio refit (pure naive Bayes) ignores
  cue correlation — LR handles it in the same linear family. GBDT/NNs break the
  drop-in additive runtime, cost calibration work, and need feature parity anyway.
  A sequential/joint model (imposter-budget redistribution across suspects) is the
  principled next step *after* the linear weights are validated — revisit then.

## 7. Stage E — runtime integration

1. **Weights artifact.** `fit.py` emits `suspicion_weights.json` (feature → coef,
   intercept, bin edges, model/version provenance). Vendored into the image like
   the nav bake; `suspicion.py` loads it at import with the current constants as
   fallback. No ML dependency in-game — scoring stays a dot product.
2. **One feature-extractor, two adapters.** A shared `features.py` defines each
   feature over an abstract event stream; adapter (a) feeds it offline expanded
   JSONL clipped by visibility intervals, adapter (b) feeds it the live perception
   tape + event log (`strategy/event_log.py` kinds: `task`, `vent`, `near_body`,
   `tailing_self`, `proximity` + witnessed point events + meeting observations).
   Parity tests assert both adapters produce the same features on the same game
   (expand one of our own episodes, compare against the agent's traced features —
   crewborg's `telemetry.jsonl` already records its event log).
3. **Thresholds re-derived, not inherited.** `VOTE_PROBABILITY` /
   `VOTE_LEAD_MIN_P+MARGIN` / `ACCUSE_THRESHOLD` get re-chosen by the §6 decision
   simulator on the *fitted* posterior (likely outcome: vote only near witnessed-
   level certainty; keep Accuse's button-slam — the CD-reset stall is independently
   valuable — but decouple its accusation/vote unless the posterior clears the new
   bar).
4. **Gate like any change:** Gate-1 smoke, then a `crewrift-ab` matched A/B (2-imp
   pinned roster per the standing lessons) with crew win + mis-vote rate as target
   axes, before any league submission.

## 8. Build order (each step lands value alone)

1. **Corpus + expansion** (`scrape_corpus.py`, per-version expander cache) — also
   immediately useful for every other analysis we do.
2. **Dataset builder** (`build_dataset.py`: visibility clipping, decision-point
   snapshots, labels) + a data-sanity report (per-cue imposter/crew ratios — the
   first real look at which current weights are wrong).
3. **Fit + decision simulator** (`fit.py`, `eval.py`); pick weights + thresholds.
4. **Runtime weights loading + shared extractor + parity tests**; implement §1's
   instance-summing and exculpatory support in `suspicion.py` as part of this step
   (they're just the runtime mirror of the fitted model's structure).
5. **A/B, iterate, ship.** Then iterate the §5 catalogue (add candidate → refit →
   keep if it earns weight).

## 9. Risks / open questions

- **Field non-stationarity.** Weights fit to *this* field's behaviour (notsus
  variants, truecrew, …) — refit cadence needed as the league evolves; date-stamp
  corpus segments and prefer recent games in training weights.
- **Observer asymmetry.** Training on all crew observers fits "an average
  crewmate's vantage"; crewborg's movement policy differs, so its evidence
  *exposure* distribution differs. Mitigation: the features are
  per-observation-clipped (correct by construction); if it matters, reweight
  training rows toward observers whose trajectories resemble crewborg's.
- **Replay retention window** unmeasured — if old replays expire, the corpus is
  append-as-you-go (the scraper's job).
- **Imposter-side reuse.** The same fitted posterior improves *imposter* meeting
  play for free (deflect onto whoever the model says looks guilty to others; avoid
  bandwagons that won't stick) — deliberately out of scope for v1.
- **Chat trust.** Chat features treat claims as unverified signals; the field
  contains scripted lines ("just resetting imposter cool downs") that are honest,
  and fabricated accusations (ours included) that aren't. Let the fit decide if
  chat carries weight; don't hand-trust it.
