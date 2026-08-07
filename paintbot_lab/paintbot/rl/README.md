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
- `pipeline.py` downloads declared episodes with the shared artifact tool,
  creates exact-source worktrees, compiles both extractors against each pinned
  revision, validates replay hashes and expert rewards, and writes balanced,
  replay-disjoint train/validation/test corpora with complete provenance.
- `modeling.py` prepends 16 global plus 16 current-position map tokens to Qwen,
  constrains generation by action slot, and provides LoRA/full-tuning loading.
- `training.py` provides Accelerate training, cosine scheduling, validation,
  best/final checkpoints, and resumable optimizer/model/RNG state; `policy.py`
  is the Sprite-v1 inference shell with opt-in per-decision activation tracing.

Install the optional training stack separately from the existing player labs:

```sh
uv sync --group rl
```

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

Resume after a preemption from an epoch directory under
`checkpoint/trainer_state/` with `--resume-from`. The final model is in
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
`evaluate_sft.py` reports the grammar-constrained accuracy that matches live
decoding as well as unrestricted vocabulary accuracy, per-slot accuracy, a
held-action persistence baseline, and accuracy restricted to examples where
the expert actually changed the button state. The latter two are required:
aggregate accuracy can otherwise reward simply copying the previous mask.

Training accepts `--action-change-weight <number|balanced>`. Numeric values
multiply loss only for movement/turn/fire/grenade targets whose state differs
from the prior tick. `balanced` derives `unchanged_components / changed_components`
from the training split; `<STOP>` remains weight 1. The first weighting sweep
showed that this mechanism creates transition recall but excessive false
changes, so it is an experiment knob rather than a new default.

The first mettabox1 run and its negative behavioral verdict are recorded in the
[`GPU training report`](../../docs/reports/rl-mettabox1-sft-2026-08-07.md).
The matched weighting follow-up is in the
[`action-change report`](../../docs/reports/rl-action-change-weighting-2026-08-07.md).

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
