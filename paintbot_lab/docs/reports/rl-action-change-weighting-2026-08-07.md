# Action-change loss-weighting experiment

Date: 2026-08-07  
Verdict: weighting teaches some transitions but does not solve action prediction

## Hypothesis

The uniform SFT objective is dominated by control components that remain held
from the preceding tick. Up-weighting only control-slot targets that differ
from the previous mask should improve action-change prediction. Class-balanced
weighting should be a principled point on that tradeoff.

The 1,700-example training corpus contains 741 changed and 6,059 unchanged
components across movement, turn, fire, and grenade slots. The inverse-frequency
class-balanced multiplier is therefore 6,059 / 741 = **8.1768×**. The structural
`<STOP>` token is excluded from this calculation and remains weight 1.

## Method

Four matched arms used the same Qwen revision, LoRA configuration, cross-era
corpus, replay-disjoint validation split, seed, sample order, optimizer,
learning rate (2e-4), batch/accumulation, BF16 precision, and three-epoch budget.
Only the changed-component loss multiplier differed:

- 1× uniform control: the previously trained checkpoint
- 3× moderate weighting
- 8.1768× class-balanced weighting
- 16× stress weighting

Selection used the GV16/24/30/35 validation set. GV40 remained sealed until
class-balanced weighting was selected as the knee of the validation curve.

`change_precision` and `change_recall` measure whether the model detects that a
control component changed. `changed_component_accuracy` is stricter: it must
also predict the correct new state. Changed-action exact requires all five
output tokens to match on a frame containing at least one change.

## Validation results

| Changed weight | Overall exact | Changed-action exact | Changed-component accuracy | Change precision | Change recall |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1× | **69.08%** | 0 / 214 (0%) | 0.74% | 100.0% | 0.74% |
| 3× | 62.86% | 11 / 214 (5.14%) | 7.35% | **34.23%** | 13.97% |
| 8.1768× balanced | 48.55% | 26 / 214 (12.15%) | 16.91% | 24.92% | 27.57% |
| 16× | 34.83% | **32 / 214 (14.95%)** | **27.21%** | 24.66% | **46.69%** |

Weighting creates real transition behavior, but the curve is a direct exchange
of persistence for changes. The 16× arm gains only 2.8 percentage points of
changed-action exact over class balancing while losing 13.7 points of overall
exact. Class balancing is the knee, not a generally good policy.

## Sealed GV40 result

| Metric | Uniform | Class-balanced |
| --- | ---: | ---: |
| Overall exact action | 77.13% | 35.26% |
| Changed-action exact | 1 / 309 (0.32%) | 29 / 309 (9.39%) |
| Changed-component accuracy | 0.53% | 11.44% |
| Change precision | 100.0% | 13.72% |
| Change recall | 0.53% | 29.26% |
| Movement accuracy | 83.52% | 81.07% |
| Turn accuracy | 88.94% | 43.06% |

The transition signal transfers to the unseen era, but poorly. Class balancing
predicts 802 component changes where only 376 occur, and turn prediction
collapses. It is not a live-policy candidate.

## Decision

Do not continue increasing loss weights. Preserve uniform, 3×, balanced, and
16× as controls. The next experiment should alter the information and sampling:

1. retain every action transition and a controlled number of held-state frames;
2. include short temporal context around each transition;
3. consider explicit `KEEP`/new-state or press/release targets;
4. select with transition precision, transition recall, correct-new-state
   accuracy, and false-change rate, not aggregate token loss.

## Artifacts

- Remote root: `~/paintbot_rl_training_20260807/runs/weighting`
- Local ignored archive:
  `paintbot/rl/data/training/mettabox1-action-weighting-20260807/paintbot-action-weighting-20260807.tar.gz`
- Archive SHA-256:
  `72446d772d3bc0dd55a6281cb20b158dffd291b2de4dd3c945b9dd364d53ad70`

The archive contains the selected class-balanced adapter/tokenizer/map encoder,
all arm manifests and validation results, the selected GV40 result, and the
three new training logs. Full optimizer states remain on mettabox1.
