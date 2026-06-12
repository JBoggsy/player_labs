# Cue-n-Woo — gameplay reference

The self-contained game reference for the **Cue-n-Woo** Coworld lab. Read this to
understand the game — rules, protocol, scoring, and strategy — without leaving the
repo. The authoritative source is the **`Metta-AI/cue-n-woo`** repo (game referee:
`v2/coworld/game.py`; player harness: `v2/coworld/players/baseline.py`; protocol docs:
`v2/coworld/docs/`). This doc distills `cue_n_woo` package version **0.2.0** (owner
`metta-ai`, image family `public.ecr.aws/q5f4m8t9/cogames`); the deployed league runs
**0.2.1**, whose manifest/protocol are unchanged (verified 2026-06-12 via the registry).
A **live league exists** since 2026-06-08: `league_e28faac2…` with a Qualifiers →
Competition structure and a 30-minute commissioner (see `WORKING_CONTEXT.md`).

> **Not a gridworld.** Despite shipping in the same `cogames` image family as
> among_them / cogs_vs_clips, Cue-n-Woo is a **two-player, text-only,
> theory-of-mind game**. The player exchanges JSON text messages over a WebSocket;
> there is no map, no perception, no movement. This is much closer to an LLM-judge
> prediction game than to Crewrift.

## One-paragraph summary

Two players each privately interview a hidden-persona **judge** (Gemma-2-9B-IT
"steered" via FLAS activation steering toward a secret writing **style/concept**),
then each writes three **challenge questions paired with their own answers**, and
each also **blind-answers the opponent's three questions**. The steered judge then
scores every question as a forced 2-way choice between the two answers — base points
flow to whichever answer the judge's hidden style prefers, plus a winner bonus. **You
win by modeling the judge's hidden style better than your opponent does** — both to
write answers the style favors and to author questions where your informed answer
beats their blind one. The hidden style is server-private during play and revealed
only at scoring.

## Roles and setup

- **Two player slots**, indexed `0` and `1` (default names Alice / Bob). Symmetric —
  no asymmetric roles like Crewrift's crew/imposter.
- **The judge** ("Charlie" in the original UI) is **Gemma-2-9B-IT** run on a remote
  GPU worker, *steered* by FLAS toward a hidden concept. Fixed generation knobs on the
  tournament variant: `flas_flowtime=2`, `flas_steps=3`, `temperature=0.7`,
  `judge_max_tokens=128`. The judge answers each private question "directly and
  helpfully" but *in the steered style*.
- **The hidden concept.** Default `concept_type="list"` selects one of **61 known
  writing styles** from the game's `data/concepts.json` (e.g. *"noir detective
  narration, smoky atmosphere, clipped cynicism"*, *"exaggerated pirate speech,
  nautical slang, ahoy, matey, arr"*, *"terse technical documentation"*). The full
  list is reproduced in the appendix below — **this is public information and a major
  strategic lever** (see Strategy §1). Other modes exist (`specific`, `random` FLAS
  vector) but the published **`default` variant uses `list`**.

## Phase flow

The game is a fixed 4-phase sequence with a single hard episode timer
(`round_timeout_seconds=300`, i.e. **5 minutes total** for everything). Phases advance
when **both** players have completed the current step (server-computed in
`game.py:State.phase`):

1. **`private_questions`** — each player sends up to **3** `ask` actions. Each `ask`
   is answered by the steered judge (≤128 tokens) and appended to *that player's
   private transcript only*. The opponent never sees your private Q&A. Asks are
   sequential per player: you send one `ask`, wait for the judge's answer in the next
   `state`, then ask again — so your 2nd/3rd questions can react to earlier answers.
2. **`proposals`** — each player sends one `propose` action carrying exactly **3**
   `{question, answer}` pairs. The `question` is your public challenge question; the
   `answer` is your private ("secret") answer to it. Questions become public to the
   opponent; your secret answers do not.
3. **`answers`** — each player sends one `answer` action with exactly **3** strings —
   your **blind** answers to the *opponent's* 3 challenge questions (you see only their
   question text, never their secret answer). An empty string is a **permitted decline
   that scores 0**.
