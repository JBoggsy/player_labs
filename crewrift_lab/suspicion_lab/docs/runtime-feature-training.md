# Reworking suspicion training onto crewborg's runtime features

**Status:** investigation (2026-06-30). The nightly auto-fit+submit cron is **disabled**
pending this rework (`tools/nightly_refit.sh` early-exits unless `NIGHTLY_REFIT_ENABLED=1`).

## Why

The shipped suspicion model is fit and validated on the **offline replay reconstruction**
(`suspicion_lab/tools/features.py` over `game.sees()`), then *served* from crewborg's
**live perception + `event_log`**. These two feature pipelines diverge → a train→serve
gap: ~94% imposter-precision on held-out *offline* rows vs ~39% on crewborg's *live*
votes (see `crewborg/docs/crew-voting-investigation.md`). Re-fitting on the same offline
reconstruction cannot close that gap — which is why nightly refits churned versions
without moving outcomes.

**The rework:** train on the features crewborg's runtime *actually computes*, captured by
its own tracing. Train and serve then share one feature pipeline by construction. The
runtime trace doubles as a **parity oracle**: diff it against the offline reconstruction
per (observer, suspect, meeting) to find and fix where `game.sees()` ≠ live belief.

## Is current tracing sufficient? — No, but the gap is one small emit.

### What we already have (good)
- **The right event exists and is already captured in hosted games.**
  `events.py:_observe_meeting_suspicion` emits `domain.suspicion_snapshot` once at each
  meeting start, per observer. It is in the **`voting`** trace group (`trace.py:135`),
  which the shipped champion's upload enables (`CREWBORG_TRACE_GROUPS=voting,…`), and the
  bridge uploads the trace as the policy artifact. So **every hosted crewborg game already
  produces a runtime corpus** — no infra change to *capture* it.
- Per suspect it emits: `color`, `p` (posterior), `confirmed` (witnessed), and an event
  summary (`kind, dur, target, region, min_dist`). It also emits the observer `role`,
  `prior`, `would_vote`, `vote_bar`, and the meeting `tick`.
- **Labels** are recoverable: the trace carries `episode_id` + suspect `color`; the replay
  / `results.json` gives `slot→role`, and `color↔slot` is the standard warehouse join.

### What is missing for exact runtime-feature training (the gap)
`strategy/suspicion.py:_fitted_features` — the exact model input — needs, per suspect,
quantities the snapshot does **not** carry:
1. **The 10 public/social counters** (`tasks_completed_watched`, `accusations_made`,
   `times_accused`, `times_defended`, `votes_cast`, `votes_skipped`,
   `voted_against_observer`, `vote_agreement_with_observer`, `reported_bodies`,
   `button_calls_made`) — `PlayerRecord` fields, emitted by **no** trace.
2. **`seen_ticks`** per suspect (→ `observed_samples`) — emitted by no trace.
3. **Per-event `end_tick`** — the event summary has only `dur`; `follow_death_samples`
   needs `end_tick` vs the victim's `death_seen_tick`.

From the event summary alone you can approximate the *positional* aggregates
(tail/copresence/vent/near-body/witnessed) but **cannot** reproduce `follow_death`,
`observed_samples`, or any of the 10 social counters — so the current trace is
**insufficient to reconstruct the exact feature vector**.

### The fix: emit the feature vector itself (one additive line)
`_fitted_features(belief, record)` already returns the exact named feature dict and is
pure. Emit it per suspect inside the `suspicion_snapshot` ranking (or a sibling
`suspicion_features` event). This single change:
- makes the trace **sufficient for exact runtime-feature training** (you train on
  literally the vector the live model scored — zero reconstruction);
- is the **parity oracle** for free: diff the runtime vector against `features.py`'s
  offline vector on the same (episode, observer, suspect, meeting) key;
- is **cheap** (≤7 suspects × a few meetings/game × ~22 floats) and bounded well under the
  artifact cap.

Optionally also emit the raw inputs (`seen_ticks`, per-event `end_tick`) to make parity
*debuggable* (localize which feature diverges), but the feature dict is the load-bearing
addition.

## Pipeline implications (beyond tracing)
- **Corpus source shifts** from league *replays* (any game, `game.sees()`-reconstructed)
  to crewborg's own *policy artifacts* (only games crewborg played, runtime-emitted). The
  new scraper pulls crewborg's uploaded trace artifacts + the matching replay for labels,
  instead of `scrape_corpus.py`'s replay-only path.
- **Volume** is bounded by crewborg's own game count; the pipeline may need to *generate*
  games (experience requests) rather than rely on incidental league play.
- **Decision-point/look-ahead parity holds:** `features.py` rows are cumulative-to-tick,
  prior-meetings-only; the runtime snapshot fires at meeting start before this meeting's
  ballots — same convention.
- **Fit unchanged in spirit:** `fit.py --features runtime` consumes the same named
  features; only their *source* changes (runtime trace vs offline reconstruction).

## Proposed sequencing
1. **Tracing emit** (this enables everything): add the runtime feature vector to
   `suspicion_snapshot`; add a unit test; verify in a local run that the emitted vector
   equals `_fitted_features` for the same belief.
2. **Parity harness:** for a batch of crewborg games, join runtime vectors to the offline
   `dataset.parquet` rows and report per-feature divergence — quantify the train→serve gap
   and confirm the runtime path is the trustworthy one.
3. **Runtime dataset builder + fit:** scrape artifacts+replays → runtime feature rows +
   labels → `fit.py`. Gate on held-out AUC computed **on runtime rows**.
4. **Re-enable** the nightly only when it fits on runtime features and the parity harness
   is green (`NIGHTLY_REFIT_ENABLED=1`), and reconsider the auto-*submit* (it should
   re-qualify behaviourally, not just by AUC).
