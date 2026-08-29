# Initial cross-era RL-policy SFT pass

Date: 2026-08-06  
Verdict: pipeline and Mac feasibility confirmed; useful learned behavior not yet demonstrated

## Configuration

- Hardware: MacBook Pro, Apple M4 Pro (14 cores), 48 GB unified memory
- Accelerator: PyTorch MPS
- Base: `Qwen/Qwen3-0.6B-Base` at pinned revision
  `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`
- Tuning: LoRA rank 8 plus the 17 added action-token rows
- Map input: 32 cached/gathered spatial tokens
- Text ceiling: 2,048 tokens
- Batch: 1, gradient accumulation 4
- Epochs: 1; learning rate: 2e-4; seed: 1
- Corpus: 125 examples, exactly 25 from each of GV16/24/30/35/40
- POV selection: one winning high-performing policy trajectory per era
- Holdout: 25 disjoint frames, exactly five per era

The ignored local run directory is
`paintbot/rl/data/training/initial-cross-era-20260806/`. Its accepted checkpoint
contains `training_run.json` and `holdout_evaluation.json`.

## Mac feasibility

The first pilot exposed an MPS adaptive-pooling limitation; the map pool was
replaced with equivalent explicit bin means. Retrying without activation
checkpointing on a 2,684-token example drove unified memory into pressure and
swap during the first optimizer step, so that configuration was stopped.

With activation checkpointing and a 2,048-token ceiling, a five-example pilot
completed in 26.9 seconds with no swaps. The accepted 125-example run completed
in 549.8 seconds (9.2 minutes), also with zero swaps reported by `time -l`.

Conclusion: small Qwen3-0.6B LoRA experiments are practical on this 48 GB M4
Pro. Full tuning or uncheckpointed 3K-4K-token training is not the sensible Mac
path.

## Training result

| Batch window | Mean loss | Median loss |
| --- | ---: | ---: |
| 1-25 | 10.00 | 9.71 |
| 26-50 | 6.09 | 5.93 |
| 51-75 | 3.83 | 3.34 |
| 76-100 | 2.53 | 2.52 |
| 101-125 | 2.29 | 2.22 |

The first-20 mean was 10.76 and the last-20 mean was 2.31.

## Disjoint holdout

The runtime constrains each output position to its legal action subset, so the
decision metric is constrained accuracy rather than argmax over Qwen's entire
vocabulary.

| Metric | Model | Majority baseline |
| --- | ---: | ---: |
| Component-token accuracy | 72.0% | 71.2% |
| Exact five-token action | 8.0% | 8.0% |

Per-era constrained component accuracy was GV16 60%, GV24 72%, GV30 80%, GV35
84%, and GV40 64%, with only five examples per cell. Those cells are descriptive
only, not stable era estimates.

The accepted checkpoint reloaded successfully and generated a valid five-token
sequence autoregressively. On the inspected holdout frame it matched turn,
fire, grenade, and STOP but selected south rather than the target east.

## Invalid prototype caught by evaluation

The first completed prototype joined added action tokens with spaces. Qwen
therefore saw nine targets: five special tokens plus four ordinary whitespace
tokens, while constrained inference could only emit the five specials. That
checkpoint is retained locally as `checkpoint-invalid-spaced-targets` and must
not be used. Action serialization now joins special tokens without separators;
the tokenizer contract is verified as exactly five IDs.

## Next experiment

Build a replay-disjoint dataset large enough to beat per-component and exact-
action majority baselines while preserving equal era weighting. Split by entire
replay—not frames from the same replay—before increasing epochs. Report per-slot
accuracy so movement and turning cannot hide behind always-released fire and
grenade states.
