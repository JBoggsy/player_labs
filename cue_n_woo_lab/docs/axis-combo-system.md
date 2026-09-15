# Cue-n-Woo — the axis-combo concept system

The judge's hidden concept combines values from independent axes. A player
must infer that combination from feedback and produce text matching it. The
`axis_combo` configuration selects values as described below.

---

## 1. The mechanism, precisely

`game.py:select_axis_combo_concept` (config `concept_type: "axis_combo"`):

1. Load **15 axis files** from `data/concept_axes/*.json`. Each is a flat list of string
   values (a "register," a "place," an "emotion," …).
2. Sample **`concept_axis_count = 4`** distinct axes uniformly at random (default uses all 15
   axes; tournament sets no `concept_axis_names` override).
3. From each chosen axis, pick **one value** uniformly at random.
4. The hidden concept is those 4 values **joined with `"; "`**. Example from the live episode:

   ```
   "technical; evidence-first; frontier town; sterile"
     register=technical · rhetoric=evidence-first · time=frontier town · sensory=sterile
   ```

   The judge (still Gemma-2-9B-IT, FLAS-steered, `flas_steps=3`, `flas_flowtime=2`,
   `temperature=0.7`) is steered toward that blended concept and answers/scoring run against it.

The phase sequence is three private asks, three proposal question/answer pairs,
three blind answers and scoring. Answer comparison uses both orderings of
`/choice-logprobs`; answers have a twelve-token cap.

### Axis-combination configuration

| Knob | Value |
| --- | --- |
| `concept_type` | `axis_combo` |
| `concept_axis_count` | 4 |
| `round_timeout_seconds` | 600 |
| `llm_worker_url` | `cue-n-woo-fleet.softmax-research.net` |
| `reveal_concept_to_clients` | false |

Resolve these values from the selected manifest before evaluation. The engine also
supports other concept types; they do not share the axis-combination inference problem.

## 2. The 15 axes (concept dimensions)

326 values total across 15 axes. The full lists live in
`data/concept_axes/<axis>.json`; counts and flavor:

| Axis | # | What it controls | Sample values |
|---|---|---|---|
| `register` | 16 | tone/formality | terse, clinical, poetic, technical, devotional, luxurious |
| `syntax` | 16 | sentence shape | short clipped, numbered sections, archaic diction, bullet rhythm |
| `rhetoric` | 16 | argument style | evidence-first, Socratic, proverb-filled, contradiction-hunting |
| `cognition` | 16 | thinking style | forensic, taxonomic, paranoid pattern-matching, probabilistic |
| `epistemology` | 16 | basis of belief | data-driven, mystical conviction, legal standard of proof, Bayesian |
| `morality` | 16 | value frame | duty, fairness, efficiency above all, divine judgment |
| `social` | 16 | stance to reader | deferential, conspiratorial, adversarial, customer-service polite |
| `persona` | 16 | speaker identity | noir detective, patent attorney, monastic scribe, ship captain |
| `emotion` | 12 | mood | suspicious, wistful, smug, reverent, indignant |
| `genre` | 30 | text type | police procedural, investor memo, sermon, ship log, patent filing |
| `domain` | 30 | subject field | finance, astronomy, maritime law, horology, epidemiology |
| `sensory` | 30 | physical texture | metallic, antiseptic, candlelit, sterile, honeyed |
| `time` | 24 | era/setting | Victorian London, frontier town, cyberpunk alley, orbital paperwork |
| `object` | 36 | recurring motif | brass key, lighthouse, pocket watch, signal flare, hourglass |
| `place` | 36 | locale | deep-sea lab, courthouse hallway, planetarium, oil rig |

**Combinatorial size.** Choosing 4 of 15 axes and one value each =
**≈287 million distinct concepts** (vs. 61 before — ~4.7-million-fold larger). Per-concept
memorization or a nearest-neighbor library is dead. But note the space is **factored**: only
~326 atomic values exist, and each concept is a small set of them. A tractable classifier is
**per-axis** (which value on each present axis), not whole-concept.

## Policy implications

Infer the selected axis values from observable feedback. Separate concept inference,
question authorship and answer generation so each can be evaluated independently.
Measure the policy on the selected game configuration and current opponents; a
single-style classifier does not represent a combination of independent axes.
