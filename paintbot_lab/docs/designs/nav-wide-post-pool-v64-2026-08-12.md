# v64 — wide post pool: potential posts everywhere, all choice at selection

**Status: APPROVED in discussion (James, 2026-08-12) and IMPLEMENTED same
day.** What it turned up, beyond the pool itself (~200–250 fully-scored
potential posts per front, vs 16): the widened pool **detonated a latent
performance landmine** — `squads.advancePoint` called
`routeDistance(home, candidate.pos)`, whose GOAL argument keys the lazy
Dijkstra cache, minting a full-grid field *per candidate* (the deep-dive's
M2 unbounded-minting hazard). Wall time exploded 6×; two hypotheses failed;
a 5-second `sample` of the one pegged process found it (all samples inside
`dijkstra` under `advancePoint`). Fixes, both root-level: (1) argument-order
rule — the goal slot takes stable goals only (homes/capture points),
arbitrary points go in the start slot (grid is undirected); (2) `fieldsFor`
returns `lent RouteFields` with expression-form callers, ending the ~1.4 MB
per-call copy for every caller including per-tick `flowWaypoint`. Net:
giant `post_ms` **18 ms** with the 14× pool (73 ms in v63), episode
tick-rate faster than v63, giant seat init ~1.0 s. Original plan below. Follows directly from the v63
review: ~16 candidates / 4–6 posts per front put the decision weight at
init with zero context; the belief-scored selection had almost nothing to
select from. The funnel caps were tuned for a cost model (expensive rays/
ducks, defenders-only consumer) that no longer exists post-hoist.

## Change

Pipeline (per front) becomes: gate-vicinity admission (v63, unchanged, incl.
empty-bucket fallback) → per-bucket retention with a **wide cap**
(`PostRayCandidatesPerBucket` 6 → **24**, same 32 px separation) → sightline
rays + duck pairing for **every** retained candidate (the 16-post shortlist
stage is gone; `PostShortlistCount` becomes the pool safety cap, 16 →
**256**) → every candidate carries the full final score
(0.65·sightline + 0.20·corridor + 0.15·duck-contrast). The static top-6
"posts" survive only as a no-context default view (and trace/viewer
labeling); they are no longer a separate consumer menu.

Duck policy: pool membership does NOT hard-require a duck (sparse areas keep
their best-available positions); ducklessness costs the 0.15 contrast term.
The final top-6 keeps the hard duck requirement (unchanged).

Selection unification: `defensivePostForSeat` now selects from the wide
candidate pool — same home-outward 64 px band ordering with score+facing
inside a band, plus a `PostSeparationPx` separation filter so dense pools
don't stack defenders on adjacent cells (seat-th distinct survivor).
`orderPost` is unchanged (it already searched candidates; the pool just got
real). Layer 4 intent profiles will later add the objective dimension.

Static stays static: per-front sightline orientation and all scoring
geometry. Out of scope: which defender/squad goes where (Q6).

## Validation

Property invariants extended to the pool (scores finite, separation within
buckets, defender seats distinct + separated); giant cost measured before
upload (rays+ducks now run on ~10× the candidates — expected low hundreds
of ms per front, budget check required); corpus renders (the simulator
should finally have alternatives to arbitrate); matched v64-vs-v63 batch,
same shape, paired giant probes.
