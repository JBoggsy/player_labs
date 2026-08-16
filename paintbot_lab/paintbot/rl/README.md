# Paintbot RL policy

This directory is the separate experimental policy track alongside Stencil.
The initial policy is behavior cloning over historical high-performing agents:
a pretrained causal language model consumes semantic Sprite-v1 entities, a
cached walkability-map representation, and the previous action. It predicts
four grammar-constrained action tokens followed by `<STOP>`.

The living architecture and decision record is
[`../../docs/designs/rl-policy.md`](../../docs/designs/rl-policy.md).

## Implemented pipeline

The implementation now covers the complete replay-to-checkpoint path:

- `actions.py` defines the 16-token factorized action vocabulary, `<STOP>`,
  canonical raw-mask conversion, and the previous-mask-aware wire decoder.
- `episode_map.py` decodes, hashes, bit-packs, and restores the exact static
  walkability raster once per episode.
- `capture_wire_observations.py` records replay ticks and can write the episode
  map separately with `--map-out`.
- `extract_replay_actions.nim` extracts one POV's raw held-mask changes from an
  exact-version replay; `dataset.py` and `build_sft_dataset.py` align those with
  observations.
- `build_temporal_experiment.py` derives matched uniform/transition and
  current/history corpora. Four-tick histories store bounded bot-semantic
  entity deltas and prior actions at offsets `-4` through `-1` only.
- `pipeline.py` downloads declared episodes with the shared artifact tool,
  creates exact-source worktrees, compiles both extractors against each pinned
  revision, validates replay hashes and expert rewards, and writes balanced,
  replay-disjoint train/validation/test corpora with complete provenance.
- `modeling.py` prepends 16 global plus 16 current-position map tokens to Qwen,
  constrains generation by action slot, and provides LoRA/full-tuning loading.
- `training.py` provides Accelerate training, cosine scheduling, validation,
  best/final checkpoints, and resumable optimizer/model/RNG state; `policy.py`
  is the Sprite-v1 inference shell with opt-in per-decision activation tracing.
- `pipeline_manifest.py` is the validated manifest contract a run is declared
  against — episode IDs, source commits, reward-qualified POVs, split sizes.
  `discover_expert_replays.py` populates it by finding and manifesting every
  replay-bearing CTF/Paintbot expert episode.
- `shard_expert_manifest.py`, `prepare_expert_corpus.py`, and
  `merge_prepared_shards.py` turn that catalog into a coverage-balanced,
  resumable multi-process corpus without allowing a replay into two splits.
- `corpus_store.py` opens nested, memory-mapped Hugging Face Datasets Arrow
  shards as one virtual dataset and builds finite balanced training indices.
- `run_expert_training.py` waits for preparation, builds Arrow plus indices,
  runs and evaluates a GPU canary, then launches resumable full training and
  frozen-validation evaluation. It never opens the sealed test.
- `assemble_corpus.py` deduplicates maps and samples a balanced cross-era corpus
  from what the pipeline extracted.
- `train_sft.py` is the CLI entry point that fine-tunes a run end to end (the
  `training.py`/`modeling.py` machinery is the library beneath it);
  `evaluate_sft.py` scores a checkpoint against an explicitly supplied split.
- `measure_action_alignment.py` measures which replay action tick explains each
  observed aim transition — the instrument that settled zero-tick alignment.
  `measure_observation_lengths.py` is the corresponding token-length instrument.

Install the optional training stack separately from the existing player labs:

```sh
uv sync --group rl
```

### Large expert corpus

`configs/expert-replay-discovery-v1.json` is the canonical identity map for the
nine requested expert accounts. Discovery queries CTF and Paintbot separately,
then deduplicates shared episodes globally and records the exact expert policy
version IDs present in each replay. This prevents preprocessing from silently
choosing a higher-reward non-expert seat.

The August 7, 2026 exhaustive scan found 333,253 unique episodes. Of those,
327,188 have immutable source commits and form the reproducible corpus: 271,590
CTF and 55,598 Paintbot episodes, containing 584,873 selected expert-policy
trajectories across 35 recorded GameVersions spanning 1–41. The other 6,065 are
retained in discovery provenance but excluded because their Coworld source URLs
pointed at mutable `main`, so exact historical reconstruction is impossible.

