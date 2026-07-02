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

> **Expander gotcha:** the JSONL emitter (`--format jsonl`) only exists from ref
> `42fed21` on, but that ref may hash-fail on the *current* game. You need a binary that
> is **both** JSONL-capable **and** matches the live game hash — build via
> `crewrift_lab/tools/build_expand_replay.sh`, verify one replay expands `ok`, and drop it
> at `crewrift_lab/tools/bin/expand_replay-<ref>`. A stale committed binary for the current
> game ref may be *pre-JSONL* (fails with "Unknown option: --format") — check before a run.
>
> Rows are **crewborg-POV only** (its own vantage — correct per suspicion-learning.md §9),
> so fewer rows than the offline all-observers dataset, but parity-correct by construction.
> The `nightly_refit.sh` re-enable (`NIGHTLY_REFIT_ENABLED=1`) waits on this path landing.

## The nightly champion loop (cron)

`tools/nightly_refit.sh` runs the whole pipeline unattended (user crontab,
`30 0 * * *`): scrape → expand → dataset → fit → **gates** (CV AUC ≥ 0.70,
corpus ≥ 500 games, full crewborg test suite, local Gate-1 smoke — any failure
aborts with the current champion untouched) → vendor weights → build → upload →
**submit** (James's standing instruction, 2026-06-12) → version-log line + commit.
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

## Current state (2026-07-02, v4 — the runtime-feature refit)

**The train→serve gap is closed and measured.** No pre-v90 upload ever carried
`CREWBORG_TRACE_SUSPICION_FEATURES=1` (`TRACE_GROUPS=all` does NOT imply it), so the
runtime path first ran on `crewborg:v90` (v89 code + the flag, now part of the standing
upload recipe). Data: 3×100-ep prime xreqs → **2,220 live-traced rows / 205 crew-POV
episodes / 398 meetings** (`models/runtime-v90/`). Live calibration of the OLD (v3,
offline-fit) weights at scale (6,258 degraded-snapshot rows, v82–v90): **AUC 0.59–0.61
live** (vs 0.812 offline-held-out) and **58–66% precision at the P≥0.9 vote gate** —
the offline eval's 94% never existed at serve. The v4 refit on live features:
**held-out AUC 0.671; precision at P≥0.9 = 98%** (n=65, essentially witnessed-grade
only), P≥0.7+lead≥0.2 = 94–97% at 0.16 votes/decision. Non-witnessed AUC 0.553→0.638 —
the remaining ceiling is **detector-side, not weight-side**: live single-cue AUCs are
0.42–0.55 for everything, and `reported_bodies`/`button_calls_made` were **all-zero
across 398 live meetings** (the runtime caller-attribution parse never fires at serve —
an open bug worth fixing before the next refit). Weights vendored; A/B pending.

`build_dataset_runtime.py` now takes repeatable `--policy`/`--version` (omit version to
accept any) and `--allow-degraded` (reconstructs the 7 mechanically-recoverable features
from pre-v90 snapshots' event summaries; rows marked `features_degraded=1` — never fit
the full runtime feature set on those rows).

## Prior state (2026-06-12, v3 — superseded; kept for the numbers' provenance)

Full-corpus fit on **1,857 games / 196k rows**: **runtime model AUC 0.812 — the
full-feature ceiling**. The `strategy/social_evidence.py` detectors (watched task
completions via the `crew_tasks_remaining` decrement + dwell gate, chat stances,
attributed vote dots) plus the MeetingCall-interstitial caller parse
(`reported_bodies`/`button_calls_made`) make every offline feature
runtime-observable. Held-out decision sim @ P≥0.9: 0.20
votes/decision at **94% imposter precision** (live hand model: 42%), net +17.3/100
vs always-skip. `tasks_completed_watched` is the single strongest weight (−10.9;
imposters produced ZERO across 62k labelled rows). Weights vendored at
`crewrift/crewborg/data/suspicion_weights.json`; every cue's direction was stable
from the 341-game interim fit to the full corpus. Next: Gate-1 smoke → 2-imp A/B
(crew win + votes-at-crew rate) → Gate-2.
