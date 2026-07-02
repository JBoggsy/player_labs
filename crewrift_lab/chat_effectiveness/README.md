# chat_effectiveness — field-wide chat accuracy & effectiveness study

Answers two questions about Crewrift Prime chat, field-wide (every
player/policy, not just crewborg): (1) how accurate are crew accusations
vs. ground-truth imposter identity, and (2) how effective are accusations
(crew + imposter) at moving votes/ejections and correlating with
seat-normalized win rate. Design:
[`../docs/designs/2026-07-02-chat-accuracy-effectiveness-design.md`](../docs/designs/2026-07-02-chat-accuracy-effectiveness-design.md).

Observational, not causal — no randomized intervention on who accuses whom.

## Pipeline

    uv run python tools/episode_outcomes.py --episodes <dir of episode dirs> --out data/outcomes.parquet
    uv run python tools/extract_accusations.py --expanded <dir of expanded jsonl> --out data/accusations.parquet
    uv run python tools/metrics.py --accusations data/accusations.parquet --outcomes data/outcomes.parquet --out-dir data/metrics
    uv run python tools/validate_detector.py --expanded <expanded dir> --chat-suss <warehouse>/events/key=chat_suss/chat_suss.parquet --episodes <dir of episode dirs> --out data/validation.json
    uv run python tools/build_report.py --meta data/meta.json --validation data/validation.json --metrics-dir data/metrics --out data/report.html

`data/` is gitignored (rebuildable from a fresh pull + the historical
suspicion_lab corpus); the report and any durable findings get written up
in `crewrift_lab/TENTATIVE_LESSONS.md` per this lab's living-docs
discipline. The persisted, human-readable write-up lives at
[`../crewrift/crewborg/docs/reports/2026-07-02-chat-accuracy-effectiveness.html`](../crewrift/crewborg/docs/reports/2026-07-02-chat-accuracy-effectiveness.html).

**Pulling the data itself** (resolving a pinned roster, splitting a big ask
across the 100-episode/request cap, expanding replays, building a bounded
historical subset) is the repeatable part of this study, not just its
one-off analysis code — that process is packaged as the
[`crewrift-field-study`](../.claude/skills/crewrift-field-study/SKILL.md)
skill, with `tools/resolve_champion_roster.py`, `tools/expand_episodes.py`,
and `tools/build_historical_subset.py` (below) as its durable scripts.

## 2026-07-02 run

- **Fresh pull:** 200 episodes (2 xreqs of 100, pinned to the current
  top-8 Prime champions by score, natural roles, rotating seats — a
  `top_n`-based request hit a server-side query timeout, so explicit
  `policy_ref`s were used instead). Coworld `crewrift_prime` v0.4.31→v0.4.32.
  Expander `/tmp/expand-043` (master-sim `26ee08c`) verified clean: 0
  hash-fails across all 200 replays, and the built warehouse reported zero
  `trace_warning` episodes.
- **Historical cross-check:** 2,976 episodes from the existing
  `suspicion_lab/corpus` (June 12–13 batch — the only slice with intact
  `results.json`; the most recent scraped batch, June 25, only has
  `episode.json` and could not be used).
- **Detector validation:** regex vs. the warehouse's LLM-based `suss` job
  on all 200 fresh episodes' chat — 97.5% stance agreement, 87.7% target
  agreement (n=200 matched). A manual spot-check of 10 accusation rows
  found 9/10 clearly correct; the one miss was a multi-color sentence
  ("Blue dead... Pink sus: no alibi") where the regex's
  first-color-mentioned heuristic picked the wrong target — a known,
  now-quantified limitation, not a new bug.
- **Bugs found and fixed along the way:** the event-warehouse's `chat_suss`
  keys episodes by `episode.json`'s internal `id`, not this pipeline's
  directory-stem convention (would have silently zeroed the detector
  validation); and `replay_parse.py`'s per-meeting `Meeting.ejected_slot`
  is never actually set (a same-tick event-ordering bug — caught via a
  suspicious flat 0.0% ejection rate across every row). Both are recorded
  in `crewrift_lab/TENTATIVE_LESSONS.md`.

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