```sh
CATALOG=paintbot_lab/paintbot/rl/data/runs/expert-replay-pool-v1
CONFIG=paintbot_lab/paintbot/rl/configs/expert-replay-discovery-v1.json
CORPUS=paintbot_lab/paintbot/rl/data/runs/expert-corpus-v1

uv run python paintbot_lab/paintbot/rl/discover_expert_replays.py \
  --config "$CONFIG" --workspace "$CATALOG" --workers 4

uv run python paintbot_lab/paintbot/rl/prepare_expert_corpus.py \
  --manifest "$CATALOG/expert-replay-pool-v1.json" \
  --workspace "$CORPUS" --shards 8 --workers 8
```

With no `--max-episodes`, the preparation command includes the entire
discoverable catalog. A bounded run uses coverage-balanced round-robin selection
across expert, world, and GameVersion before sharding. Each shard resumes at the
trajectory level, and rerunning the launcher skips completed shards. Generated
wire/action/observation intermediates are removed after durable samples and maps
are written. In large unbalanced runs, each worker groups 512 trajectories at a
time, converts that bounded group to a verified Arrow part, then deletes only
the corresponding sample JSON. The global merge writes a small virtual-dataset
manifest over those parts rather than copying their payloads. Maps are
content-deduplicated once and hard-linked across splits. Raw replays,
exact-source extractors, Arrow parts, and per-trajectory/per-shard provenance
remain; no full merged sample JSONL is created.

Production-scale training uses the disk-backed handoff rather than passing the
full JSONL corpus directly to `train_sft.py`. The conservative first run uses
250,000 distinct examples per epoch for three epochs, 10,000-example
validation/test subsets, LoRA at 2e-4, BF16, and four-tick history. Each index
is balanced 50/50 between changed and held actions, then across GameVersion,
expert identity, and CTF/Paintbot world. These are initial experiment settings,
not claims that the budget or balance is optimal.

```sh
uv run python paintbot_lab/paintbot/rl/run_expert_training.py \
  --manifest "$CATALOG/expert-replay-pool-v1.json" \
  --workspace "$CORPUS" \
  --output "$CORPUS/training-v1"
```

`training-v1/status.json` is the machine-readable state. The launcher skips
completed stages and resumes full training from the newest valid state. It
runs a 1,024-example GPU canary first and starts full training immediately when
the canary and its validation evaluation complete. Full training checkpoints
every 1,000 optimizer updates and retains the newest two step checkpoints plus
each completed epoch. The unattended launcher evaluates the selected checkpoint
on frozen validation and then stops. The sealed test can only be opened through
the guarded final-gate workflow below after validation exceeds 70%.

`supervise_expert_training.sh` retries a failed handoff after 60 seconds;
it also raises the open-file soft limit for the many memory-mapped Arrow parts.
`paintbot-rl-training.service` is the checked-in mettabox1 user-unit definition.
On the current host, that supervisor is detached and an `@reboot` crontab entry
provides reboot recovery because the `metta` account does not have systemd
lingering enabled. The enabled user unit is a secondary login-time recovery
path; the shared lock prevents concurrent launchers.

### Training dashboard

`training_dashboard.py` serves a read-only, dependency-free view of the active
run: microbatch/epoch progress and ETA, recent and validation loss, checkpoints,
GPU utilization/VRAM/temperature, disk headroom, process health, recent errors,
and detailed action metrics plus the replay-cluster confidence interval once
evaluation files exist. It binds to remote
localhost and is reached through SSH rather than exposing a network service.

From the repository root on a Mac, deploy/restart the dashboard, establish the
SSH tunnel, and open it with:

```sh
paintbot_lab/paintbot/rl/open_training_dashboard.sh
```

The default URL is `http://127.0.0.1:8876`; if that port is occupied by another
dashboard, the launcher chooses the next free port. Override the starting local
port with `PAINTBOT_DASHBOARD_LOCAL_PORT`; the launcher otherwise uses the
existing `mettabox1` SSH alias and exhaustive-corpus workspace.

The unattended accuracy queue retargets the remote dashboard from diversity to
the event-action screen, and then to spatial semantics if no completed arm has
exceeded 70% on frozen autoregressive validation. Passing the event screen but
finishing below the target does not stop the independent spatial experiment.
If both single-factor arms pass their screens and complete below 70%, the queue
fills the preregistered 2x2 interaction cell by training event outputs with
spatial-semantic inputs. A rejected single-factor screen suppresses that
combination.
After diversity finishes, the queue also evaluates the original baseline
checkpoint autoregressively on the same frozen validation index, providing a
like-for-like diagnostic without opening the test. The SSH tunnel and local
`8876` URL remain unchanged across those handoffs.

