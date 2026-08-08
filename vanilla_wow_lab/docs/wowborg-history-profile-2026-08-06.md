# Wowborg historical replay profile — 2026-08-06

## Decision summary

Wowborg's current Traverse failure is concentrated in the opening Tanaris corridor, not
distributed across the route. In the 113 unique playable replays from versions 63–78:

- 121 deaths occurred; 107/113 runs ended as ghosts and 60.9% of all observed time was in
  ghost form (163,409 seconds, 45.4 hours).
- 106/121 deaths (87.6%) fell in four adjacent 100-yard cells along y≈-2500, from x≈-9100 to
  x≈-8800. The same cells contain 304,429/343,566 incoming damage (88.6%).
- Glasshide Petrifiers dealt 237,779 damage (69.2%), followed by Rabid Blisterpaws (53,332)
  and Scorpid Dunestalkers (30,515).
- 111/113 runs sent no attack packet. Only v73 dealt damage (7,825); it survived but moved
  only 417 yards north and scored 408.57. Combat is effectively absent in every productive
  route trial.
- Explicit Stuck handling fired 155 times in 120 clustered episodes, covering 1,068.82
  non-overlapping seconds. Those stuck cells strongly overlap the opening death cells.
- Recovery always released spirit after death (121/121), but repeated corpse-reclaim controls
  did not produce durable recovery: 107 runs still ended ghosted. No spirit-healer control or
  resurrection response was recorded.

The next improvement should therefore target survival through the opening hostile corridor
and reliable post-death recovery as separate hypotheses. Later route and Great Lift work is
not currently on the causal path in the repeated v78 evidence.

## Corpus and provenance

The corpus combines the 100 most recent ordinary-access `wowborg` policy replays with every
experience request ID recorded in `WORKING_CONTEXT.md`, `wowborg/VERSION_LOG.md`, and `TODO.md`.
The artifact downloader found 28 request replays; failed and cancelled jobs usually exposed
no replay. One v78 request replay also appeared in the policy feed and was removed by exact
SHA-256 deduplication.

| Coverage | Count |
| --- | ---: |
| Replay files discovered | 130 |
| Exact duplicates removed | 1 |
| Unique playable replays | 129 |
| Current Tanaris Traverse family, v63–v78 | 113 |
| Earlier Durotar-era trials, v47–v61 | 16 |

The current-family analysis includes 96 v63 replays and 17 later trials. Versions 65, 68,
and 76 have no playable replay in the recorded requests. Policy logs and results artifacts
were not exposed at ordinary permissions; the figures here come from the retained wire
replays plus adjacent episode metadata. The canonical owner reducer was run from clean commit
`649bb31d69c98188f958fec676a66ee06b5ffa97`.

## Current-family hotspots

Coordinates below are centroids within 100-yard map cells. The likely killing source is the
last incoming-damage source observed within 15 seconds before death, so source attribution is
an inference; death time and location are direct replay state.

| Death cell | Deaths | Principal inferred killers |
| --- | ---: | --- |
| (-9094.5, -2531.5, 17.9) | 65 | Glasshide Petrifier (65) |
| (-9015.2, -2529.0, 17.6) | 25 | Glasshide Petrifier (14), Scorpid Dunestalker (10) |
| (-8886.3, -2516.3, 13.6) | 9 | Rabid Blisterpaw (6), Glasshide Petrifier (2) |
| (-8834.5, -2510.9, 11.4) | 7 | Rabid Blisterpaw (6), Glasshide Gazer (1) |

The Stuck clustering independently lands on the same corridor:

| Stuck cell | Episodes | Calls | Retry-window seconds |
| --- | ---: | ---: | ---: |
| (-9095.7, -2530.9, 17.8) | 70 | 75 | 566.8 |
| (-9014.1, -2527.9, 17.4) | 22 | 22 | 151.2 |
| (-8884.6, -2522.8, 13.3) | 10 | 10 | 72.4 |
| (-9302.7, -2666.5, 9.4) | 5 | 30 | 180.2 |

`stuck_union_seconds` merges overlapping retry windows per replay. It is intentionally not a
claim that every stationary second was a navigation failure. Quiet stalls remain visible via
`longest_stationary_interval`.

## Version comparison

| Version | Runs | Deaths | Ended ghost | Ghost time | Stuck episodes / union s | Damage in / out |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 63 | 96 | 97 | 95 | 60.6% | 98 / 777.23 | 273,134 / 0 |
| 64 | 1 | 3 | 1 | 74.5% | 0 / 0 | 7,623 / 0 |
| 66–71 | 5 | 11 | 1 | 72.6% combined | 7 / 2.8 | 30,938 / 0 |
| 72 | 1 | 1 | 1 | 34.2% | 1 / 6.5 | 2,757 / 0 |
| 73 | 1 | 0 | 0 | 0% | 0 / 0 | 3,811 / 7,825 |
| 74–77 | 3 | 3 | 3 | 55.9% combined | 3 / 42.03 | 8,488 / 0 |
| 78 | 6 | 6 | 6 | 70.5% | 11 / 240.26 | 16,815 / 0 |

v78 is repeated evidence, not a one-off bad seed: all six runs died once and ended ghosted.
Four deaths cluster around (-9108, -2547), one at (-9036, -2571), and one at
(-9308, -2682); all six have a Glasshide Petrifier as their final damage source. Scores range
from 1,095.77 to 1,304.14. The region-level static envelope audit that predicted zero contacts
did not predict hosted behavior and should not be used as a survival gate without accounting
for hostile movement and actual replay trajectories.

## Magic, forms, and recovery

The batch contains only four requested spell IDs: Stuck (7355) 445 times, Travel Form (783)
16 times, Prowl rank 1 (5215) nine times, and Cat Form (768) six times. Every recorded form
request reached a corresponding spell effect, but the current owner report does not summarize
continuous form uptime. Ghost aura/effect 8326 occurred once per death. There is no evidence
of offensive spell use.

The repeated v78 sequence is: Travel Form succeeds, incoming combat begins in the opening
corridor, the character deals no damage, death occurs, Release Spirit and corpse-reclaim
controls appear, and the run ends ghosted. This makes recovery observability actionable now:
the controls are emitted, but the outcome is ineffective.

## Reproduce

Download artifacts without elevated access, then run:

```bash
uv run python vanilla_wow_lab/tools/wow_batch_profiler.py \
  /path/to/policy-artifacts /path/to/request-artifacts \
  --owner-repo /path/to/current/coworld-vanilla-wow \
  --json-out /tmp/wowborg-history-profile.json
```

The JSON records corpus coverage and duplicates, aggregate and per-version summaries, and
per-replay damage, death, stuck, recovery, spell, form, and provenance evidence. Raw replays
and the generated report remain runtime artifacts and are not checked into the lab.
