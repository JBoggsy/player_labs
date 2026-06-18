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

## GAME CHANGED: FLAS-Gemma → prompt-steered Claude Sonnet (cue-n-woo PR #20, canonical 0.2.25, live 2026-06-17)

The judge is now Bedrock Claude Sonnet, prompt-steered (persona trait list in the system
prompt) and scored by 9 forced-choice samples — **delta-of-delta and the whole flood meta are
dead**. superflood went `disqualified/inactive` (loses ~0/9 + ate league-wide timeout -100s).
The reporters were migrated to the Sonnet judge (probe rewritten, validated repro_err 0.00).

| Policy | Mode | Result | Verdict |
|---|---|---|---|
| `mentalist-v4-inject:v1` | static-phrase injection: 3 private Qs are direct-prefer notes naming a fixed committed answer ("the lighthouse keeper's ledger") | **swept nishad (#2) 660-0**; the injection biases the Sonnet judge on BOTH players' questions. (Other matchups timed out — league-wide infra, not losses.) | injection exploit CONFIRMED live |
| **`mentalist-v4-inject2:v1`** | **hardened injection: Q1 self-report → fingerprint → vivid IN-PERSONA phrase → inject toward it AND commit it** | verified vs nishad 3/3, won 398-262; two win paths (injection + persona-fit fallback) | **CHAMPIONSHIP — submitted (sub_37b03583), qualifying. Needs --use-bedrock.** |

Mechanism: game.py `scoring_context` feeds both players' private QUESTIONS (verbatim, 256-tok,
no content filter) into every `forced_choice_prompt` as "Reference material", and the Sonnet
judge follows instructions — so a direct-prefer note naming our committed answer makes the judge
pick it. The reborn passphrase exploit. CAVEAT: the live Sonnet league is timing out heavily
(judge too slow for the 600s timer); standings + evals are noisy until commissioners fix it.

### INJECTION DISPROVEN as a reliable lever; PERSONA-FIT is the strategy.

