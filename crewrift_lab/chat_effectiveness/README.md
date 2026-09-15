# chat_effectiveness — field-wide chat accuracy & effectiveness study

Observational, not causal — no randomized intervention on who accuses whom.

## Pipeline

**Pulling the data itself** (resolving a pinned roster, splitting a big ask
across the 100-episode/request cap, expanding replays, building a bounded
historical subset) is the repeatable part of this study, not just its
one-off analysis code — that process is packaged as the
[`crewrift-field-study`](../.claude/skills/crewrift-field-study/SKILL.md)
skill, with `tools/resolve_champion_roster.py`, `tools/expand_episodes.py`,
and `tools/build_historical_subset.py` (below) as its durable scripts.

## Files

- `tools/episode_outcomes.py` — per-slot policy identity/role/win from
  `episode.json` + `results.json`.
- `tools/extract_accusations.py` — same-meeting accusation/vote/eject rows
  for every speaker (crew and imposter), via `suspicion_lab`'s
  `chat_stances()`/`replay_parse.py` (read-only reuse).
- `tools/metrics.py` — crew accuracy, same-meeting effectiveness,
  seat-normalized win-rate association tables.
- `tools/validate_detector.py` — regex-vs-LLM agreement, using the
  event-warehouse's existing `suss` job as the LLM ground truth. Remaps
  `episode.json`'s internal `id` to this package's directory-stem join key
  before joining (the warehouse keys `chat_suss` by that internal id, not
  the stem — see `build_episode_id_map`).
- `tools/build_report.py` — static HTML report (plain f-strings, matching
  `crewrift-survey`'s pattern).
- `tools/resolve_champion_roster.py` — resolves the current top-N champions'
  exact `policy_ref` labels and writes a pinned-roster experience-request
  body, sidestepping the `top_n`/`random` selectors' server-side 500.
- `tools/expand_episodes.py` — expands a whole downloaded episode batch
  with a version-matched `expand_replay` binary, reporting a per-episode
  failure count (version/button skew tell).
- `tools/build_historical_subset.py` — symlinks a bounded, verified
  (results.json + matching expanded replay present) subset out of an
  existing scraped corpus, for a historical cross-check.