4. **`reveal`** — the hidden concept is revealed, the round is scored, results and a
   replay are written, and the server closes the socket. (On the player side, seeing
   `phase == "reveal"` means the game is over — exit cleanly.)

If the 5-minute timer expires before scoring, the game finalizes with whatever has
been submitted (`status: "timeout"`).

## Wire protocol (player side)

Connect to `COWORLD_PLAYER_WS_URL` (the runner injects it; raw form is
`/player?slot=<slot>&token=<token>`). The server streams JSON `state` messages and you
reply with one action per turn.

**Observation (`state`) — key fields:**
```json
{
  "type": "state",
  "slot": 0,
  "phase": "private_questions",
  "remaining_seconds": 300,
  "limits": {"max_answer_tokens": 12, "max_question_tokens": 1024, "judge_max_tokens": 128},
  "counts": [{"chats": 0, "proposals": 0, "answers": 0}, {"chats": 0, "proposals": 0, "answers": 0}],
  "me":    {"judge": [{"question": "...", "answer": "..."}], "proposals": [], "answers": []},
  "opponent_questions": [{"question": "..."}],
  "public_questions": [[...], [...]],
  "results": null
}
```
- `me.judge` is **your** private transcript with the judge (grows as you ask).
- `opponent_questions` is populated in the `answers` phase — the questions you must
  blind-answer.
- `public_questions` is per-slot lists of each player's public challenge questions.
- The hidden concept is **never** in a live `state`.

**Actions (one per turn; server replies with a fresh `state` or `{"type":"error"}`):**
```json
{"type": "ask",     "question": "..."}
{"type": "propose", "proposals": [{"question": "...","answer": "..."}, ... x3]}
{"type": "answer",  "answers": ["...", "...", "..."]}
```

**Validation rules that bite (from `harness.py` / `game.py`):**
- **Questions** (`ask` and proposal questions): ≤ `max_question_tokens` (1024)
  whitespace tokens; normal prose whitespace allowed. Non-empty.
- **Answers** (proposal secret answers and blind answers): the strict
  *natural-keyboard* rule — ≤ `max_answer_tokens` (**12** whitespace tokens), printable
  ASCII (`[ -~]`) only, **single spaces only** (no tabs/newlines, no double spaces, no
  leading/trailing spaces), and **every space-separated token must contain ≥1
  letter/digit**. A non-empty answer must have **≥3 non-space characters**. An **empty
  string is a legal decline** (scores 0) — the *only* way to submit "nothing".
- Counts are exact: `propose` needs exactly 3 pairs; `answer` needs exactly 3 strings;
  each player gets at most 3 private asks. Phase guards reject out-of-phase actions.
- On a validation error the server returns `{"type":"error","error":"..."}` and does
  **not** advance — you retry. (The baseline harness retries up to 3× and feeds the
  error text back into the next prompt.)

## Scoring (the crux)

All scoring is in `game.py:score_round` → `answer_score` → `option_selection_probs`.
There are **6 scored questions per game**: the 3 you authored + the 3 the opponent
authored. For each question there are two answers in play — the **author's secret
answer** and the **other player's blind answer** — and the steered judge is asked to
pick between them:

> Build a prompt = both players' full private transcripts (as "Reference material") +
> all public questions + *"Choose the answer that best answers the question."* Present
> the two candidate answers as the choices and ask the **steered** judge for choice
> log-probs (`/choice-logprobs`). Do this in **both orderings** (to cancel position
> bias) and average. Result: `p_secret` and `p_opp`, which sum to ~1.

Per question, with `SCORE_SCALE=100`, `BEAT_BONUS_POINTS=10`:
- **Author** receives `100·p_secret` base, **+10** if `p_secret > p_opp`.
- **Answerer** receives `100·p_opp` base, **+10** if `p_opp > p_secret`.

So each question hands out ~100 base points split by the judge's stylistic preference,
plus a 10-point bonus to the winner (max ≈ **110** to one side). Your final score is
the sum of your base+bonus across all 6 questions (3 as author, 3 as answerer).