Confirmation selection is also unattended and fixed before results. The first
eligible arm in queue order—diversity, event actions, spatial semantics, then
the eligible interaction—that reports strictly more than 70% autoregressive
exact action on frozen validation is sent once through
`evaluate_sealed_candidate.py`. The queue then stops regardless of confirmation
pass or failure; it never evaluates a second candidate on the same holdout. If
no arm clears validation, the holdout remains unopened. An interrupted process
may verify and finish the decision for an already-written result, but it never
runs model inference on the confirmation rows twice.

To follow a non-default experiment while retaining the same dashboard URL, set
the remote output and log explicitly:

```sh
PAINTBOT_DASHBOARD_TRAINING_ROOT=/home/metta/paintbot_rl_training_20260807/runs/expert-corpus-v1/training-v2-diversity \
PAINTBOT_DASHBOARD_TRAINING_LOG=/home/metta/paintbot_rl_training_20260807/logs/diversity-750k.log \
  paintbot_lab/paintbot/rl/open_training_dashboard.sh
```

### Matched-compute diversity arm

`run_diversity_experiment.py` compares the original 250,000 unique rows x three
epochs against 750,000 unique rows x one epoch. Total example presentations and
optimizer updates remain fixed. The runner writes a separate balanced index,
trains and resumes under `training-v2-diversity`, evaluates validation, and
deliberately stops before the sealed test. `supervise_diversity_experiment.sh`
provides retry and reboot recovery on mettabox1. The baseline diagnosis and
frozen checksums are recorded in the
[`exhaustive-corpus report`](../../docs/reports/rl-exhaustive-baseline-2026-08-14.md).

### Full run

The tracked GPU-oriented manifest uses winning POVs from GV16/24/30/35 for
training and replay-disjoint validation, then holds out GV40 as a complete
unseen era:

```sh
MANIFEST=paintbot_lab/paintbot/rl/configs/historical-cross-era-v1.json
RUN=paintbot_lab/paintbot/rl/data/runs/historical-cross-era-v1

# Requires `softmax login`. Add --elevated when reading other owners' episodes.
uv run python paintbot_lab/paintbot/rl/pipeline.py download \
  --manifest "$MANIFEST" --workspace "$RUN" --elevated
uv run python paintbot_lab/paintbot/rl/pipeline.py prepare \
  --manifest "$MANIFEST" --workspace "$RUN"
uv run python paintbot_lab/paintbot/rl/pipeline.py bundle \
  --manifest "$MANIFEST" --workspace "$RUN" \
  --bundle-out "$RUN.dataset.tar.gz"
```

Copy the repository plus the dataset bundle to the GPU host, extract the bundle
at the run root, and install the locked training group. No CUDA-specific code or
Accelerate config is required for one GPU:

```sh
uv sync --frozen --group rl
uv run python paintbot_lab/paintbot/rl/pipeline.py train \
  --manifest "$MANIFEST" --workspace "$RUN"
uv run python paintbot_lab/paintbot/rl/pipeline.py evaluate \
  --manifest "$MANIFEST" --workspace "$RUN"
```

Resume after a preemption from a step or epoch directory under
`checkpoint/trainer_state/` with `--resume-from`. Mid-epoch checkpoints use a
deterministic epoch permutation, so completed batches can be skipped without
changing the remaining order. The final model is in
`checkpoint/`, the lowest-validation-loss copy is in `checkpoint/best/`, and
validation/test metrics are written alongside them. `provenance.json` records
every replay, source commit, selected seat/policy/reward, raw/retained entity
count, preparation setting, and split size.

`configs/local-smoke.json` is a deliberately tiny two-era plumbing test. It is
not evidence of policy quality. On Apple Silicon, use `mixed_precision: "no"`
and a 2,048-token ceiling for real experiments unless memory measurements justify
more. The initial 48 GB M4 Pro pass completed 125 examples in 9.2 minutes without
swapping; an uncheckpointed 2,684-token sample caused severe memory pressure.

The preparation stage persists the bot-semantic observation, not the rejected
human-renderer view. It removes only `fog`, `splatter ...`, `hit splat ...`, and
`damage pop ...`, retains unknown future labels, and keeps the walkability raster
in its deduplicated binary-map table. Each split is downsampled to its
least-populated era (subject to the configured cap), then round-robined across
complete trajectories so neither a recent era nor one long replay dominates.

The default observation-to-action delay is zero simulation ticks. It is recorded
in each sample as separate `observation_tick` and `action_tick` fields and can
be changed with `--action-delay-ticks`. A six-POV GV40 aim-transition
investigation selected zero ticks decisively; see the living design for results.

