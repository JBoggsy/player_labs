# mentalist-v4 — version log

The SDK-based rewrite (policy name `mentalist-v4`, distinct from the legacy
`mentalist` policy whose log is `../mentalist/VERSION_LOG.md`). Each uploaded
policy version → the change it carries; the canonical id is the policy-version
UUID from `policy_lifecycle.py versions --name mentalist-v4`.

Internal "vN" design-iteration names (v4…v9 in `TENTATIVE_LESSONS.md`) do NOT
equal the uploaded version numbers — the upload counter started at v1 for the
first `mentalist-v4` upload. This table maps the two.

| Upload | Design iter | Change | Notes |
|---|---|---|---|
| v1 | v4 | Passphrase offense (fresh per-episode plant+retrieve) + Titan fingerprint feeding defensive leads only. SDK `run_message_bridge`. | Gate-1 clean; matched eval 26% — beat the weak field, lost 0% to every passphrase author (bug: generic random plant values are concept-blind; opponents out-answer on quality). |
| v2 | v5 | LLM writes **in-concept** plant values (fingerprint → committed value). | REGRESSED to 24% — in-concept values came out LONG; judge strongly prefers SHORT. Terseness > richness. Not submitted. |
| v3 | v6 | **Fingerprint-core**, passphrase stripped. Fingerprint the style (3 probes → Titan match), author style-discriminating Qs, answer terse + in-concept. | BREAKTHROUGH: 62% vs field (from 26%/24%); beat the passphrase authors it used to lose to. First competitive version. Submitted; became Competition champion for a time. |
| v4 | v7 | **One-word** answers formatted as "The {word}"; fingerprint guesses passed to the LLM with calibrated likelihoods; confident-prepend; prompt-injection fence on opponent questions; emphasis-matching rule. | A/B beat v6 mainly on RELIABILITY (v6 timed out 67% of games, v7 28%) — the one-word path is faster (max_tokens lower). Submitted (sub_35f9a826) → qualified → Competition champion. But a clean-data eval later showed 21% win: the emphasis-matching rule caused 33 duplicate-conflicts + author word-choice was weak. |
| v5 | v8 | Writer prompt **reframed for delta-of-delta scoring**: pick the word the BASE model would NOT pick but the STEERED model loves (distinctively in-concept, not generically good). Dropped the now-invalid emphasis-echo rule (judging went context-free; priming is dead). | Gate-1 clean, more distinctive words ("The augury"/"The talisman"). Submitted (sub_33df6269) → Qualifiers. Shipped fast to capture the context-free + delta-scoring learnings; expected to be a heuristic stopgap, not the principled fix. |
| v6 | v9 | **Test-time delta scoring.** Writer returns K=5 candidate words/question; `judge_client.JudgeClient` delta-scores each (steered flas_flowtime=2 vs unsteered flowtime=0, both orderings, one batched POST to the public fleet worker), engine commits the max-delta word. Steered with OUR fingerprint guess (top-4 axis values). Graceful fallback to the LLM's first candidate if the worker is unreachable. Config: `TESTTIME_SCORING_ENABLED`, `TESTTIME_CANDIDATES_PER_Q=5`, `JUDGE_TIMEOUT_SECONDS=12`, `JUDGE_MAX_CALLS=12`. | Gate-1 clean (2026-06-16): full pipeline fired, candidate scores separate cleanly (obvious answers ~0, surprising-but-steered words win), "The smudges" beat "The rejoinder" 69→41. The measured version of v8's heuristic. Time-tight A/B vs v8 (64 eps, 8 opponents, 0 timeouts): v9 50% win / mean 320 / margin −20 vs v8 44% / 247 / −164 — but this A/B is **VOID**: both v5 and v6 were uploaded WITHOUT `--use-bedrock`, so the hosted pods ran `backend=none` + Titan `NoCredentialsError` → 1 fallback word repeated 6× (test-time scoring a no-op). Submitted (sub_2d9406d1) but **brain-dead in the league**. Superseded by v7. |
| v7 | v9 (fixed) | **Same image as v6, re-uploaded WITH `--use-bedrock`.** No code change — fixes the silent regression where v5/v6 uploads dropped the flag and disabled the LLM + Titan in the league pod. | Verified live (2-ep XP): pod logs show `backend=bedrock haiku-4-5`, `submit_candidates ok 1.1–1.6s`, candidate count = 5, `fingerprint backend:titan` with confident guesses — the strategy actually RUNS. Beat daveey 424-236 & 334-326. **Submitted (sub_e09a9795)**, placed, champion, climbed to rank 6. ★ Every mentalist upload MUST include `--use-bedrock`. Real baseline: 58% vs field; only loses to the 3 flooders. |

## Strategy-variant candidates (separate policy names, one shared codebase, ARG-baked mode)

The goal-driven loop (become #1) spawned env-selected strategy variants of the same image
(`config.STRATEGY_MODE` etc., baked via Docker ARGs). Race results vs the live Competition field:

| Policy | Mode | Result | Verdict |
|---|---|---|---|
| `mentalist-v4-rare:v1` | LLM proposes obscure/archaic candidate words, delta-scored | 67% race / beats all non-flooders, still loses flooders | best *player* profile; loses floppers |
| `mentalist-v4-flood:v1` | fixed "palimpsest" everywhere | 64% / sheds non-flooder margin | control; pure fixed-word worse than rare |
| `mentalist-v4-basket:v1` | rare + seed candidate pool with curated phlogiston-class words | 28% (flooder-weighted) / failed floppers | offline "vs neutral" ≠ live head-to-head |
| `mentalist-v4-floodaware:v1` | detect flood word in opponent question → echo-to-tie | failed: flood word is in their ANSWER, undetectable | no runtime signal; dead end |
| `mentalist-v4-multibase:v1` | score candidates vs neutral+goblin+phlogiston, max-of-min | failed floppers live (coin flip vs real shared concept) | right idea, but no word beats phlogiston |
| **`mentalist-v4-superflood:v1`** | **flood "The phlogiston" ×8 on every answer** | **30-8-0, ZERO losses, mean 556 vs 66; sweeps field, ties gabby 240-240** | **CHAMPIONSHIP — submitted (sub_9ff7d378)** |

Key finding chain: the field's top is fixed rare-word flooders; "phlogiston" is the dominant
token (no different word beats it, even quintessence loses head-to-head); repetition is the
tiebreaker (x8 beats gabby's x4 @0.81, but same-word → duplicate-conflict tie in practice).
Super-flood adopts the league's dominant strategy and out-repeats the incumbent → beats
everyone gabby beats, ties gabby. Full reasoning in `../TENTATIVE_LESSONS.md`.
