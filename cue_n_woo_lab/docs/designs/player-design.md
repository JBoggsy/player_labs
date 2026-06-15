# Cue-n-Woo player — design

A living design doc for our Cue-n-Woo player policy. It records the architecture
we're agreeing on before writing code, the rationale, and the open questions. It
builds on the game reference ([`../cue-n-woo-gameplay.md`](../cue-n-woo-gameplay.md))
and the worker-probe findings ([`../probe-findings.md`](../probe-findings.md)) — read
those first; this doc does not repeat the rules or the evidence.

> **Status:** implemented as [`../../mentalist/`](../../mentalist/) (2026-06-12, build
> order §13.1–13.4; v2 self-scoring §6 parked). Architecture and LLM backend were decided
> by the human; the name `mentalist` and the "ship LLM-only first" scope were adopted
> under the session's goal directive and remain open to human revision. The human's
> design review of this doc is still owed.

## 1. Goal

Beat the shipped `baseline-player` (a generic Bedrock-Claude harness) and place well in
a future Cue-n-Woo league. The baseline makes every decision from one generic prompt
and never exploits the public 61-style concept pool. Our edge is **structure**: cheaply
identify the judge's hidden style, then spend the LLM's effort on the thing it's good at
— writing short, on-topic answers *in that style* — and on authoring questions that
split styles.

## 2. What the probes told us (the design constraints)

From [`../probe-findings.md`](../probe-findings.md), the load-bearing facts:

- **Topicality dominates; style is a decisive tilt on top of answer quality.** The
  winning answer is *a genuinely good, on-topic answer phrased in the judge's style* —
  not style markers alone (those win 0%), not generic-plain (coin flip).
- **Style classification is tractable and cheap** (strong, distinctive steering). A
  near-neighbor style is usually good enough for answering; exact top-1 matters more for
  the proposal phase. (Cheap-classifier ceiling: Finding 4, pending.)
- **The judge worker is publicly callable unsigned** — which we can exploit at *runtime*
  for self-scoring (see §6, optional).

## 3. Architecture overview

A thin protocol harness drives a phase-dispatched policy with three reusable services:

```
            COWORLD_PLAYER_WS_URL  (game referee)
                      │  state(phase, transcript, opp questions)
                      ▼
        ┌─────────────────────────────────┐
        │  Harness (WS loop, phase switch, │   reuse baseline.py's loop:
        │  validation-retry, clean exit)   │   connect → recv state → act → repeat
        └───────────────┬─────────────────┘
                        │ dispatch by phase
   ┌────────────────────┼─────────────────────────────┐
   ▼                    ▼                              ▼
private_questions    proposals                      answers
   │                    │                              │
   │ fixed discriminating│ style-discriminating Qs +   │ in-style on-topic
   │ question bank       │ in-style answers            │ answers to opp Qs
   ▼                    ▼                              ▼
        ┌───────────────────────────────────────────┐
        │ Services:                                  │
        │  (a) StyleClassifier  — local, cheap, NN   │
        │      over a shipped reference library      │
        │  (b) BedrockWriter    — Claude, seeded     │
        │      with the classified style + transcript│
        │  (c) AnswerValidator  — enforce game rules │
        │      locally, retry before sending         │
        └───────────────────────────────────────────┘
```

**Component boundaries are the unit of attribution** (operating model: change one thing
per iteration). Classifier, writer, question banks, and prompts are each swappable behind
a config layer.

## 4. The harness

Reuse the structure of the bundled `baseline.py`: a `websockets` loop that receives a
`state`, acts, and on `phase == "reveal"` exits cleanly (the server closes the socket on
the last action — that close is the end signal, not an error). Keep its
validation-error retry (the server returns `{"type":"error"}` and does not advance; we
fix the answer and resend, up to N tries). What changes is the **decision function**: a
phase dispatcher instead of one generic prompt.

## 5. Service (a): StyleClassifier — local, cheap, offline-built

**Job:** from the judge's answers to our private questions, return a ranked list of the
61 styles (and a confidence).

**Method:** TF-IDF nearest-neighbor against a **reference library** precomputed offline
and shipped in the image — *no runtime worker or LLM cost*.

- **Library:** for each of the 61 styles, the judge's answers to our **fixed private
  questions**, generated with the tournament steering config (`flowtime=2, steps=3,
  temp=0.7`). Store **multiple draws per style** (temp 0.7 is stochastic) and use k-NN /
  max-similarity to cut sampling noise. This is `probe/cache/` graduating into a curated
  player asset.
- **Featurizer:** settled by Finding 4. Over **all 3 private questions**, a simple
  featurizer (`word_raw` = keep case+punctuation, or `char_3_5`) hits **~95–97% top-1 /
  ~100% top-3** — and the featurizer choice barely matters; **question count is the
  driver** (1 Q ≈ 45%, 3 Q ≈ 96%). Use `word_raw` or `char_3_5` over the concatenated
  3-question fingerprint. The no-LLM classifier is validated; even a wrong top-1 is
  near-always a top-3 neighbor that answers fine.
- **Hard coupling:** the library MUST be built with the **same private questions** the
  player asks at runtime, or fingerprints aren't comparable. Question bank and library
  are versioned together.