For live inference, set `PAINTBOT_RL_CHECKPOINT`. Set
`PAINTBOT_RL_TRACE=1` to emit generated tokens, mask transitions, and latency.
`evaluate_sft.py` reports autoregressive exact-action and per-slot accuracy
using the same feedback decoding as inference. It retains teacher-forced
`constrained_*` diagnostics for interpreting older artifacts and adds an
explicit teacher-forced exact-action alias. It also reports a held-action
persistence baseline plus accuracy restricted to examples where the expert
actually changed the button state. The latter two are required:
aggregate accuracy can otherwise reward simply copying the previous mask.
Both absolute and event decoders prefill the observation once, then reuse
Qwen's KV cache for generated action tokens; this changes evaluation latency,
not token selection or the metric contract.

Training accepts `--action-change-weight <number|balanced>`. Numeric values
multiply loss only for movement/turn/fire/grenade targets whose state differs
from the prior tick. `balanced` derives `unchanged_components / changed_components`
from the training split; `<STOP>` remains weight 1. The first weighting sweep
showed that this mechanism creates transition recall but excessive false
changes, so it is an experiment knob rather than a new default.

`--action-encoding events` selects the residual press/release experiment. It
targets only changed buttons, in canonical release-then-press order, followed
by `<STOP>`; an unchanged mask targets `<STOP>` alone. The checkpoint records
the codec and live inference dispatches to the matching stateful decoder. Event
checkpoints retain the absolute action tokens as trainable prompt vocabulary so
`previous_action` has the same five-token representation under both codecs.
Every row reserves the worst-case nine-token event budget during truncation,
regardless of its true target length. `evaluate_event_sft.py` generates
autoregressively until `<STOP>` while enforcing the same release-before-press,
button-order grammar used by the targets. It decodes the result back to a
canonical held mask before reporting the selection exact-action and
per-component accuracy; teacher-forced event scores are diagnostics only. The
default remains `absolute`, so existing checkpoints and unattended runs retain
their original four-slot action language.

LoRA defaults to rank 8 over the attention Q/K/V/O projections. Capacity
experiments can set `--lora-rank` and choose
`--lora-target-modules attention|all-linear`; both resolved values are recorded
in `training_run.json`. The exhaustive-corpus all-linear canary fit in 24 GB but
regressed movement and validation loss, so attention-only remains the default.

`evaluate_sft.py --logits-out validation_logits.npz` persists only legal
per-slot logits plus replay IDs, prior tokens, and labels. The output is intended
for validation-only decoder diagnosis. `calibrate_change_bias.py` splits it by
replay ID, selects a single previous-state change bias on one half, and reports
the untouched confirmation half. Do not use this path to tune against sealed
test logits.

`evaluate_sealed_candidate.py` is the only supported final-gate command. It
refuses to run unless the candidate's validation JSON attests the frozen
validation-index SHA-256, Arrow dataset fingerprint, SHA-256 of the 10,000
selected semantic sample records, and validated map-set fingerprint. It must
contain exactly 10,000 rows and report strictly more than 70% autoregressive
exact action; teacher-forced exact action cannot satisfy this gate. The
validation artifact must also attest the exact checkpoint-tree SHA-256, action
codec, spatial representation, and 4,096-token budget. The guard independently
verifies the frozen test index and Arrow dataset, requires validation and test
to reference the same map-table file, checks the test evaluator's row and map
attestations and writes a separate sealed decision record. If inference wrote
the result but the process stopped before recording the decision, a retry
revalidates that same immutable artifact instead of repeating inference.
Every new autoregressive evaluation also reports a fixed replay-cluster BCa
bootstrap interval for exact-action accuracy: replay IDs are resampled as whole
clusters, with 9,999 resamples, 95% two-sided confidence, and seed `20260814`.
The sealed gate verifies that contract and records whether the interval's lower
bound clears 70%. This is uncertainty evidence, not another candidate-selection
threshold; the preregistered promotion metric remains exact-action point
accuracy strictly above 70%.
This keeps model selection on validation and makes the one-time test opening
auditable:

The legacy `indices/test.npy` was opened by the original teacher-forced
evaluator before this guard existed, so it is retired from final confirmation.
The gate instead requires `indices/test-confirmation.npy`, frozen before any
current-arm validation result with `freeze_confirmation_holdout.py`. The
replacement excludes every replay ID touched by the legacy index, contains one
row from each of 10,000 episode-seat trajectories (7,236 replays), and is
balanced 5,000/5,000 between changed and held actions. No model-selection or
diagnostic command reads it. Its immutable provenance is recorded in
`configs/confirmation-holdout-v1.json`.

