# cheater

A deliberately silly Cue-n-Woo player with one mission: get the word `goblin` to
win as many head-to-heads as possible, with a fixed deterministic policy. No
classifier, no LLM. The whole policy is two constants in [`config.py`](config.py).

> cheater is **not** [`mentalist`](../mentalist/) and shares no code with it.
> mentalist is the serious player (reads the hidden style, writes in-style prose
> to win honestly). cheater bludgeons with one word for fun. Keeping them
> code-isolated means active work on either can't break the other — hence
> cheater vendors its own [`validator.py`](validator.py).

## Strategy (v3 — the "daveey" approach)

**Always answer `"The goblin"`.** That's it. This copies the deterministic shape
that wins for `daveey-cnw-stock`, the strongest fixed bot in the field, which
answers every question with a fixed `"The <noun>"` (`"The water"`, `"The sea"`…)
and beats most opponents on that alone.

1. **`private_questions`** — asks a goblin-promoting injection
   ([`config.INJECTION`](config.py)) on all three probes. This lands in the
   `"Reference material:"` block the judge reads when scoring **every** question
   (`v2/coworld/game.py:scoring_context`) — a free nudge toward goblin.
2. **`proposals`** — open-ended questions; commits `"The goblin"` as each secret.
3. **`answers`** — blind-answers the opponent's questions with `"The goblin"` too.

### Why short beats the alternatives

The FLAS-steered Gemma judge strongly prefers **short, plain, concrete** answers.
The journey here:

- **v1** (bare `goblin` everywhere) — ~40% live win-rate; a single bare word
  loses to coherent answers.
- **v2** (long goblin-y *sentences*) — looked great on a probe vs a benign fixed
  opponent, but dropped to **30%** in live play: long/weird/repetitive is the
  *worst* profile against this judge, losing even to daveey's mediocre "The sea".
- **v3** (`"The goblin"`) — probed against **real** field answers pulled from
  replays (daveey's "The water"/"The morning"/"The sea", biglobes' descriptive
  answers), under our saturated context:

  | our answer | mean preference | wins |
  |---|---:|---:|
  | **`The goblin`** | **0.876** | **30/36** |
  | `goblin` (bare) | 0.488 | 18/36 |
  | goblin sentence (v2) | 0.274 | 6/36 |

  `"The goblin"` beats daveey's own answers **18/18** and stays competitive
  (~0.63) against longer descriptive answers. Short shape + goblin loyalty.

## Layout

- `player.py` — WebSocket loop + state-driven phase dispatch (in-flight `pending`
  guard + idempotence from state counts; the server-contract notes in its
  docstring are load-bearing).
- `config.py` — `TARGET_WORD`, the fixed `ANSWER` (`"The goblin"`), the injection,
  the proposal questions.
- `answers.py` — returns the fixed answer (clamped legal).
- `validator.py` — vendored mirror of the game's answer rules (cheater's own copy).

## Build / test / ship

```sh
uv run pytest cue_n_woo_lab/cheater/tests                    # unit tests
cd cue_n_woo_lab/cheater && docker build --platform linux/amd64 -t cheater:dev .
uv run coworld upload-policy cheater:dev --name cheater \
  --run python --run=-m --run cheater
```

**`--run` is mandatory** (upload AND local runs): without it the cue_n_woo
manifest's stub-player argv gets applied to this image and crashes
(`No module named 'v2'`). cheater needs **no** LLM backend — do not pass
`--use-bedrock` or an `ANTHROPIC_API_KEY`.
