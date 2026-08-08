# Mettabox1 cross-era SFT run

Date: 2026-08-07  
Verdict: training infrastructure confirmed; the learned policy does not yet beat held-action persistence

## Run contract

- Host: `mettabox1` (`metta1`), NVIDIA GeForce RTX 4090 (24,564 MiB), driver
  570.211.01
- Environment: uv 0.11.8, PyTorch 2.11.0+cu128, CUDA 12.8, BF16
- Model: `Qwen/Qwen3-0.6B-Base`, LoRA, seed 1
- Corpus: 1,700 training examples and 692 replay-disjoint validation examples,
  balanced across GV16/24/30/35; 1,347 examples from GV40 were sealed for the
  final unseen-era evaluation
- Batch size 2, gradient accumulation 8, 4,096 text tokens, weight decay 0.01,
  warmup ratio 0.03
- Prepared-data bundle SHA-256:
  `d810851ac3fb0b4f83fcf46c7e0a164c16ad4028cae93535ad11e51cda845e1a`

The first dependency resolution selected a CUDA 13 PyTorch build, which the
installed driver could not initialize. The lock now selects PyTorch's explicit
CUDA 12.8 index on Linux and keeps the normal platform build on macOS.

## Canary

The end-to-end four-train/two-validation pipeline canary completed on CUDA in
17.68 seconds, including checkpoint save and reload. A direct BF16 canary then
completed in 3.93 seconds. Both exercised the same model, map encoder, LoRA,
collator, and evaluator used by the full run; their tiny losses and accuracies
are plumbing checks, not behavioral evidence.

## Learning-rate and epoch sweep

The sweep kept data, seed, batch, accumulation, context, LoRA, schedule, and
regularization fixed. It selected by replay-disjoint validation loss. Weak arms
were culled once they could no longer challenge the current winner.

| Learning rate | Validation loss by completed epoch | Decision |
| ---: | --- | --- |
| 1e-4 | 0.716370, 0.338551, 0.315051, 0.313784 | plateaued; reject |
| 2e-4 | 0.342919, 0.308851, **0.299010** | select epoch 3 |
| 4e-4 | 0.325649 | better than 2e-4 at epoch 1, but already behind its epoch-2/3 result; cull |

The selected 2e-4 arm completed the requested three full epochs over the
1,700-example training corpus. It is therefore also the full-length training
job; rerunning the identical seed and configuration would only duplicate it.
The adaptive sweep started epoch 4 for that arm, then stopped it after 200
minibatches because the completed epoch-3 checkpoint remained the selected
model. That epoch-3 best checkpoint was promoted to `runs/full/checkpoint`.

## Evaluation

The evaluator constrains each of the five output positions to its legal action
tokens. The persistence baseline emits the previous held-button mask unchanged.

| Split | Samples | Loss | Model token | Persist token | Model exact | Persist exact | Changed-action exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GV16/24/30/35 validation | 692 | 0.299541 | 92.20% | 92.14% | 69.08% | 69.08% | 0 / 214 (0%) |
| Held-out GV40 | 1,347 | 0.258066 | 94.45% | 94.42% | 77.13% | 77.06% | 1 / 309 (0.32%) |

Held-out GV40 slot accuracy was 83.52% movement, 88.94% turn, 99.78% fire,
100% grenade, and 100% stop. Those high aggregate values are not evidence that
the policy learned decisions: most sampled targets preserve the prior held
state, and the model reproduced only one complete action change in 309 changed
examples. This checkpoint should not be packaged as a live player.

The next dataset experiment should target transitions explicitly: retain all
button-state changes, add a controlled sample of held-state frames, and select
models using changed-action and per-slot metrics rather than aggregate token
loss alone. A lower sampling stride or event-centered windows may also expose
the temporal evidence preceding a decision.

## Artifacts

- Remote run root: `~/paintbot_rl_training_20260807`
- Remote checkpoint: `runs/full/checkpoint`
- Remote logs: `logs/canary.log`, `logs/canary-bf16.log`,
  `logs/sweep-lr*.log`, `logs/full-validation-eval.log`, and
  `logs/full-test-eval.log`
- Local ignored archive:
  `paintbot/rl/data/training/mettabox1-cross-era-20260807/paintbot-qwen-cross-era-20260807.tar.gz`
- Checkpoint archive SHA-256:
  `eaa73135a4c1bb330f59e64639b977d143fe00d23b60a2917a9682f4359d0b3f`

The checkpoint includes `run_manifest.json`, `validation_evaluation.json`, and
`test_evaluation.json` alongside the adapter, tokenizer, map encoder, and policy
configuration.