**Fallback if cheap classification underperforms:** let the BedrockWriter also see the
raw transcript and infer style itself (it's a strong mimic); the classifier label then
becomes a *prior*, not the sole signal. We keep the classifier regardless because the
proposal phase needs an explicit style.

## 6. Service (b): BedrockWriter — Claude, seeded with the style

**Backend:** AWS Bedrock Converse, `us.anthropic.claude-opus-4-8` (the baseline's path;
confirmed working via the `softmax` profile). Forced `submit_action`-style tool or plain
text we parse; reuse the baseline's retry-on-throttle.

**Answering opponent questions (`answers` phase):** prompt Claude with (i) the
**classified style descriptor**, (ii) the **judge transcript** (real in-style examples —
strong few-shot signal), (iii) the opponent's question, and (iv) instructions to produce
a **short (≤12 token), on-topic, in-style** answer that **diverges early and
distinctively** (the scorer weighs the first divergent token; don't echo the question).
Validate locally (§7) and retry.

**Why give Claude both the label and the transcript:** the probes show style must ride on
a good on-topic answer; Claude supplies the topical quality, the style label + examples
supply the tilt. *Open question:* is the label worth much beyond the transcript for
answering? Ablate once running.

**Optional, high-value extension — runtime self-scoring (v2):** because the worker is
publicly callable, the player can, before submitting, score its candidate answers with
`/choice-logprobs` using the **classified style as the concept** — i.e. simulate the real
scorer at game time and keep the best of K candidates. The probe harness already does
exactly this (`worker_client.choice_probs`). Adds latency + an external call inside the
5-minute timer; ship the LLM-only version first, then layer this on and measure.

## 7. Service (c): AnswerValidator

Enforce the game's answer rules locally *before* sending, so we never waste a round-trip:
≤12 whitespace tokens, printable ASCII, single spaces only, ≥3 non-space chars, each
token has a letter/digit. Mirror `harness.py:validate_natural_keyboard_answer`. On
failure, feed the reason back to Claude and retry (and as a last resort, deterministically
repair: truncate, strip, collapse spaces).

## 8. Phase strategies

- **`private_questions`:** ask the **fixed discriminating question bank** (3 questions
  chosen to split the 61 styles; the same ones the library is built from). Finding 4
  confirms **fixed-3 is sufficient** (~96% top-1), so no adaptive disambiguation needed —
  keep it deterministic.
- **`proposals`:** author 3 **style-discriminating** challenge questions — ones where the
  in-style answer differs from a generic answer (the probes' "free afternoon", not "good
  meal"). For each, BedrockWriter (knowing the style) writes our in-style answer. Avoid the
  **duplicate-conflict trap** (40/40): our answer should be the style-favored one *and*
  distinctive enough a blind opponent won't match it. Optional self-scoring (§6) ranks
  candidates.
- **`answers`:** §6. Never decline — a real answer beats a decline 110–0.

## 9. Config layer

Tunable knobs live in a config module separate from logic (operating-model requirement):
private-question bank, challenge-question strategy/bank, Bedrock model id + region +
retries, classifier featurizer + k, prompt templates, `self_score` on/off and K. So an
iteration changes one knob and the next eval is attributable.

## 10. Packaging & deploy

- **Where the code lives:** `cue_n_woo_lab/<player_name>/` (vendored policy, mirroring
  Crewrift's `crewborg/`). **Player name — open.** Candidates: `mentalist` (reads the
  judge's "mind"), `styleseer`, `mimic`, `woober`. Default proposal: **`mentalist`**.
- **Image:** Python + `boto3` + `websockets` (the baseline's deps), ships the reference
  library data file, built `--platform=linux/amd64`.
- **Bedrock creds:** local = the `softmax` SSO profile; **hosted = the player pod's IAM
  role** (the baseline already invokes Bedrock from the cluster, so the mechanism exists —
  confirm the role grants `bedrock:InvokeModel`/Converse when we package). Flagged later
  detail, not a blocker for local work.

## 11. Testing & evaluation

- **Classifier:** offline accuracy on the cached held-out draws (`classify_offline.py`).
- **Writer/validator:** unit-check that generated answers pass the game rules.
- **Local integration (Gate 1):** run a full local episode with the downloaded game image
  pointed at the **live public worker** (`require_signing=false`, real `llm_worker_url`),
  our player vs the bundled `baseline`/`stub`. Confirms connect→play→exit and produces a
  **real head-to-head** — a true self-eval without the league, since the worker is public.
- **Iterate** offline/locally until clearly better than baseline; only then consider a
  hosted experience request / league submission (human's Gate 2).

## 12. Risks & open questions

1. **Classifier ceiling on near-neighbors** (noir/gothic, legal/compliance) — Finding 4
   pending; mitigated by transcript-conditioning the writer.
2. **Label-vs-transcript value** for answering — ablate.
3. **League config drift** — the library assumes `concept_type="list"` with the shipped 61
   styles and the fixed steering knobs; a swap to `random`/`specific` or a new concept
   list breaks classification. Detectable (low NN confidence) → fall back to
   transcript-only mimicry.
4. **Hosted Bedrock role** — confirm at packaging.
5. **Latency** — ~5 sequential Claude calls + classification fit easily in the 5-min timer;
   self-scoring adds worker round-trips to watch.

## 13. Build order (proposed)

1. Vendor harness skeleton + config layer + AnswerValidator (cheap, testable).
2. Finalize private-question bank + build the curated reference library; lock the
   featurizer from Finding 4; ship StyleClassifier.
3. BedrockWriter for the `answers` phase; local integration run vs baseline.
4. Proposal strategy (style-discriminating bank + writer); measure vs baseline.
5. (v2) Runtime self-scoring; ablations; tuning.
