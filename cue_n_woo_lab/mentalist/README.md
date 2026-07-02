# mentalist

Our Cue-n-Woo player policy: a **cheap local style classifier → Bedrock Claude
writer**. Design + rationale: [`../docs/designs/player-design.md`](../docs/designs/player-design.md);
evidence: [`../docs/probe-findings.md`](../docs/probe-findings.md).

## How it plays

1. **`private_questions`** — asks the 3 fixed questions in [`config.py`](config.py)
   (the same ones the reference library was generated from — that coupling is
   load-bearing).
2. Classifies the judge's hidden style with a TF-IDF nearest-neighbor over
   [`data/library.json`](data/library.json) (61 styles × 2 independent judge
   draws; ~96% top-1 per probe finding 4). Local, zero runtime cost.
3. **`proposals`** — submits the fixed style-discriminating question bank with
   secret answers written by Bedrock Claude *in the classified style*.
4. **`answers`** — Claude writes short, on-topic, in-style, early-diverging
   answers to the opponent's questions.

Every LLM path degrades to deterministic legal fallbacks (Bedrock outage, server
rejections, low clock) — the player never declines, never crashes the episode.

## Layout

- `player.py` — WebSocket loop + state-driven phase dispatch (the server-contract
  notes in its docstring are load-bearing; read them before touching the loop).
- `classifier.py` / `data/library.json` — StyleClassifier + shipped reference library.
- `writer.py` — LLMWriter: Claude via the `anthropic` SDK over a dual backend
  (Bedrock or direct Anthropic API, chosen at runtime from the pod env) + no-LLM
  fallback answers. (`BedrockWriter` remains as a back-compat alias.)
- `validator.py` — local mirror of the game's answer rules + deterministic repair.
- `config.py` — every tunable knob (question banks, model, thresholds).
- `tools/build_library.py` — regenerates `data/library.json` from the probe cache.
  **If you change `PRIVATE_QUESTIONS` you must regenerate the library from live
  judge draws of those questions** (see `../probe/build_cache.py`).

## Build / test / ship

```sh
cd cue_n_woo_lab/mentalist && docker build --platform linux/amd64 -t mentalist:dev .
# upload straight away — the next hosted eval is the test (no local smoke test)
uv run coworld upload-policy mentalist:dev --name mentalist \
  --run python --run=-m --run mentalist --use-bedrock
# (unit tests exist — uv run pytest cue_n_woo_lab/mentalist/tests — run only when
#  a test is the fastest answer to a specific question, not as a routine step)
```

**`--run` is mandatory** here (upload AND local runs): without it the cue_n_woo
manifest's stub-player argv gets applied to this image and crashes
(`No module named 'v2'`).

**LLM backend (dual).** The writer picks its Claude transport at runtime from the
pod env: `--use-bedrock` sets `USE_BEDROCK=true` so the pod runs under the
tournament Bedrock IRSA role (creds from the role; **re-upload after a Bedrock
platform change to re-store the secret-env** — a stale upload silently falls back).
Alternatively `--secret-env ANTHROPIC_API_KEY=...` selects the direct Anthropic
API (infra-independent). You may pass both as belt-and-braces (Bedrock wins). With
neither, the player runs deterministic fallbacks only — legal, never crashes, but
weak. **Debugging run that exercises the writer** (when an eval shows the LLM path
silently falling back): run a real-config local episode against the live worker —
```sh
# build an episode_request.json from the default variant's game_config with
# require_signing=false + stub_worker=false, then:
uv run coworld run-episode <manifest> <request.json> \
  --use-bedrock --aws-profile softmax --aws-region us-east-1
```
and confirm the log shows `LLM backend: bedrock ... ok` and real prose answers,
not the `"<Style> speaking, ... matters most to me"` fallback.

Version history → change mapping: [`VERSION_LOG.md`](VERSION_LOG.md).
