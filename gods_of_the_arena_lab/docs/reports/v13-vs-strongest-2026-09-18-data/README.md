# Replay comparison data

Companion to `../v13-vs-strongest-2026-09-18.html` and `.md`.

- `all-seats.csv`: 2,880 exact seat results from 288 unique archived games. `xp` is lifetime internal game XP; rates are XP per 1,000 elapsed simulation ticks (24 ticks/second). `win` is the engine's binary team outcome. Every game contains exactly one immutable james-botts-gota:v13.
- `all-policies.csv`: separate exact policy versions. `*_standardized` is the equal-weight mean of ten hero-class means, not the raw roster-weighted mean. Blank standardized values indicate missing classes. Small class samples make secondary rankings unstable.
- `timing-and-uncertainty.json`: 2,000 whole-match bootstrap draws, class sample counts, and fixed six-minute-cohort timing. Confidence intervals describe this historical cohort; they do not establish an improvement from copying behavior.
- `proximity-by-class.json`: death-event denominators and per-class proximity/conversion. Proximity is within 12 tiles immediately before death, subject alive. Tiny ambiguous killer counts remain in denominators as non-own kills.
- `sample-manifest.json`: the deterministic 40-match behavior sample and original artifact paths. Two-second state snapshots and reproducible scripts remain in `../../../.reports-working/v13-vs-strongest-2026-09-18/` (canonical path: `gods_of_the_arena_lab/.reports-working/v13-vs-strongest-2026-09-18/`).

Archived matches were created 2026-09-17 22:28:36–23:54:24 UTC. The live leaderboard snapshot was retrieved 2026-09-18 17:33:24 UTC. Engine revision: f2ab9598d8f8001b6beae3e66404e341770c803f; report checkout: 7a1d1bfc85084206f9cb0c87170912b87f44f121, with existing local changes preserved.