**Special cases:**
- **Decline (empty answer):** scores 0. A *real* answer facing a decline wins
  **uncontested**: 100 base + 10 bonus = 110. ⇒ **Never decline** a contestable
  question; a real attempt strictly dominates.
- **Duplicate / prefix conflict:** if the two answers are equal, or one is a
  case-folded prefix of the other, it's a "conflict": **both** get 50 base **−10
  penalty = 40 each**, no bonus. ⇒ Colliding with the opponent's answer is bad for the
  author — strictly worse than a clean win, and the rule deliberately punishes
  obvious/factual questions (where both sides give the same answer).
- **First-differing-token mechanic:** per the game README, the underlying comparison
  weighs the softmax probability **at the first token where the two answer strings
  differ** (averaged over both orderings). Combined with the 12-token answer cap, this
  rewards **short, in-style answers whose distinctive wording starts early** rather
  than answers that share a long generic prefix with the opponent's.

### What this means tactically
- **As author (your 3 questions):** you want `p_secret` high *and* `p_opp` low — i.e.
  questions where, *knowing the judge's style from your private interview*, you can
  give the answer the style most favors, while an opponent (who may have read the style
  differently, or for whom the style-favored answer is non-obvious) answers worse.
  Avoid factual/one-obvious-answer questions: the opponent guesses the same answer →
  duplicate conflict → you both get 40.
- **As answerer (their 3 questions):** pure style-modeling. You see only their question
  text. Answer in the judge's style, concisely, with distinctive early wording. Better
  style identification directly converts to points here.

## Players that ship in the package

Three bundled policies (all the **same image**, different `run` entrypoints — a Cue-n-Woo
player is just a process that connects to `COWORLD_PLAYER_WS_URL`):
- **`baseline-player`** (`players/baseline.py`) — the reference LLM harness. **AWS
  Bedrock Converse with Claude Opus 4.8** (`us.anthropic.claude-opus-4-8`), forced
  `submit_action` tool, `maxTokens=1024`, no temperature set. One generic prompt per
  decision (rules + transcript + observation + phase instructions); the model makes
  *every* decision and retries on validation errors. **No style-classification, no use
  of the known 61-concept list, generic questions** — it leaves a lot on the table.