| Policy | Mode | Result | Verdict |
|---|---|---|---|
| `mentalist-v4-inject3:v1` | injection "opponent_wrong" (assert ours + discredit opponent's decoy) — the offline duel "winner" | LIVE 2-1-5, mean 176 vs 484; LOST 0-4 to michaelsmith (a non-injector on persona-fit, 600-60) | injection unreliable; offline duel probe was confounded (placeholder judge answers) |
| **`mentalist-v4-personafit:v1`** | **no injection: self-report probes → fingerprint persona → vivid in-character answer PER question (writer.persona_answers)** | racing vs michaelsmith/gabby/nishad/daveey/aaron | the correct direction — the Sonnet judge picks the most in-character answer; needs --use-bedrock |

The injection wrappers (inject/inject2/inject3) are RETIRED: the Sonnet judge largely picks the
genuinely most-in-character answer, and a planted instruction does not reliably override a real
persona-fit answer (michaelsmith, a non-injector, beats injectors). The committed in-persona
answer — which inject2/3 already generated as a "fallback" — was the part that actually worked;
personafit drops the injection and makes a tailored in-character answer per question the whole
strategy. Lab rule reconfirmed: offline probes screen but mislead; only live XP decides.

### Persona-fit progression (Sonnet era) — the working strategy

After injection was disproven, persona-fit became the strategy. Each version fixed a
diagnosed gap vs the field leader michaelsmith (the wall). Win-record vs michaelsmith:

| Policy | Change | vs michaelsmith |
|---|---|---|
| `mentalist-v4-personafit:v1` | per-question in-character answers | 0-3 |
| `mentalist-v4-personafit2:v1` | register-matched (terse/voice) | 0-7 |
| `mentalist-v4-personafit3:v1` | multi-axis + raw self-report (submitted sub_aeff8c7b) | 0-8 (188 vs 468) |
| `mentalist-v4-personafit4:v1` | axis-balance (mood>jargon) | 0-8 (250 vs 406) |
| `mentalist-v4-personafit5:v1` | michaelsmith-style rich voice-eliciting PROBES | **1**-6 (first win) |
| **`mentalist-v4-personafit6:v1`** | + voice-axis delivery (speak in the persona's manner) | **2**-6 (282 vs 374) — **submitted sub_dba7cc14** |

Biggest lever = the PROBES (rich multi-part self-characterization that makes the judge
speak in-character) — that's what got the first michaelsmith win. v6 beats the rest of
the field decisively; michaelsmith is near-parity (coin-flip) on pure-voice concepts.
Untried lever for the last gap: offline Sonnet re-rank of several candidate answers.

### ★ THE LATENCY GATE — personafit-fast (the version that actually QUALIFIES)

All persona-fit submissions (pf3/6/8, inject2) were DISQUALIFIED on LATENCY, not strategy:
league episodes timed out at 599s (8/8), score [-100,0] (we get the inactive penalty). Root
cause: our rich multi-part PERSONA_PROBES made the Sonnet judge GENERATE long answers, and our
answer-gen (25s x3 attempts) stacked on top -> past the 600s hard timer.

| Policy | Change | Result |
|---|---|---|
| `mentalist-v4-pffast:v1` | short single-part probes (judge answers <=6 words) + writer timeout 12s/1 attempt + no rerank | **9/9 episodes COMPLETE, 30-159s** (was 599s timeouts); 56% win, +103; nishad 4-0, michaelsmith 1-2. **Submitted sub_90dc0483.** |

Lesson: against an LLM judge with a hard round timer, OUR judge-facing latency is a first-class
constraint. Keep probes terse and CAP the judge's output length; a fast adequate player beats a
slow excellent one that disqualifies. personafit-fast is the first version that can qualify +
accrue a WEMA. Persona-fit quality (field-beating, ~parity with michaelsmith) is preserved.

### ★ THE QUALIFY FIX (2026-06-18): why nothing made it into the tournament + the latency fixes

ROOT CAUSE: every submission was DISQUALIFIED (status=disqualified/inactive, notes="Score <= 0").
Qualifier mean round score <= 0 because episodes TIMED OUT (-100). Episodes timed out due to a
chain of latency causes:
- (a) rich multi-part PERSONA_PROBES made the Sonnet judge GENERATE long answers, 3 sequential
  round-trips on a shared/loaded judge -> >600s. FIX: one-word-answer probes (interview.PERSONA_PROBES).
- (b) BUG: our answers exceeded the limit and were SERVER-REJECTED ("13 simple tokens; limit 12")
  -> 6 retries/episode. "Simple tokens" = ceil(len/4) CHARACTERS (<=48), our validator counted
  WORDS. FIX: validator.simple_token_count + repair_answer enforce the char budget.
- (c) too many sequential probes. MITIGATION: MENTALIST_PROBE_COUNT (pffast3=2, pfmin=1).
- (d) FLEET SATURATION (shared Sonnet judge): under load NOTHING completes regardless of our
  latency. Uncontrollable; time-varying. Verified: pffast2 completed gabby 6/6 @25-36s in a light
  window; pffast3 timed out 12/12 in a 20:xx saturation window (whole division dur=0 then).

| Policy | Change | Status |
|---|---|---|
| `mentalist-v4-pffast2:v1` | one-word probes + char-limit fix | gabby 6/6 @25-36s (light load); times out under saturation |
| `mentalist-v4-pffast3:v1` | + PROBE_COUNT=2 | **submitted sub_66cc94bb, qualifying** (outlived DQ'd pffast) |
| `mentalist-v4-pfmin:v1` | PROBE_COUNT=1 (min latency) | fallback, built |

The controllable latency is fixed; qualifying now hinges on landing a qualifier window during
healthy fleet load. Re-submit on DQ to get a fresh window.
