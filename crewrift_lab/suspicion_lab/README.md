# suspicion_lab — fitting crewborg's suspicion model from scraped replays

The data-science half of the suspicion system: scrape league games, expand their
replays into observer-exact evidence, fit the evidence weights against ground-truth
roles, and emit a weights file for the agent to load. **The design (read first):**
[`../crewrift/crewborg/docs/designs/suspicion-learning.md`](../crewrift/crewborg/docs/designs/suspicion-learning.md).
The runtime model it feeds: [`suspicion.md`](../crewrift/crewborg/docs/designs/suspicion.md).

## Pipeline (each stage idempotent; re-run any time)

```sh
# A. scrape completed league rounds (replay + results per episode) into corpus/
uv run python crewrift_lab/suspicion_lab/tools/scrape_corpus.py --max-rounds 12

# B. expand replays -> expanded/<episode>.jsonl.gz (needs tools/bin/expand_replay-<ref>;
#    build via crewrift_lab/tools/build_expand_replay.sh --ref 42fed21)
uv run python crewrift_lab/suspicion_lab/tools/expand_corpus.py --workers 8

# C. per-(observer, suspect, meeting) feature rows + labels -> dataset/dataset.parquet
uv run python crewrift_lab/suspicion_lab/tools/build_dataset.py

# D. fit weights (L1 logistic regression, game-grouped CV) -> models/<tag>/
uv run python crewrift_lab/suspicion_lab/tools/fit.py --tag <tag> --features runtime
#    --features full  = the research ceiling (every offline feature)
#    --features runtime = only what crewborg's current event log can compute (SHIP THIS)

# E. decision-level eval: vote policies vs the always-skip baseline
uv run python crewrift_lab/suspicion_lab/tools/eval.py --model crewrift_lab/suspicion_lab/models/<tag>
```

`corpus/`, `expanded/`, and `dataset/` are gitignored data (rebuildable);
`models/<tag>/suspicion_weights.json` is committed — it is the deliverable the
agent vendors.

## Files

- `tools/scrape_corpus.py` — round-ledgered incremental scraper (wraps the
  episode-artifacts fetcher).
- `tools/expand_corpus.py` — version-matched `expand_replay --format jsonl
  --snapshot-every 24` over the corpus; `_manifest.json` records per-episode
  status (`hash_failed` = that episode came from a different game build).
- `tools/replay_parse.py` — expanded JSONL → typed `Game` (players/roles, sampled
  states, visibility intervals, kills/bodies/ejections, meetings, chats).
  NB: `player_manifest` roles are join-time (always "crew"); roles are taken from
  `player_state` rows.
- `tools/features.py` — the evidence catalogue: cumulative, visibility-clipped,
  instance-summed per-(observer, suspect) features + chat stance triples
  (design §5/§10). Every feature must stay runtime-admissible.
- `tools/build_dataset.py` — rows + the per-cue imposter/crew sanity report.
- `tools/fit.py` — the model + the transform contract (`BIN_SPEC`, `LINEAR_CLIP`)
  that ships inside `suspicion_weights.json` and is mirrored by the runtime scorer.
- `tools/eval.py` — held-out (out-of-fold) meeting decisions through a vote-policy
  grid; ship only what beats always-skip on net parity (design §6).

## Current state (2026-06-12)

First interim fit on 341 games / 35k rows: full model CV AUC 0.811 (calibrated);
runtime-subset AUC 0.739. Decision sim: runtime-subset at P≥0.9 votes 0.11/decision
with 88% imposter precision (live hand model: 42%), net +8.3/100 vs always-skip.
Biggest fitted facts: `tasks_completed_watched` is a near-perfect exculpation
(−9.0; needs a new runtime perception detector — the top integration priority),
`follow_death` is the strongest graded cue, `accusations_made` is incriminating
(+1.1), and `tailing` is ~10× weaker than the hand model assumed. Corpus scrape was
mid-flight; refit on the full corpus before shipping.