The one-time deterministic freeze command was:

```sh
uv run python paintbot_lab/paintbot/rl/freeze_confirmation_holdout.py \
  --dataset runs/expert-corpus-v1/arrow/test \
  --contaminated-index runs/expert-corpus-v1/indices/test.npy \
  --out runs/expert-corpus-v1/indices/test-confirmation.npy
```

The command refuses to overwrite either the index or its adjacent JSON
manifest.

```sh
uv run python paintbot_lab/paintbot/rl/evaluate_sealed_candidate.py \
  --checkpoint runs/expert-corpus-v1/training-v2-diversity/full/best \
  --validation-evaluation runs/expert-corpus-v1/training-v2-diversity/full/validation_evaluation.json \
  --workspace runs/expert-corpus-v1 \
  --out runs/expert-corpus-v1/training-v2-diversity/full/sealed_test_evaluation.json
```

The first mettabox1 run and its negative behavioral verdict are recorded in the
[`GPU training report`](../../docs/reports/rl-mettabox1-sft-2026-08-07.md).
The matched weighting follow-up is in the
[`action-change report`](../../docs/reports/rl-action-change-weighting-2026-08-07.md).
The subsequent 2x2 found that history, not transition sampling alone, carries
the useful signal. Its selected arm improved action changes on held-out GV40
but is not deployment-ready; see the
[`temporal-history report`](../../docs/reports/rl-transition-temporal-2x2-2026-08-07.md).

History-aware training uses `--max-history-tokens` (default 832) to reserve the
entire compact history before allocating the remaining text budget to the
nearest-first current observation. The previous action and all five targets
are always retained. This is currently an offline training/evaluation path;
`policy.py` does not yet maintain the rolling history required by these
checkpoints. The experiment builder can reproduce the matched corpora:

```sh
uv run python paintbot_lab/paintbot/rl/build_temporal_experiment.py \
  --source-workspace paintbot_lab/paintbot/rl/data/runs/historical-cross-era-v1 \
  --out paintbot_lab/paintbot/rl/data/runs/temporal-2x2-v1
```

## Observation-length experiment

`observation_text.py` defines the candidate semantic-entity serialization.
`capture_wire_observations.py` converts a recorded Sprite-v1 wire stream into
versioned snapshots, and `measure_observation_lengths.py` measures those
snapshots with the exact pinned Qwen tokenizer.
`extract_replay_wire.nim` is compiled against an exact historical
`coworld-ctf` checkout to reconstruct the player-view stream while enforcing
the replay's recorded state hashes.

The measurement deliberately fails unless the corpus covers all five
preregistered GameVersion eras and supplies at least 1,000 observations for
each represented GameVersion. It samples exactly 1,000 evenly spaced frames
per version so recent data cannot dominate the result. Raw corpora and
generated results are local artifacts, not repository data.

The first run covered GV16/24/30/35/40 and **refuted** the full all-label
serialization: global p99 was 30,297 tokens and max was 43,672. Historical
human-view `fog` runs dominated the failure. Removing only those objects from
the same frames reduced p99 to 3,429 and max to 4,424; that is a diagnostic,
not a revised verdict. See the
[`experiment report`](../../docs/reports/rl-observation-length-experiment.html)
and [`living design`](../../docs/designs/rl-policy.md).

The source-derived follow-up excludes exactly `fog`, `splatter …`,
`hit splat …`, and `damage pop …` while retaining unknown labels. It
**confirmed** the canonical bot-semantic representation: global p99 3,178 and
max 4,424 tokens. `serialize_observation()` applies this filter by default;
pass `include_human_visuals=True` only to reproduce the rejected all-label
baseline. See the
[`filtered experiment`](../../docs/reports/rl-bot-semantic-length-experiment.html).

```sh
uv run python paintbot_lab/paintbot/rl/capture_wire_observations.py \
  path/to/slot.wire.jsonl --game-version 35 \
  --out paintbot_lab/paintbot/rl/data/gv35.jsonl

uv run python paintbot_lab/paintbot/rl/measure_observation_lengths.py \
  paintbot_lab/paintbot/rl/data/*.jsonl \
  --entity-view bot-semantic \
  --out paintbot_lab/paintbot/rl/results/lengths.json
```

The length experiment covered only labeled entities and geometry. The vertical
slice now decodes the walkability payload through a separate, configurable map
encoder; its architecture and token budget are baseline choices, not settled
experimental conclusions.
