# Stencil online navigation initialization profile — 2026-08-03

> **Historical experiment record.** Version, source, and “current” language in
> this report refer to the dated experiment, not today's deployment.

## Verdict

Online navigation initialization is fast enough to keep. Across 100 real local
Paintbot games (200 policy starts), the worst observed startup was **453.5 ms**
on a giant 3,211x1,713 map while eight games / sixteen policy processes were
starting concurrently. The giant-map p95 was **419.3 ms**; standard-map p95 was
**67.8 ms**. This is one-time first-frame setup, not recurring per-tick work;
the local ready-paced server waits for the policy decision before advancing.

Dijkstra is the only meaningful optimization target: on giant maps it accounts
for 286.0 ms / 81.8% of mean startup. Walkability decode averages 10.4 ms,
vectorized erosion 52.5 ms, and cover extraction 0.2 ms. There is no evidence
that decode, cover, or the basic WorldMap representation needs optimization.

## Method

- Canonical game: Paintbot 0.7.180, source `052b058002014c16c49988f69004838ea8cc9a23`.
- Instrument: `tools/self_play.py --profile-nav-init` using the live manifest
  and exact detached game-source worktree.
- 100 generated 1v1 maps: 20 seeds at each explicit map size (`small`,
  `standard`, `large`, `huge`, `giant`).
- Eight episodes ran concurrently per batch, producing sixteen simultaneously
  starting stencil processes. This intentionally measures the self-play stress
  case rather than an unloaded microbenchmark.
- Each game ran for 40 ticks so both seats completed initialization even on
  giant maps. Gameplay outcomes are irrelevant.
- Timed boundary: snappy walkability decode and bool-mask conversion, WorldMap
  erosion and cover construction, and the two startup Dijkstra fields. Metrics
  freeze before ordinary first-tick item or tactical routing, so every one of
  the 200 samples measures exactly the same work.
- Raw summaries: ignored local artifacts under
  `paintbot_lab/self_play/nav-profile-v3/<size>/<run>/summary.json`.

## Results

All values are milliseconds. “Episode p95” is the p95 of the slower of its two
policy seats, which is the latency that gates episode readiness.

| map size | pixels | grid cells | seat mean | seat p50 | seat p95 | seat max | episode p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| small | 1,050x560 | 9,170 | 36.2 | 30.4 | 76.9 | 80.9 | 79.2 |
| standard | 1,235x659 | 12,628 | 49.7 | 43.8 | 67.8 | 84.9 | 69.6 |
| large | 1,606x857 | 21,400 | 78.1 | 77.6 | 86.8 | 90.0 | 89.0 |
| huge | 2,223x1,186 | 40,996 | 158.5 | 156.5 | 181.5 | 190.5 | 190.1 |
| giant | 3,211x1,713 | 85,814 | 349.7 | 345.8 | 419.3 | 453.5 | 442.7 |

The equal-size-weighted aggregate across all 200 policy starts was 134.4 ms
mean, 78.3 ms p50, 359.2 ms p95, and 453.5 ms max. Small-map tail values are
CPU-contention artifacts: their unloaded pilot was about 28 ms, while sixteen
policies were intentionally competing during the measured batch.

### Mean component cost

| map size | decode | base WorldMap | erosion | cover | 2x Dijkstra | Dijkstra share |
|---|---:|---:|---:|---:|---:|---:|
| small | 1.3 | 5.0 | 4.8 | 0.08 | 29.9 | 82.4% |
| standard | 1.7 | 6.5 | 6.3 | 0.10 | 41.4 | 83.4% |
| large | 2.4 | 9.2 | 9.0 | 0.10 | 66.5 | 85.1% |
| huge | 5.0 | 19.5 | 19.1 | 0.12 | 134.0 | 84.6% |
| giant | 10.4 | 53.4 | 52.5 | 0.18 | 286.0 | 81.8% |

`base WorldMap` includes erosion, cover, and small allocation/bookkeeping costs;
it is not additive with the erosion and cover columns.

## Decision

Keep the current online construction. Even the worst stressed giant startup is
under half a second, with no recurring tax after the flow fields are cached.
If startup latency later becomes observable in hosted episodes, optimize or
replace the pure-Python heap Dijkstra first; do not spend time on decompression,
cover extraction, or tactical-anchor derivation.
