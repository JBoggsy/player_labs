# Transition sampling and four-tick history

Date: 2026-08-07
Verdict: four-tick history is useful; transition-centered sampling is a small
increment once history is present, not a sufficient intervention by itself

## Question

The first cross-era SFT model mostly repeated its previous button mask. This
experiment separates two candidate causes:

1. transitions are too rare under uniform frame sampling; and
2. the current observation does not contain enough temporal evidence to infer
   when the expert changes an action.

The matched 2x2 varies sampling and observation history independently. All
arms use Qwen3-0.6B-Base, LoRA rank 8, learning rate `2e-4`, three epochs, the
same replay-disjoint GV16/24/30/35 split, and unweighted token loss.

| arm | sampling | input |
| --- | --- | --- |
| control | uniform frames | current frame |
| transition-current | 50% changed / 50% held masks | current frame |
| uniform-history4 | uniform frames | four causal deltas + current frame |
| transition-history4 | 50% changed / 50% held masks | four causal deltas + current frame |

Each training arm has 1,700 samples; validation has 692. Transition-centered
sets preserve those sizes and balance changed and held examples within each
era. History steps cover offsets `-4,-3,-2,-1`, include the action held at each
step, and retain at most four prioritized bot-semantic entity changes. They
never contain the target tick or future state. Complete history uses at most
831 Qwen tokens in this corpus; the collator reserves 832 tokens before
truncating the current frame's lowest-priority tail.

## Validation results

The natural, uniformly sampled validation distribution is the primary view:

| arm | overall exact | changed-action exact | changed-component accuracy | change precision | change recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| uniform / current | 69.1% | 0.0% | 0.7% | 100.0% | 0.7% |
| transition / current | 68.8% | 0.0% | 0.7% | 42.9% | 1.1% |
| uniform / history4 | **71.1%** | 7.9% | 9.9% | 72.7% | 11.8% |
| transition / history4 | 70.1% | **8.4%** | **10.3%** | **73.1%** | **14.0%** |

On the balanced transition validation distribution, the same ordering holds:

| arm | overall exact | changed-action exact | changed-component accuracy | change precision | change recall |
| --- | ---: | ---: | ---: | ---: | ---: |
| uniform / current | 49.9% | 0.3% | 0.7% | 75.0% | 0.7% |
| transition / current | 49.4% | 0.0% | 0.7% | 42.9% | 0.7% |
| uniform / history4 | 52.2% | 6.3% | 8.5% | 72.2% | 9.2% |
| transition / history4 | **52.3%** | **6.9%** | **8.9%** | **77.8%** | **11.5%** |

Sampling alone is flat. History produces the large effect and does so without
the false-change collapse seen under class-balanced loss weighting. Balanced
sampling adds a smaller improvement once history is available. We selected
`transition-history4` before opening GV40 because it had the best transition
metrics on both validation views with stable precision; its one-point natural
overall-accuracy cost was accepted under the preregistered transition goal.

## Held-out GV40 result

The selected model was evaluated once on the 1,347-example natural-distribution
GV40 history test set (309 changed-action examples).

| metric | current-frame control | selected history model |
| --- | ---: | ---: |
| Overall exact action | **77.1%** | 74.7% |
| Changed-action exact | 0.3% (1/309) | **3.9% (12/309)** |
| Changed-component accuracy | 0.7% | **8.8%** |
| Change precision | not decision-useful at near-zero recall | 45.2% |
| Change recall | 0.7% | **11.2%** |

The cross-era test confirms that temporal history carries useful action-change
information, including for an unseen game era. It also rejects the stronger
claim that this four-tick representation and seed corpus are sufficient for a
deployable behavioral clone: the model still misses almost nine in ten changed
components, predicts too many false changes in GV40, and loses 2.4 points of
overall exact accuracy.

## Decision and next experiment

Keep compact causal history in the policy design and keep transition-centered
sampling as an experiment knob, not a universal default. Do not package this
checkpoint as a live player.

The next experiment should expand replay and expert diversity before adding
more model complexity. Within that larger corpus, compare the current delta
history against a short sequence of full self/nearby-entity states and measure
results by change type (movement, turn, fire, grenade). That will distinguish
missing evidence in the delta grammar from simple data scarcity.

## Reproducibility

- Dataset bundle SHA-256:
  `d433465ffa34115cc0178cf477fd6ccefaaef7b521817ff9d48aa6a5b9154ced`
- Archived run SHA-256:
  `d6aff13a867eaa1ce88b5ed3dace0c4a8540f0b85cf842aefe902f9984a96920`
- Local archive:
  `paintbot/rl/data/training/mettabox1-temporal-2x2-20260807/mettabox1-temporal-2x2-20260807.tar.gz`
- Remote workspace: `/home/metta/paintbot_rl_training_20260807`
- Selected checkpoint: `runs/temporal-2x2/transition-history4`

The archive contains all three new lightweight checkpoints, training logs,
validation/test metrics, corpus provenance, and the experiment manifest. Large
resumable optimizer/model states remain on mettabox1 and are intentionally not
duplicated locally.