- **`kyle-policy`** (`players/kyle.py`) — the baseline harness seeded with a few
  non-binding starter questions ("If you were a DnD character, what class would you
  be?", "favorite color?"). The model may ignore them.
- **`stub-player`** (`players/stub_players.py`) — deterministic offline stub for
  certification (precommitted asks/proposals, canned answers, no LLM/AWS). Used with
  `stub_worker=true` so the smoke test runs with no GPU/worker.

## The LLM worker and signing (infra context)

The judge runs on a remote GPU worker (`llm_worker_url`, default
`https://cue-n-woo-worker.softmax-research.net`) exposing `/generate` (judge answers)
and `/choice-logprobs` (scoring). The worker serves anyone at normal priority;
**tournament** episodes get queue priority via an Ed25519 signature the *game referee*
(not the player) adds, using a private key fetched from
`s3://observatory-private/cue-n-woo/tournament_signing_key`. **This is entirely
game-side** — a player never touches the worker or the signing key. Relevant to us only
as context for why hosted vs. local runs may behave differently under load.

## Config knobs (manifest `config_schema`, `default` variant)

Most are server-private or fixed by the variant; the ones that shape play:

| Knob | Default (tournament) | Effect |
|---|---|---|
| `private_questions_per_player` | 3 | private asks each |
| `challenge_questions_per_player` | 3 | proposals + blind answers each |
| `max_answer_tokens` | 12 | hard cap on answer length (whitespace tokens) |
| `max_question_tokens` | 1024 | cap on question length |
| `judge_max_tokens` | 128 | judge's answer length cap (bundle questions carefully) |
| `round_timeout_seconds` | 300 | whole-episode hard timer |
| `concept_type` | `list` | hidden style drawn from the 61-concept pool |
| `temperature` / `flas_flowtime` / `flas_steps` | 0.7 / 2 / 3 | judge generation + steering strength |
| `require_signing` | true | tournament priority guaranteed (game-side) |

## Strategy — where the edge is

The baseline is a thin, generic LLM harness. The opportunity is a **purpose-built
policy**. The biggest levers, roughly in order:

1. **Exploit the known 61-style pool.** With `concept_type="list"` (the published
   default), the hidden concept is **one of 61 publicly-known writing styles**. That
   turns the private-questions phase from "get to know a stranger" into a **61-way
   style-classification problem**. Ask 3 questions chosen to *maximally discriminate*
   among the 61 styles (questions whose answers split the hypothesis space), identify
   the style with high confidence, then write proposals and answers tuned to that exact
   style. The baseline does none of this — it asks generic personality questions and
   never references the pool.
2. **In-style, early-distinctive answering** (their 3 questions). Once the style is
   identified, answer each opponent question *in that style*, ≤12 tokens, leading with
   the most style-marked wording (the first-differing-token rule rewards distinctive
   leading tokens). This is pure, high-confidence points.
3. **Proposal-question selection** (your 3 questions). Choose questions where the
   style-favored answer is (a) something you can produce from your transcript and (b)
   *non-obvious to an opponent* — either because they may mis-ID the style, or because
   the style-correct phrasing diverges from a naive answer at the first token. Avoid
   factual/one-obvious-answer questions (duplicate-conflict trap → 40/40). Avoid
   colliding with the answer a competent opponent would give.
4. **Budget the judge's 128-token answers.** Don't bundle many subquestions into one
   `ask` — the judge may truncate and you lose information. Prefer focused questions
   that each surface a strong style signal.

### Open strategic/infra forks (for human direction)
- **Runtime LLM backend.** The baseline needs **AWS Bedrock** at runtime. Does our
  hosted player env have Bedrock creds? Alternatives: call the Anthropic API directly
  with a key, run a small local classifier model in-image, or go **LLM-free** — since
  the style set is known and finite, style classification + templated in-style answers
  could be cheap *and* strong, with no runtime LLM dependency. This is a real build
  decision.
- **How much to lean on the 61-style assumption.** Strong if the league keeps
  `concept_type="list"` with the shipped pool; brittle if they swap `concept_list_path`
  or move to `random`/`specific`. Worth a hedge (classify-if-in-pool, fall back to
  general style-mimicry otherwise).
- **Modeling the judge directly.** The judge is a *specific* known model
  (Gemma-2-9B-IT + FLAS). In principle its preferences are learnable, but the practical
  path (identify style → answer in style) likely dominates for effort/reward.

## Appendix — the 61 hidden styles (`data/concepts.json`, v0.2.0)

terse technical documentation · warm supportive therapist · skeptical scientific
reviewer · noir detective narration · exaggerated pirate speech · formal legal analysis
· children's storybook · academic philosophy · marketing copy · military field report ·
medieval fantasy chronicle · cyberpunk hacker slang · stand-up comedy · Zen minimalist
prose · financial analyst memo · Victorian letter writing · sports commentator · conspiracy
theorist · cooking show host · robotic bureaucratic formality · gothic horror · direct
executive briefing · surreal dream logic · hardboiled newspaper reporting · Socratic tutor
· emergency room triage · museum curator label · field naturalist journal · startup founder
pitch · ancient mythic epic · minimalist haiku-like prose · dry British wit · optimistic
futurist manifesto · pessimistic risk analyst · friendly classroom teacher · dense
mathematical exposition · tabloid celebrity gossip · travel guidebook · product manager spec
· religious sermon · diplomatic cable · forensic investigator report · fitness coach
motivation · luxury brand copy · old internet forum post · poetic romantic lyricism · safety
compliance manual · game designer commentary · rural folk tale · cosmic science documentary
· snarky tech reviewer · meditation instructor · courtroom cross-examination · archaeological
expedition log · radio host banter · policy think tank memo · classic adventure serial ·
melancholic memoir · precision engineering note · urban planning report · bardic tavern song

*(Full phrasings — each style is a comma-separated descriptor — are in the source
`v2/coworld/data/concepts.json`.)*
