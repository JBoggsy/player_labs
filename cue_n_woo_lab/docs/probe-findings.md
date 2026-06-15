# Cue-n-Woo — probe findings (worker spike, 2026-06-12)

What we learned by probing the live FLAS/Gemma judge worker directly, before
building a player. The goal was to settle one decision: **can the player be
LLM-free, and where does the edge actually come from?** Probe code lives in
[`../probe/`](../probe/) and is reproducible.

## Setup

The judge worker (`https://cue-n-woo-worker.softmax-research.net`) is **live and
serves unsigned requests** (Gemma-2-9b-it on an NVIDIA L4, no VPN/auth needed) — so
we can probe `/generate` and `/choice-logprobs` directly, no game and no local GPU.
It is **slow and shared** (~1 generation / 10s at 128 tokens), which shaped how the
probes batch and cache. The scoring reproductions match the game referee's exact
prompt construction and both-orderings averaging (`game.py:option_selection_probs`).

## Finding 1 — Steering is strong and visually distinctive

The three sampled styles (pirate / legal / noir) produced unmistakable, well-separated
text. Style classification is clearly *tractable*; the open question is only how cheap
a classifier can be (see Finding 4).

## Finding 2 — Cheap word-only classification is mediocre; the misses are neighbors

A pure-python TF-IDF nearest-neighbor over one short (48-token) reference answer per
style, **word-only featurizer**, classified a fresh draw across all 61 styles at:

- **top-1 = 31%, top-3 = 57%** (vs 21% top-1 for the naive answer-vs-descriptor baseline).

Every miss was a *semantic neighbor*: noir→gothic/melancholic, legal→safety-compliance/
executive-briefing, therapist→cooking-show/forum-post. Two caveats make this a **floor,
not a ceiling**: (a) the featurizer lowercased and dropped ≤2-char tokens — discarding
case, punctuation, and function words, which is exactly where *style* lives; char
n-grams should do far better; (b) it used **1 question at 48 tokens**, where the player
gets **3**. The char-n-gram / 3-question ceiling is measured separately (Finding 4).

## Finding 3 — Topicality dominates; style is a tilt, not a trump (the key result)

Reproducing the real per-question scorer, we compared three answer types under the true
style (n=10: 5 styles × 2 challenge questions), where the answers were judge-generated
and truncated:

| Matchup | avg "secret" prob | win rate |
|---|---|---|
| off-topic in-style **vs** on-topic plain | **0.04** | **0%** |
| on-topic in-style **vs** off-topic in-style | 0.93 | 100% |
| on-topic in-style **vs** on-topic plain | 0.45 | 60% |

Then a cleaner test (`probe_style_leverage.py`): fixed question, a menu of short,
early-diverging candidate answers each crafted for a different style, scored under many
steered styles. Diagonal hits (does a style prefer its *own* candidate?):

- Q "free afternoon": **4/5** (pirate 0.81, zen 0.74, noir 0.61, neutral 0.96).
- Q "difficult problem": **3/5**.
- Q "good meal": **1/5** — the plain-sensible "simple bowl of rice" answer beat every
  style's own candidate, even under that style's steering (pirate preferred it 0.55 vs
  its own "hardtack and grog" 0.01).

**Synthesis — the load-bearing conclusion:**
- **Pure style markers lose** (off-topic style: 0% win). A template/style-only answerer
  is dead on arrival.
- **Style modeling has real, often decisive value — but only as a *tilt* on top of
  answer quality.** When the style-matched answer is *also a good answer to the
  question*, steering reliably makes it win (Q "free afternoon", 4/5). When a
  style-flavored answer is a *poor* response (gross meal, silly problem-solving),
  steering can't rescue it and a universally-sensible answer wins regardless of style.
- **The winning answer = a genuinely good, on-topic answer *phrased in the judge's
  style*.** Both ingredients are required.

## Finding 4 — Cheap classification is near-perfect with 3 questions

Offline bake-off (`classify_offline.py`) over a cached library (61 styles × 3 questions,
held-out separate temp-0.7 draws for refs vs tests). Top-1 / top-3 accuracy:

| featurizer | 1 Q | 2 Q | 3 Q |
|---|---|---|---|
| word_lower | 46% / 62% | 85% / 98% | 92% / 98% |
| **word_raw** (keep case+punct) | 43% / 56% | 85% / 95% | **97% / 98%** |
| char_3_5 | 46% / 62% | 87% / 97% | 95% / **100%** |
| combined | 48% / 62% | 87% / 97% | 95% / **100%** |

**The driver is question count, not the featurizer.** One question is mediocre (~45%);
**three questions reach ~95–97% top-1 and ~100% top-3**, and word/char/combined are all
within noise of each other. The earlier "31%" (Finding 2) was the one-question artifact.

Conclusion: **the no-LLM classifier is validated** — cheap, zero runtime cost, and even a
wrong top-1 is essentially always a top-3 near-neighbor that still answers fine. Pick a
simple featurizer (`word_raw` or `char_3_5`) over all 3 private questions. A single ref
draw per style already gives this; multi-draw libraries can only help.

## Implications for the player build

1. **Classifier as keystone: yes.** Identifying the hidden style cheaply is valuable and
   tractable. Exact top-1 is not strictly required — a near-neighbor still yields the
   right "stylistic neighborhood" for answering.
2. **A fully LLM-free *answer* path looks weak.** Answers must be good, on-topic
   responses to *arbitrary* opponent questions — templates can't do that. This points to
   the hybrid you proposed: **cheap classifier → feed the identified style to an LLM that
   writes a good answer in that style.** The classifier removes the hardest LLM task
   (figuring out the style); the LLM does the topical heavy lifting.
3. **Proposal lever:** author *style-discriminating* questions (like "free afternoon",
   where styles split) and avoid *universal-answer* questions (like "good meal", where one
   sensible answer dominates → duplicate-conflict 40/40 trap). Target questions where our
   style-informed answer diverges from a blind opponent's generic-good answer.
4. **Answer construction matters:** short, early-diverging answers put the scored
   first-divergent token where steering has the most leverage. Avoid echoing the question.

## Reproduce

```sh
cd cue_n_woo_lab/probe
uv run python probe_classify.py --full        # Finding 2
uv run python probe_scoring.py --styles 5     # Finding 3 (answer-type matchups)
uv run python probe_style_leverage.py         # Finding 3 (style-dependence of best answer)
uv run python build_cache.py --tokens 48      # Finding 4 (slow: builds gen cache)
uv run python classify_offline.py             # Finding 4 (offline featurizer bake-off)
```
