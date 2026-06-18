# Cue-n-Woo — the new axis-combo concept system (2026-06-15)

**What changed and why mentalist is losing.** The game's hidden-concept mechanism was
replaced. The judge is no longer steered toward **one of 61 named writing styles**; it is
now steered toward a **combination of values drawn from 15 independent "axes."** mentalist's
keystone component — a 61-way style classifier — is now solving a problem that no longer
exists, and the whole player's strategy (identify the style → write florid in-style prose) is
mis-aimed at the new judge. This doc is the ground-truth reference for the new system.

> Sources (all verified this session, not inferred):
> - Live replay `hidden_concept` + `config_public` from a fresh league episode
>   (job `a36f76ff`, 2026-06-15 17:07Z).
> - Current game source `Metta-AI/cue-n-woo@545ec46` (`v2/coworld/game.py`,
>   `v2/coworld/data/concept_axes/`, `coworld_manifest.json`).
> - 5 most-recent mentalist:v3 league episodes' `results.json`.

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

**Everything else about the game is unchanged**: same 4-phase flow (3 private asks → 3
proposal Q&A pairs → 3 blind answers → reveal), same `/choice-logprobs` both-orderings
scoring, same 12-token answer cap, same duplicate-conflict and beat-bonus rules
(`answer_score` is byte-for-byte the prior logic). **Only the concept-selection step changed.**

### Other config deltas (tournament `default` variant)
| Knob | Old | New |
|---|---|---|
| `concept_type` | `list` (61 styles) | **`axis_combo`** |
| `concept_axis_count` | — | **4** |
| `round_timeout_seconds` | 300 | **600** (10-min rounds) |
| `llm_worker_url` | `cue-n-woo-worker…` | **`cue-n-woo-fleet.softmax-research.net`** |
| `reveal_concept_to_clients` | (n/a) | **false** (concept hidden from live `state`; still in replay) |

The other `concept_type` modes (`list`, `specific`, `random`) still exist in code, but the
deployed league runs `axis_combo`.

## 2. The 15 axes (the new "role" taxonomy)

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

## 3. Why this kills the current player (evidence)

mentalist:v3 is the league **champion** but sits **rank 3/3** — and James's read is right:
the standing (a WEMA over ~last-20 games) **already reflects the LLM player**; Bedrock has been
working. The losses are strategic, not infra. Across the 5 latest episodes mentalist
**lost 4/5**, e.g. 42.6 vs 617.4 (biglobes), 118.9 vs 541.1 (biglobes), ~210 vs ~450 (kyle v4).

Two failure modes, both visible in `results.json`:

**(a) The classifier is guessing.** On the `technical/evidence-first/frontier-town/sterile`
concept, mentalist's classifier reported its top-3 as
`minimalist haiku-like prose 0.354 | urban planning report 0.347 | religious sermon 0.341` —
three unrelated 61-list styles in a dead heat at ~0.35. The true concept isn't in the list at
all, so the TF-IDF NN returns near-uniform garbage. Under the old system the same classifier hit
95–97% top-1 with clean separation. **It has no valid target anymore.**

**(b) The judge now rewards concrete, terse, on-topic nouns — not florid prose.** This is the
decisive pattern. The opponents answer the cue/object axes literally and win crushingly:

| Question (opponent-authored) | Opponent secret answer | mentalist blind answer | judge p(secret) |
|---|---|---|---|
| "What image should the quiet doorway cue point to?" | **"A brass key"** | "Threshold stone worn smooth by countless passages…" | 0.95 |
| "…the evening signal cue point to?" | **"A green lantern"** | "Dusk settling between buildings, lamplight…" | 0.92 |
| "…the folded map cue point to?" | **"A train ticket"** | "Creased paper showing routes through unmapped…" | 0.999 |

mentalist writes long evocative phrases that *gesture at* a style; the winners name the
concrete `object`-axis value in 2–3 words. The first-differing-token scoring rule (unchanged)
rewards the terse concrete token landing first. mentalist's prose buries any signal under
generic literary throat-clearing — `secretP` of 0.00–0.17 on its own authored questions.

Note also the opponents author **questions tailored to the object/place axes** ("what image
should the *cue* point to") — they're probing and exploiting specific axis values, the literal
"Cue" in Cue-n-Woo. mentalist authors generic open prompts ("free afternoon," "crowded room")
that no longer discriminate, because the concept isn't a single coherent persona to play to.

## 4. Implications for the rebuild (not yet a decision — direction)

The probe-era conclusion still holds in spirit — *a good, on-topic answer phrased in the
judge's style wins; pure style markers lose* — but "style" is now **a 4-tuple of axis values**,
and the winning phrasing is markedly **more concrete and terse** than v1/v2's prose. Concretely:

1. **Replace the 61-way classifier with per-axis inference.** From the 3 private answers,
   infer the most likely value on each *present* axis (you don't know which 4 axes are live, so
   score all 15). This is 15 small independent classification problems over 326 known strings —
   still cheap, still LLM-free-capable, and it *matches the generative process*.
2. **Re-tune the writer toward concrete + terse.** The current prose loses to 2–4-word
   literal answers. Feed the inferred axis values (esp. `object`/`place`/`domain`) to the
   writer and bias hard toward naming the concrete thing early, within the 12-token cap.
3. **Author axis-exploiting questions.** Winners ask "what image should the <cue> point to" —
   questions whose style-favored answer is a specific axis value an uninformed opponent can't
   guess. Generic open questions are now duplicate-conflict / low-discrimination traps.
4. **Re-probe the fleet worker** (`cue-n-woo-fleet…`, new URL) to re-measure: per-axis
   classification accuracy from 3 questions, and which axes are most/least learnable and most
   point-leveraged. The old probe findings predate axis_combo — re-run before committing.

**These are directional; the human picks the build target (one component per iteration).**
The single highest-leverage first move is almost certainly **#1 + #2 together as one writer
overhaul**, since the classifier output currently feeds a writer that's also aimed wrong — but
that's a Gate-2-relevant call to make deliberately, not in this report.
