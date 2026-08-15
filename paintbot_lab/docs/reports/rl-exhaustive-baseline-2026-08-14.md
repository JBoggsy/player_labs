# Exhaustive-corpus SFT baseline and diversity follow-up

Date: 2026-08-14

Verdict: 59.17% sealed-test teacher-forced proxy; autoregressive result pending; matched-compute diversity arm running

## Question

Can the cross-era Qwen3-0.6B LoRA policy exceed 70% autoregressive exact-action
accuracy on the fixed, replay-disjoint, 50/50 changed/held evaluation contract
without tuning against the test set?

## Immutable evaluation contract

The 10,000-row sealed test index remains unchanged:

- test index SHA-256: `244dad9d331ab92c2a852c1f7ca1ae31d5892c48e11acf08cb31c6f65577dbdb`
- validation index SHA-256: `78e46be391cf13c6c488b6b0ed2ccd0fe1da36eb73d13fb6db5a42c0f8d50644`
- test Arrow dataset fingerprint: `03693a38c974e27a`
- validation Arrow dataset fingerprint: `599c88fdfbf0ba82`
- test selected semantic rows SHA-256: `3f64245eff0e2f8307453455fdd8273b645ed59175eabf2db895d4b16e22e1a3`
- validation selected semantic rows SHA-256: `8b02bd5212d0ba47346d81af812be24ddf46d9e9ff9f19d3071754217ddcb35a`
- baseline test evaluation SHA-256: `f4b5fb20777076ae84856214051be63dea3daf456167df73d3f93244a6e0457e`

All diagnosis and model selection after the baseline use validation only. The
test set will be opened once for a candidate selected under the frozen
validation rule. New evaluator artifacts include their sample-index hash,
dataset fingerprint, selected-row hash, and validated map-set fingerprint.
`evaluate_sealed_candidate.py` refuses the final run unless validation attests
the frozen dataset, rows, index, maps, and exact checkpoint tree; contains
10,000 rows; uses the matching representation contract; and exceeds 70%
autoregressive exact action. It also independently checks both datasets and
indices, requires validation and test to share the same map table, verifies the
sealed evaluator's content attestations, and refuses to overwrite an existing
candidate result.

Metric correction: the original absolute-action evaluator derived its
`constrained_*` fields from teacher-forced slot logits. Live inference instead
feeds each generated slot back into the transformer. The original artifacts and
numbers below remain valid teacher-forced diagnostics, but they do not establish
autoregressive exact-action accuracy. New artifacts add explicit `autoregressive_*`
fields, and only `autoregressive_exact_action_accuracy` can satisfy the 70% gate.

## Baseline result

The baseline trained on 250,000 unique rows for three epochs: 750,000 total
presentations drawn from a 219,717,943-row training split. It used the existing
Qwen revision, LoRA rank 8, BF16, learning rate `2e-4`, effective batch 16,
four-tick causal history, and an unweighted action-token loss.

| Teacher-forced diagnostic | Sealed test |
| --- | ---: |
| Exact action | 59.17% |
| Changed-action exact | 27.19% |
| Held-action exact | 91.14% |
| Movement token | 73.69% |
| Turn token | 79.25% |
| Change precision | 78.33% |
| Change recall | 38.92% |
| Repeat-previous-mask exact | 50.01% |

This teacher-forced proxy beats repeat-previous-mask by 9.16 points, evidence
that the model learned behavior rather than merely exploiting held actions. It
is not the final autoregressive score. The 50/50 gate still makes the target
explicit: at 91.14% held-action exact, about 48.9% changed-action exact is
required to cross 70% overall.

## Validation diagnosis

Saved epoch states were exported and evaluated on the same 10,000 validation
rows. Exact-action gains flatten well below the target.

| Epoch | Validation loss | Teacher-forced exact | Changed exact | Held exact | Movement |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.3143 | 57.02% | 20.80% | 93.24% | 71.30% |
| 2 | 0.2909 | 58.49% | 25.56% | 91.42% | 72.51% |
| 3 | 0.2823 | 59.41% | 27.48% | 91.34% | 73.28% |

Movement is the dominant component bottleneck. On changed movement targets,
the epoch-3 model is correct 20.40% of the time; turn is 43.54% and fire is
73.90%. Movement's 73.28% aggregate accuracy is itself barely above the whole-
action target.

The saved validation logits further separate movement recognition from
direction selection:

| Changed-movement outcome | Share |
| --- | ---: |
| Correct new movement | 20.40% |
| Repeated previous movement | 71.85% |
| Changed to the wrong new movement | 7.76% |

When the previous movement token is excluded by an oracle change gate, the
model's highest-ranked remaining direction is correct 54.85% of the time. An
oracle movement change gate would raise the teacher-forced proxy from 59.41%
to 69.61% without changing the other four outputs. This localizes almost the
entire proxy gap to the previous-action copycat shortcut; the autoregressive
evaluation is the authoritative target.

## Rejected decoder-calibration hypothesis

Hypothesis: the model knows the new action but greedy decoding is too
conservative about departing from the previous mask.

The validation set was divided by `sha256(replay_id)` so no replay crossed the
calibration and confirmation halves. A pre-registered global logit bonus from
0.0 through 4.0 was applied only to legal action tokens that differed from the
previous state. Calibration selected `0.0`; positive bias raised transition
recall but reduced exact accuracy. A movement-only bonus selected `0.1` and
improved confirmation exact action only from 59.89% to 60.01%. This is too small
to retain and does not explain the gap.

## Next experiment: matched-compute diversity

The next arm changes one variable: unique training rows.

| Setting | Baseline | Candidate |
| --- | ---: | ---: |
| Unique rows | 250,000 | 750,000 |
| Epochs | 3 | 1 |
| Total presentations | 750,000 | 750,000 |
| Optimizer updates | 46,875 | 46,875 |
| Validation/test indices | frozen | frozen |
| Decoder bias | 0 | 0 |

The candidate is supervised under
`runs/expert-corpus-v1/training-v2-diversity`. It builds a separate balanced
index, never overwrites the baseline index, resumes after process failure or
reboot, trains automatically, and stops after validation. It does not open the
sealed test. The selected 750,000-row index is balanced 375,000/375,000 between
changed and held actions and has SHA-256
`27a2b9feafb0b07dd1140e715600c34481b9a708737cfdcc4b3fcf655f5097d8`.

Prediction: tripling unique cross-era states at fixed compute will improve
validation movement transitions and the teacher-forced proxy over the 59.41%
baseline. The diversity artifact will also provide the first authoritative
autoregressive score under the corrected evaluator. If diversity is flat, data
repetition is not the main constraint and the next experiment should compare
richer temporal state or greater adaptation capacity rather than merely adding
epochs. Once the diversity run releases the GPU, the unattended queue evaluates
the original baseline best checkpoint autoregressively on the same frozen
validation index. This supplies a like-for-like diagnostic comparison without
opening the test or changing any promotion threshold.

## Queued experiment 1: residual event actions

The first queued arm replaces four absolute-state targets with the stateful
event language James originally proposed: one press or release token for each
button that changes, followed by `<STOP>`. A held action is only `<STOP>`.
Events are canonically ordered as releases then presses; the decoder applies
them to the previous button mask and rejects redundant or contradictory
sequences. Generation is constrained to that same phase and button order so it
cannot condition later predictions on event permutations absent from SFT. This
directly supervises the residual `A_t - A_(t-1)` rather than asking the model to
reproduce four correlated held states.

This is motivated by the validation diagnosis and by prior imitation-learning
work on the copycat problem and residual-action prediction. It is not loss
weighting: every emitted event and `<STOP>` has unit weight, and the same frozen
50/50 changed/held index is used.

On the 10,000-row validation index, target sequences have this distribution:

| Tokens including `<STOP>` | Rows |
| ---: | ---: |
| 1 (held action) | 5,000 |
| 2 | 2,835 |
| 3 | 1,370 |
| 4 | 444 |
| 5-7 | 351 |

The arm trains on the exact original 250k index for one epoch under the
original three-epoch LR schedule. It promotes to epochs 2-3 only if
autoregressive validation exact is at least 58.02%, movement exceeds 71.30%,
and held exact remains at least 91.24%. These fixed preregistered hurdles were
derived before the metric correction and are conservative screening thresholds,
not a claimed one-point autoregressive delta over epoch 1. Evaluation decodes
the canonical predicted event sequence back to a held mask before scoring exact
action. The selection metric generates
autoregressively until `<STOP>` without knowing the target length; teacher-
forced event accuracy is diagnostic only. Training reserves the same worst-
case nine-token action budget for every row, so prompt truncation cannot leak
the number of target events. The codec defaults to `absolute`, is stored in
checkpoint metadata, and does not alter existing checkpoints.

