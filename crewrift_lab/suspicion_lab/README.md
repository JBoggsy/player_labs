# suspicion_lab — fitting crewborg's suspicion model from scraped replays

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

## Runtime-feature dataset — the train→serve-gap rework

Stage C (`build_dataset.py`) reconstructs features *offline* from expanded replays,
so even `fit --features runtime` fits on offline-reconstructed values that **diverge
from what crewborg actually computes at serve time** (the train→serve gap — refits
churned versions without moving outcomes). `tools/build_dataset_runtime.py` fixes
this: it reads crewborg's **own** traced feature vectors —
`domain.suspicion_snapshot.ranking[].features`, emitted per meeting when the policy
runs with `CREWBORG_TRACE_SUSPICION_FEATURES=1` (+ `CREWBORG_TRACE_GROUPS=suspicion`)
— and labels each (crewborg-observer, suspect, meeting) row from the expanded replay's
`player_manifest`. It emits the **same parquet schema**, so `fit.py --features runtime`
and `eval.py` consume it unchanged.

```sh
# 1. run a trace-enabled crewborg (build+upload with the two env vars above),
#    play a few hundred tournament episodes, fetch with replays + artifacts.
# 2. expand the replays (for labels); the runtime path only needs player_manifest.
uv run python crewrift_lab/suspicion_lab/tools/expand_corpus.py --corpus <eps> --ref <ref> --out <expanded>
# 3. join traced features to labels:
uv run python crewrift_lab/suspicion_lab/tools/build_dataset_runtime.py \
    --expanded <expanded> --artifacts <eps> --policy crewborg --version <N> --out dataset/runtime.parquet
# 4. fit / eval as normal:
uv run python crewrift_lab/suspicion_lab/tools/fit.py  --dataset dataset/runtime.parquet --features runtime --tag runtime-vN
uv run python crewrift_lab/suspicion_lab/tools/eval.py --model models/runtime-vN
```

## The nightly champion loop (cron)

`tools/nightly_refit.sh` runs the whole pipeline unattended (user crontab,
`30 0 * * *`): scrape → expand → dataset → fit → **gates** (CV AUC ≥ 0.70,
corpus ≥ 500 games, full crewborg test suite, local Gate-1 smoke — any failure
aborts with the current champion untouched) → vendor weights → build → upload →
Submit only with explicit authorization for the selected league action.
Logs: `logs/nightly-<date>.log`. `--check` verifies prerequisites (uv, docker
daemon, softmax auth). Caveats: cron skips a night if the machine is asleep at
00:30, and an expired `softmax login` token aborts the run (re-login fixes the
next night).

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
