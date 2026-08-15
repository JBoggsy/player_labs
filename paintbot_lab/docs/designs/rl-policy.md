# Cross-era RL policy

Status: replay-to-checkpoint training pipeline implemented; defaults remain provisional  
Last updated: 2026-08-07

## Goal

Build a learned Paintbot policy alongside Stencil without binding its input
vocabulary to one Coworld-CTF era. The first training stage is supervised
behavior cloning over observation-to-action pairs recovered from historically
strong agents. Reinforcement learning can follow after this establishes a
usable policy prior.

## Decisions

| area | decision | rationale |
| --- | --- | --- |
| Base model | [`Qwen/Qwen3-0.6B-Base`](https://huggingface.co/Qwen/Qwen3-0.6B-Base) | Small enough for inexpensive fine-tuning, but with more semantic capacity and context than the 135M-360M alternatives; ungated and Apache-2.0. |
| Model revision | `da87bfb608c14b7cf20ba1ce41287e8de496c0cd` | Pin the tokenizer and weights so length measurements and training examples remain reproducible. |
| Observation semantics | Serialize Sprite-v1 labels with Qwen's native tokenizer and let Qwen contextualize them. | New compositional labels reuse pretrained subword semantics without a game-specific vocabulary. |
| External embeddings | Do not use a separate sentence embedder or project precomputed vectors into Qwen. | A learned projection would itself need alignment training and would discard the clean native-token path into Qwen's pretrained embedding space. |
| Numeric label data | Pull numeric spans out of labels into ordered values while retaining placeholders in the semantic text. | Values such as `2/3`, `3211x1713`, coordinate pairs, aim brads, and handicap values should remain machine-readable instead of being conflated with label identity. |
| Spatial data | Serialize normalized center, size, and self-relative offsets, plus raw layer/depth. | Permille coordinates are stable across map sizes while retaining the spatial relationships carried by Sprite-v1. |
| Entity filtering | Exclude only `fog`, `splatter …`, `hit splat …`, and `damage pop …`; retain every unknown label. | These are exactly the human-visual families omitted by the engine's `spritesOff` bot path. A denylist preserves zero-shot handling of future semantic labels, unlike an allowlist. |
| Training eras | Mix historical game eras; never train or validate the first model on a single-era corpus. | The central claim is robustness to observation-schema evolution. A single-era success cannot test it. |
| Initial objective | SFT next-token prediction of four factorized action tokens followed by `<STOP>`. | This is the smallest compositional behavior-cloning objective that exercises the pretrained model and the cross-era representation. |
| Action output | Generate four factorized semantic action tokens, then `<STOP>`. | Factorization shares training signal across action combinations and avoids a sparse 108-token joint vocabulary. |
| Residual-action experiment | Optionally generate only canonical button press/release events, then `<STOP>`, and decode against the previous mask. | Validation localized the exhaustive model's main error to copying prior movement; this tests residual supervision without changing the default codec. |
| Map lifecycle | Decode and store the exact walkability raster once per episode; encode it into cached spatial features. | The map is static episode data delivered once at player initialization, so neither the dataset nor inference loop should duplicate or re-encode it per frame. |

The [selected model's official card](https://huggingface.co/Qwen/Qwen3-0.6B-Base)
reports 0.6B parameters, a 32,768-token context window, and Apache-2.0
licensing. [SmolLM2-360M](https://huggingface.co/HuggingFaceTB/SmolLM2-360M)
remains the lower-cost fallback; SmolLM2-135M is useful only as a pipeline
probe. [Gemma 3 270M](https://huggingface.co/google/gemma-3-270m) was not
selected because it is manually gated and uses the Gemma license.

## Candidate observation representation

One frame is deterministic text:

```text
observation game_version="35" frame=12 map_width=3211 map_height=1713
entity semantic="self red right" x_permille=210 y_permille=503 width_permille=5 height_permille=9 z=100 layer=0 dx_permille=0 dy_permille=0
entity semantic="hp {number_0}/{number_1}" label_numbers=["2", "3"] x_permille=211 y_permille=495 width_permille=9 height_permille=2 z=101 layer=0 dx_permille=1 dy_permille=-8
entity semantic="player blue left" x_permille=503 y_permille=487 width_permille=5 height_permille=9 z=100 layer=0 dx_permille=293 dy_permille=-16
```

Entities are ordered with self first, then by distance from self, semantic
label, position, and object ID as a final deterministic tie-breaker. Object IDs
are not serialized because they are episode-local implementation identifiers.

This is intentionally a faithful baseline, not a claim that every field will
survive ablation. The length experiment should measure the uncompressed form
before optimizing it.

Before serialization, the canonical bot-semantic view removes the four
source-defined human-visual families above. This is not salience pruning:
gameplay entities, unknown labels, and their complete geometry remain intact.

## Action representation

The model generates one fixed-grammar sequence per decision:

```text
<MOVE_*> <TURN_*> <FIRE_*> <GRENADE_*> <STOP>
```

The action vocabulary contains 16 semantic tokens: nine movement states
(`idle` plus eight compass directions), three aim-turn states, two fire-button
states, and two grenade-button states. `<STOP>` is the seventeenth added token.
This represents the same 108 behaviorally distinct button states as a joint
vocabulary, but every component token receives training signal across many more
examples and unseen combinations remain compositional.

Decoding is grammar-constrained by output position. The runtime decoder combines
the four semantic fields with the previous transmitted button mask to produce a
new Sprite-v1 held-button mask. This state is necessary because firing is a
press transition and grenade throwing is a C-button release transition; the
model therefore receives its previous factorized action as part of every input.
The decoder is deliberately responsible only for protocol state, not tactical
interpretation.

Loss applies to all four action tokens and `<STOP>`. Observation and previous-
action tokens provide context but are not language-model targets.

## High-level architecture

The policy has an episode path and a per-decision path:

```text
episode initialization
  Sprite-v1 walkability sprite
    -> exact binary map + stable map hash
    -> static convolutional spatial pyramid
    -> cached global and high-resolution feature grids

each decision
  cached map features + current self position
    -> global map tokens + gathered local-map tokens
  current bot-semantic entities
    -> deterministic text serialization -> Qwen token embeddings
  previous factorized action
    -> action-history tokens
  all inputs
    -> Qwen3-0.6B-Base
    -> four constrained action tokens + <STOP>
    -> stateful action decoder
    -> Sprite-v1 button mask
```

The complete static feature pyramid is computed once. At each decision, the
policy gathers a high-resolution window from the cached feature grid at the
agent's current position; it does not rerun the map encoder. Gathering should
happen every decision initially so the crop cannot become stale near walls or
narrow passages. A later optimization may reuse it until the agent crosses a
feature-grid cell.

Global map tokens remain constant for the episode. Local-map tokens, current
semantic entities, and the previous action change per decision. Dynamic actors
remain in the entity stream rather than being painted into the static map.

For the offline corpus, maps are normalized into a separate episode-level table:

```text
episode_map(map_hash, width, height, packed_walkability_bits)
sample(map_hash, replay_id, game_version, pov, tick,
       semantic_observation, previous_action, target_action)
```

This permits later map-encoder experiments without reconstructing the historical
Sprite-v1 observations or duplicating a large raster in every sample.

### Initial boundaries

- The first stage is cross-era supervised behavior cloning, not online RL.
- The map encoder is trained for policy utility; natural-image reconstruction is
  not its objective.
- Episode memory is initially limited to four compact, past-only entity deltas;
  recurrent state and longer histories remain deferred.
- A deterministic protocol fallback may be added for malformed model output,
  but scripted gameplay behavior is outside this first learned-policy design.

## Initial implementation (provisional defaults)

The code under `paintbot/rl/` now implements the complete offline-to-runtime
shape. These defaults are conservative starting points, not closed decisions:

| choice | current default | kept open by |
| --- | --- | --- |
| Map patches | two small convolutions, stride 8, 32 channels | `MapEncoderConfig` |
| Map tokens | 4x4 global pool plus 4x4 local pool (32 total) | `global_grid`, `local_grid` |
| Local context | radius 8 feature cells, gathered every decision | `local_radius_cells`; cached feature grid API |
| Tuning | LoRA rank 8 over attention projections plus only the 17 new token rows | `--tuning lora|full`, `--lora-rank`, and `--lora-target-modules attention|all-linear` |
| Text ceiling | 2,048 tokens for the Mac baseline, preserving the nearest/self-first prefix and all targets | `--max-text-tokens` |
| Replay alignment | observation at tick `t` predicts held mask at tick `t` | `--action-delay-ticks`; both ticks stored |
| Decoding | four constrained autoregressive action steps, then grammar-implied `<STOP>`, without a KV cache | isolated `greedy_action()` method |
| Temporal training input | four compact causal deltas plus previous transmitted action | `history` sample field; history length and `max_history_tokens` remain experiment knobs |

The action decoder uses the actual Sprite-v1 layout: directions occupy bits
1/2/4/8, Select (clockwise turn) is 16, A/fire is 32, B (counterclockwise turn)
is 64, and C/grenade is 128. It reports press and release transitions before
updating its retained mask. The player SDK pin was advanced to a revision that
accepts the full `0xff` mask; the previous revision clamped at `0x7f` and could
not transmit grenades.

The inference path computes the convolutional feature grid and global pool once
when the walkability sprite arrives. It gathers the local 4x4 pool at every
decision, so the crop follows the player without recomputing the convolutional
pyramid. `PAINTBOT_RL_TRACE=1` records every generated action and its protocol
edges, making activation and latency directly measurable.

## Cross-era data contract

Historic replays must be re-simulated at their exact recorded GameVersion to
recover the player-view Sprite-v1 stream. Replays contain simulator state and
inputs but do not contain rendered label bytes, so current-source rendering is
not valid reconstruction. Each example must retain replay identity, exact game
source commit, GameVersion, POV seat, frame/tick, serialized observation, raw
action mask, and acting-policy identity/version.

Training and evaluation must balance versions rather than allowing the most
abundant era to dominate. The first generalization evaluation should hold out
both complete labels and at least one complete GameVersion.

### Training pipeline

`paintbot/rl/pipeline.py` makes this contract executable. A versioned JSON
manifest declares immutable episode IDs, GameVersions, exact Coworld source
commits, POV selection, minimum expert reward, replay-level split, preparation
settings, and training hyperparameters. Duplicate episode IDs are rejected even
when assigned to different splits, so frames from one replay cannot leak across
training and evaluation.

Preparation is intentionally separate from GPU training:

1. The shared episode-artifact downloader fetches replay plus episode metadata.
2. Each replay's declared source revision is checked out independently and its
   `nimby.lock` is synchronized before compiling the wire and action extractors.
3. Exact-source replay simulation enforces recorded state-hash validation while
   reconstructing the selected Sprite-v1 POV.
4. Episode metadata resolves the highest-reward seat (or validates explicitly
   selected seats) and enforces the manifest's reward floor.
5. Human-renderer-only entities are removed before samples are persisted;
   unknown semantics remain. The static walkability raster is deduplicated by
   content hash.
6. Each split is downsampled to its least-populated era (and an optional cap),
   then round-robined across replay trajectories so neither era abundance nor a
   long episode can silently dominate training or evaluation.
7. Small experiments retain replay-disjoint split JSONL. Exhaustive runs
   convert deterministic 512-trajectory groups to verified Arrow parts and
   delete each group's redundant JSON before proceeding. A virtual manifest
   joins those parts without copying the full corpus; provenance remains
   replay-disjoint and complete.

The Accelerate loop supports LoRA or full tuning, cosine learning-rate decay,
warmup, gradient accumulation/checkpointing, BF16/FP16/no mixed precision,
epoch validation, best and final policy saves, and resumable model/optimizer/
scheduler/RNG state. Evaluation uses the same grammar-constrained token metric
as live action decoding and reports results by GameVersion.

The initial tracked corpus manifest trains on winning agents from GV16/24/30/35,
uses complete held-out replays from those eras for validation, and reserves two
winning GV40 replays as an unseen-era test. This is a plumbing-scale seed corpus,
not enough data to support a competitive-policy claim; later manifests should
add more high-performing replay diversity without weakening replay-disjoint
evaluation.

## Current experiment and boundary

The first experiment asks whether the full semantic entity representation fits
comfortably inside Qwen's context. Its preregistration is
[`../reports/rl-observation-length-experiment.html`](../reports/rl-observation-length-experiment.html).

The semantic-entity experiment does **not** encode the compressed RGBA pixels
of the `walkability map` sprite. Treating that sprite as merely the words
"walkability map" would erase the actual navigation map. The architecture above
therefore gives the map a separate cached spatial encoder; its exact resolution
and token budget remain experimental.

### Observation-length result

The preregistered full-serialization hypothesis was **refuted**. We reconstructed
player-view streams with the exact historical simulator source, retained replay
hash validation, collected 11,168 observations, and sampled 1,000 from each of
five GameVersions.

| GameVersion | Source commit | Sampled | Median tokens | p99 | Max |
| --- | --- | ---: | ---: | ---: | ---: |
| 16 | `35fa06b` | 1,000 | 8,541 | 13,643 | 16,522 |
| 24 | `e05c731` | 1,000 | 8,760 | 15,365 | 17,634 |
| 30 | `1047232` | 1,000 | 8,825 | 16,501 | 17,169 |
| 35 | `95bb768` | 1,000 | 9,021 | 15,442 | 17,370 |
| 40 | `ec244e6` | 1,000 | 9,721 | 36,436 | 43,672 |

Global p99 was 30,297 tokens and the maximum was 43,672, so every era
missed the 8,192-token p99 criterion and the corpus exceeded Qwen's 32,768-token
context.

The falsifying diagnostic identified the mechanism rather than inferring it
from map size. Historical human views represent fog as hundreds of labeled
`fog` run objects. On the same 5,000 frames, removing only those human-only
objects reduced global p99 to 3,429 and max to 4,424. The largest raw frame had
836 entities, 804 of them fog; its length fell from 43,672 to 2,052 tokens.
This diagnostic does not change the preregistered verdict, but it motivated the
source-derived bot-semantic follow-up reported below.

Corpus provenance: three hosted episodes and two opposing POV seats per
GameVersion. The historical fields included Picasso/Focusfire (GV16),
tournament policies including Picasso (GV24), a broad field including Beacon
(GV30), Alphashot/Focusfire (GV35), and current Paintbot matches including
Stencil and the champion (GV40). Raw replays, reconstructed wire streams, and
snapshots live under ignored `paintbot/rl/data/`; the complete machine-readable
result is under ignored `paintbot/rl/results/observation-lengths.json`. The
tracked episode, Coworld, source-commit, and policy manifest is
[`../reports/rl-observation-length-corpus.json`](../reports/rl-observation-length-corpus.json).

### Bot-semantic filter result

The follow-up experiment derived its denylist independently from the current
engine's `buildSpriteProtocolPlayerUpdates(..., spritesOff=true)` branches and
reran the exact same deterministic sample. It was **confirmed**.

| GameVersion | Sampled | Median tokens | p99 | Max |
| --- | ---: | ---: | ---: | ---: |
| 16 | 1,000 | 1,478 | 2,252 | 2,608 |
| 24 | 1,000 | 1,816 | 3,332 | 3,919 |
| 30 | 1,000 | 1,632 | 2,553 | 3,247 |
| 35 | 1,000 | 1,891 | 3,419 | 4,424 |
| 40 | 1,000 | 1,781 | 3,020 | 3,239 |

Global median was 1,722, p99 was 3,178, and max was 4,424. Every
era cleared the 8,192-token p99 threshold, and the maximum leaves 28,344 tokens
of Qwen's 32,768-token context available. The paired all-label measurement
reproduced the first experiment exactly, establishing that sampling and
tokenizer state did not drift.

Decision: adopt the source-derived denylist as the canonical entity view for
the initial SFT dataset. This experiment resolved text-entity length only; the
subsequent architecture decisions above add previous action, factorized targets,
and a separately encoded walkability map. Full verdict:
[`../reports/rl-bot-semantic-length-experiment.html`](../reports/rl-bot-semantic-length-experiment.html).

## Alternatives considered

- **One token per 256 raw masks:** exact to the wire but includes contradictory
  controls and gives rare combinations little training signal.
- **One token per 108 canonical joint actions:** behaviorally clean and one-step
  to generate, but still prevents component sharing across unseen combinations.
- **Eight button-state outputs:** only 16 vocabulary entries, but requires eight
  generated tokens and allows contradictory directions unless constrained.
- **Pretrained natural-image ViT:** attractive reuse, but its visual semantics and
  resize assumptions do not match a variable-sized binary topology raster.
- **Re-encode a raw local crop every decision:** simple, but needlessly repeats
  convolution over static pixels; gathering from cached spatial features retains
  the same location dependence.

## Large-corpus training execution

The exhaustive expert replay corpus is stored for training as nested Hugging
Face Datasets Arrow shards, not as an in-memory Python list or one monolithic
Arrow copy. Arrow is the established memory-mapped path in the Hugging
Face/PyTorch stack and preserves random access for balanced sampling. The sample
payload remains the versioned JSON contract; Arrow adds only changed-action,
GameVersion, expert player ID, and world index columns. New Sprite labels
therefore do not require a storage-schema change.

The storage invariant is that no durable step requires two complete corpus
copies. Each preprocessing shard converts 512 trajectories at a time and prunes
their JSON only after Arrow count verification. The global dataset recursively
concatenates shard manifests in memory without rewriting Arrow payloads. Map
JSON is content-deduplicated once and hard-linked across splits. Interrupted
parts are idempotent: a verified Arrow part is reused, while an incomplete
temporary part is rebuilt from its still-retained source JSON.

The first full run bounds an epoch at 250,000 distinct samples. It assigns half
the budget to action transitions and half to held actions, then water-fills each
half across GameVersion, expert, and CTF/Paintbot strata. Scarce strata are
consumed and their unused quota is redistributed. This prevents both the held
action baseline and newer or higher-volume experts from dominating an epoch.
The exact budget, balance dimensions, and epoch count remain experiment knobs.

Training writes resumable state every 1,000 optimizer updates and at epoch
boundaries. A deterministic per-epoch permutation makes mid-epoch recovery
repeatable. An independent launcher waits for preprocessing, opens the virtual
Arrow corpus and builds indices, requires a complete BF16 GPU canary and validation
evaluation, then starts the full job automatically.

## Open decisions

- Exact spatial-pyramid architecture, resolution, and number of Qwen map tokens.
- Whether four compact entity deltas or short full self/nearby-state snapshots
  are the better temporal representation at larger data scale.
- Action-token embedding initialization.
- Whether the factorized autoregressive decoder meets the live decision latency
  budget; if not, the same targets can feed four parallel prediction heads.
- Full fine-tuning versus parameter-efficient tuning after the dataset size and
  available accelerator are known.
- Dataset sampling cadence, era/agent balancing weights, and how much idle-held
  action data to retain.
- Whether to initialize new action-token rows from related Qwen wordpieces or
  learn them from the default random initialization.

### Action-alignment result

The replay ordering and a direct GV40 measurement settle the initial causal
alignment. `stepReplay` loads input recorded for simulator tick `t`, advances
the world to `t+1`, and only then emits observation `O_(t+1)`. Therefore the
expert action chosen from `O_t` is the mask consumed at tick `t`; its visible
effect appears in `O_(t+1)`.

Across three GV40 episodes and two POVs each, 30,704 consecutive aim
transitions were compared against action offsets -1, 0, and +1. The zero offset
matched 30,401 transitions (99.01%) and 11,134 of 11,436 commanded turns
(97.36%). The neighboring offsets achieved 89.68%/80.66% and 89.72%/80.75%
respectively. Zero is now the dataset default. The configurable delay remains
only as an ablation hook, not an unresolved production choice.

### Initial Mac training result

The first accepted plumbing pass used LoRA, activation checkpointing, 2,048
text tokens, batch size 1, gradient accumulation 4, and 25 examples from each
of GV16/24/30/35/40. Every POV belonged to a winning policy in its source
episode. On a 48 GB M4 Pro it completed 125 batches in 550 seconds without swap
activity during the run. The first-20 mean training loss was 10.76 and the
last-20 mean was 2.31.

A disjoint five-example-per-era holdout produced 72.0% constrained component
accuracy and 8% exact-action accuracy. A training-corpus majority baseline was
71.2% and 8%, so this tiny pass validates the representation, training,
checkpoint, and autoregressive decoding paths but does **not** establish useful
observation-conditioned behavior. Full record:
[`../reports/rl-initial-sft-2026-08-06.md`](../reports/rl-initial-sft-2026-08-06.md).

The first attempted checkpoint is explicitly invalid: spaces between added
special tokens became four unintended language-model targets. Action tokens are
now serialized adjacently and verified as exactly five tokenizer IDs.

### Initial mettabox1 GPU result

The first GPU sweep trained the balanced GV16/24/30/35 corpus and kept GV40
sealed. Learning rate 2e-4 at epoch 3 won on validation loss (0.299010), ahead
of 1e-4 after four epochs (0.313784) and 4e-4 after one epoch (0.325649). The
held-out GV40 loss was 0.258066, with 94.45% constrained token and 77.13% exact
action accuracy.

Those aggregate metrics are almost entirely held-state prediction. Repeating
the previous mask scores 94.42% token and 77.06% exact on the same GV40 split;
the model exactly predicted only 1 of 309 actual action changes. Future corpus
and model selection must explicitly weight transitions and report changed-action
and per-slot metrics. Full record:
[`../reports/rl-mettabox1-sft-2026-08-07.md`](../reports/rl-mettabox1-sft-2026-08-07.md).

### Action-change weighting result

The follow-up compared changed-component weights 1×, 3×, class-balanced
(8.1768×), and 16× under the same three-epoch training contract. Weighting did
teach transitions, but only by producing many false changes. Class balance was
the validation knee: 12.1% changed-action exact versus 0% at 1×, while overall
exact fell from 69.1% to 48.6%. On held-out GV40 it reached 9.4% changed-action
exact but only 13.7% change precision and 35.3% overall exact. Weighting alone
is rejected; transition-centered sampling and temporal context are now the
next representation experiments. Full record:
[`../reports/rl-action-change-weighting-2026-08-07.md`](../reports/rl-action-change-weighting-2026-08-07.md).

### Residual event-action follow-up

Exhaustive-corpus validation logits show that 71.85% of changed-movement
examples repeat the previous movement, while only 7.76% choose a different but
incorrect direction. Excluding the prior movement token raises correct-new-
direction choice to 54.85%; an oracle movement change gate would yield 69.61%
exact action. This is a direct copycat signature rather than ordinary class
confusion.

The opt-in `events` codec therefore supervises only button transitions:
canonical releases, canonical presses, then `<STOP>`. The decoder owns previous
button state, rejects redundant/contradictory events, and reconstructs the raw
held mask. The absolute four-slot codec remains the default and the selected
codec is checkpoint metadata. Event training always reserves nine target
tokens, preventing target-length leakage through prompt truncation. Model
selection uses autoregressive generation through `<STOP>`; teacher-forced
event accuracy is not the gate. A schedule-matched one-epoch validation screen
is queued ahead of the spatial-semantics arm; neither arm can open the sealed
test. Current experiment contract and results live in
[`../reports/rl-exhaustive-baseline-2026-08-14.md`](../reports/rl-exhaustive-baseline-2026-08-14.md).

### Sealed-candidate gate

Validation and test evaluators now attest the exact sample-index SHA-256 in
their result JSON. `evaluate_sealed_candidate.py` opens the frozen test only
when validation uses the recorded index, contains exactly 10,000 rows, and is
strictly above 70% autoregressive exact action. Teacher-forced
constrained metrics remain diagnostics for old artifacts but cannot satisfy the
gate. Validation must attest the same checkpoint-tree hash, action codec,
spatial representation, and 4,096-token budget used by the sealed run. The
guard re-hashes the frozen test index, refuses to overwrite a prior candidate
result, and writes a separate pass/fail decision. This is the mechanical
boundary between model selection and the one-time sealed test.
All unattended training runners stop after frozen-validation evaluation; do not
invoke `evaluate_sft.py` directly for a new final candidate.

### Next-state/action extension audit

The proposed extension can be written causally as:

```text
O_t, A_t, A_(t+1) -> delta(O_t, O_(t+1)), A_(t+2)
```

Here `A_t` is the previously held mask and `A_(t+1)` is the action chosen from
`O_t`. The future observation target must follow that chosen action before the
following action is predicted. This is compatible with an autoregressive
trajectory model, but the transition data must contain every intervention.

The exhaustive Arrow corpus is not sufficient for the literal objective as
stored. Its observations use stride 6. In the first 100,000 physical training
rows, 99,218 adjacent rows from the same trajectory were six ticks apart; the
remaining same-trajectory gaps were predominantly 72 or 78 ticks. Each later
sample's stored history covers offsets -4 through -1, so it does not recover
all actions and state changes across the preceding six-tick gap. Treating these
rows as a one-step transition would ask the model to explain hidden intervening
actions and is rejected as a causal training contract.

The stored rows do show that a compact future target is practical. On 9,848
six-tick adjacent pairs, the existing semantic-delta serialization measured 158
Qwen tokens at median and 165 at p95, versus 909 and 3,062 tokens for the full
next observation. Full observation generation would regularly exceed the
4,096-token budget once the prompt and action targets are included. These
numbers measure compactness only; they do not make the six-tick pairs valid
world-model supervision.

If the queued diversity/event/spatial arms do not clear the autoregressive
validation gate, the next-state arm should therefore:

1. Re-extract exact tick `t+1` observations and actions from retained raw
   replays for a bounded, replay-disjoint subset of the existing train and
   validation splits. Do not derive or inspect test pairs during development.
2. Keep current-action prediction as the primary loss. Add an action-conditioned
   future semantic-delta or latent-representation objective, followed by the
   next action, with its loss weight fixed before validation.
3. Prefer a compact target over reconstructing the full Sprite-v1 text. Compare
   an inspectable semantic-delta target against a latent self-prediction target
   only as a preregistered validation experiment; do not add both at once.
4. Preserve the frozen validation index/checkpoint attestation and require the
   same autoregressive exact-action gate. Future-state loss is an auxiliary
   representation objective, never a substitute success metric.

This follows the useful part of established approaches without importing their
full machinery: Trajectory Transformer models correctly ordered state/action
sequences; Self-Predictive Representations predicts future latent states; and
Dreamer learns action-conditioned latent dynamics. For this SFT policy, a small
auxiliary target is the conservative first experiment—not a Dreamer-style
planner or full-observation language rollout.

References:

- [Offline Reinforcement Learning as One Big Sequence Modeling Problem](https://trajectory-transformer.github.io/)
- [Data-Efficient Reinforcement Learning with Self-Predictive Representations](https://arxiv.org/abs/2007.05929)
- [Mastering diverse control tasks through world models](https://www.nature.com/articles/s41586-025-08744-2)

### Transition sampling and temporal-history result

A matched 2x2 independently varied uniform versus 50/50 transition/hold
sampling and current-frame versus four-tick causal history. Sampling alone was
flat. On the natural validation distribution, history raised changed-action
exact accuracy from 0% to 7.9%; the combined arm reached 8.4% with 73.1%
change precision. The selected combined arm improved sealed-GV40
changed-action exact from 0.3% to 3.9% and changed-component accuracy from
0.7% to 8.8%, but reduced overall exact from 77.1% to 74.7% and achieved only
45.2% change precision.

Decision: retain compact causal history in the architecture. Transition
sampling remains optional because its incremental effect is small. The seed
checkpoint is not deployable; expand replay and expert diversity before
comparing the delta grammar with short full self/nearby-state history. Full
result:
[`../reports/rl-transition-temporal-2x2-2026-08-07.md`](../reports/rl-transition-temporal-2x2-2026-08-07.md).

The current live inference shell still serializes only the current frame and
previous action. Wire the rolling history buffer into `policy.py` only after a
checkpoint clears the offline quality gate; this experiment intentionally did
not package or upload a player.