## Queued experiment 2: spatial semantics

Movement remains the dominant error, while the current text representation
asks Qwen to infer direction and proximity from map-normalized integer offsets.
That is a poor inductive bias for nearby geometry: permille rounding can collapse
small displacements, and self sprite width changes from 18 to 96 pixels across
the sampled game versions.

The queued arm adds two observation-derived labels to the self and 15 nearest
entities:

- an eight-way egocentric screen bearing such as `above-right`;
- a logarithmic range such as `2-to-4-self-widths`.

Both are computed from fields already available to the live Sprite-v1 policy;
no replay-only world metadata is used. Raw offsets remain present. The feature
defaults off in training, evaluation, and inference, so it cannot change the
active diversity run if that run resumes.

On 1,000 evenly spaced rows from the 750k diversity index, annotating every
entity increased mean prompt length 16.0%, so that version was rejected before
training. Limiting labels to the nearest 16 increased mean length 6.2% (2,972
to 3,155 tokens) and the share above 4,096 tokens only 0.4 points (5.7% to
6.1%). Since entities are nearest-first, all labeled entities remain ahead of
the truncation boundary.

The screen runs only if the event-action screen is rejected. It uses
the original 250k index and trains one epoch with the original three-epoch LR
schedule. Promotion to epochs 2-3 requires all of:

- autoregressive validation exact action at least 58.02%;
- autoregressive validation movement above 71.30%;
- autoregressive held-action exact no lower than 91.24%.

Failure stops the arm. Passing resumes the same optimizer/scheduler state for
epochs 2-3. Both selection stages use validation only; the sealed test remains
closed.

## Rejected adapter-capacity canary

PEFT's QLoRA-style guidance recommends adapting every transformer linear layer
when trying to approach full-finetuning quality. A matched 1,024-train / 256-
validation canary therefore compared the rank-8 attention-only default against
rank-8 `all-linear`, holding all other inputs and hyperparameters fixed.

| Adapter | Validation loss | Exact action | Changed exact | Movement |
| --- | ---: | ---: | ---: | ---: |
| Attention only | 1.2094 | 9.38% | 6.25% | 23.05% |
| All linear | 1.6847 | 9.77% | 8.59% | 18.75% |

All-linear fit on the RTX 4090 at 22.2/24.6 GB VRAM, but validation loss
worsened 39%, movement regressed 4.30 points, and the one-example aggregate
gain is not meaningful at this sample size. Do not promote this configuration.
The implementation retains adapter coverage and rank as explicit experiment
knobs; the attention-only rank-8 default remains unchanged.

## Caveats

- Exact imitation may have an irreducible ceiling because expert internal state
  and long-term goals are only partially observable from four causal deltas.
- The balanced gate is intentionally unlike the natural tick distribution; it
  measures decisions on changes rather than rewarding action persistence.
- Historical `constrained_*` results are teacher-forced and optimistic after an
  early token error. Corrected `autoregressive_*` evaluation now matches the
  inference decoder's feedback semantics and is the only metric accepted by the
  final gate. Runtime support for the checkpoint's four-tick history remains a
  separate deployment requirement.

## References

- [Hugging Face PEFT LoRA reference](https://huggingface.co/docs/peft/main/package_reference/lora)
- [QLoRA paper](https://papers.neurips.cc/paper_files/paper/2023/file/1feb87871436031bdc0f2beaa62a049b-Paper-Conference.pdf)
- [The Road To Know-Where (ICCV 2021)](https://openaccess.thecvf.com/content/ICCV2021/html/Qi_The_Road_To_Know-Where_An_Object-and-Room_Informed_Sequential_BERT_for_ICCV_2021_paper.html)
- [Rethinking and Improving Relative Position Encoding for Vision Transformer (ICCV 2021)](https://openaccess.thecvf.com/content/ICCV2021/html/Wu_Rethinking_and_Improving_Relative_Position_Encoding_for_Vision_Transformer_ICCV_2021_paper.html)
- [Fighting Copycat Agents in Behavioral Cloning from Observation Histories (NeurIPS 2020)](https://proceedings.neurips.cc/paper/2020/hash/1b113258af3968aaf3969ca67e744ff8-Abstract.html)
- [Resolving Copycat Problems in Visual Imitation Learning via Residual Action Prediction](https://arxiv.org/abs/2207.09705)
