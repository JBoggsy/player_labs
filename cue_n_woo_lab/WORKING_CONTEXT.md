# Cue-n-Woo working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
Cue-n-Woo lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight). This is *not* a log: the
full game reference, the probe evidence, and the design each live in their own doc (linked
below); this file is the one-screen "where are we and why."

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/cue-n-woo-gameplay.md`](docs/cue-n-woo-gameplay.md) →
> [`docs/probe-findings.md`](docs/probe-findings.md) →
> [`docs/designs/player-design.md`](docs/designs/player-design.md). And the lab-wide
> [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-06-13, session 3): mentalist v2 built + Gate-1 verified — FIXES the production Bedrock fallback

**The bug we found.** All 5 latest league episodes (vs kyle_policy v3) ran the
**deterministic fallback**, never Claude: every Bedrock call threw marketplace
`AccessDenied`. Root cause is NOT code (mentalist's Bedrock call is byte-identical to the
league baseline) and NOT your earlier IAM hotfix (that was the *game-container signing
key*, a different axis). It is a **stale upload**: a player pod reaches Bedrock only if
its stored `policy_secret_env` carries `USE_BEDROCK=true` under the *current* dispatch
path (runs under the `episode-runner` IRSA SA — `coworld/runner/kubernetes_runner.py`).
**metta#15616** ("Add hosted Coworld secret URIs", squash `cf8ddcc`) reworked that
secret-env dispatch and landed **2026-06-12 23:41Z** — *after* mentalist:v1's upload
(20:22Z) but the player must be **re-uploaded** to re-store its secret-env. kyle_policy:v3
(uploaded 02:58Z, tagged `purpose=bedrock_fallback_fix`) did exactly this and its Bedrock
works in the same episodes ours fails.

**The fix (v2, this session — pending upload).** Dual-backend LLM writer
([`mentalist/writer.py`](mentalist/writer.py)), the crewrift/suspectra convention: the
`anthropic` SDK over a runtime-selected transport — `USE_BEDROCK` → `AnthropicBedrock`,
else `ANTHROPIC_API_KEY` → `Anthropic` — replacing raw boto3. Re-uploading fixes Bedrock
(re-stores secret-env post-#15616); the API-key path is an infra-independent fallback.
**Gate-1 verified**: real-config local episode vs the live worker
(`--use-bedrock --aws-profile softmax`) → `LLM backend: bedrock ... ok`, genuine in-style
pirate prose (all ≤12 tokens, no rejections, no fallback), scores [579.2, 80.8], 86s. 29
unit tests pass. See [`mentalist/VERSION_LOG.md`](mentalist/VERSION_LOG.md).

**Prior status (session 2):** mentalist v1 (UUID `9fcac03b-a8b8-4195-8402-7c887a7574c0`)
qualified and was promoted **CHAMPION** in Competition (`div_82c69031…`) — but on the
crippled fallback player. v2 is the first real-LLM player.

**Environment:** git worktree, branch `worktree-cue-n-woo-lab`, dir
`.claude/worktrees/cue-n-woo-lab`. Run everything from the worktree root. Game image is
now **cue_n_woo 0.2.10** (was 0.2.1; manifest/protocol look unchanged — re-verify if play breaks).

## The league (DISCOVERED THIS SESSION — earlier "no league" notes were stale)

- **League:** `league_e28faac2-d187-4526-b73b-432c43943aed` ("Cue N Woo", created
  2026-06-08), running **cue_n_woo 0.2.1** (repo `main` still shows 0.2.0; manifest/
  protocol unchanged — verified via `/v2/coworlds/cow_74400031-…`).
- **Divisions:** Competition (`div_82c69031…`) + Qualifiers (`div_d700ca02…`, staging).
- **Commissioner:** every **30 min**, stage = 1 round / ≥1 episode per entrant,
  `minimum_champions: 2`. Submit → placed in Qualifiers → a qualifier round runs → promote
  or disqualify ("did not qualify from Qualifiers").
- **Precedent:** `kyle_policy:v1` (Kyle Herndon) submitted 2026-06-12 19:44Z and was
  **disqualified at 19:48Z** because its qualifier episode **failed game-side**
  ("Container game Error with exit code 1", `failed_policy_index: null`,
  ereq `ereq_90ebf51d…`). Risk: if that game-container crash is systemic (signing-key
  fetch? worker under load?), our qualifier fails identically — watch for it.

## The player (mentalist/) — what shipped in v1

3 fixed private questions → local TF-IDF NN style classifier (61 styles × 2 cached judge
draws shipped as `data/library.json`, ~96% top-1 per probe finding 4) → Bedrock Claude
(`us.anthropic.claude-opus-4-8`, in-style short early-diverging answers for proposals +
blind answers; fixed style-discriminating proposal bank). Deterministic legal fallbacks on
any Bedrock failure / low clock / repeated server rejections — never declines, never
crashes. State-driven WS loop (server-contract notes in `player.py` docstring).
Tests: `uv run pytest cue_n_woo_lab/mentalist/tests` (validator parity + classifier).

**Gate-1 evidence:** cert smoke PASS (fallback path exercised, clean exit); real-config
local self-play vs the live worker: complete in 96s, scores [355.7, 304.3], both slots
independently classified the same style, Bedrock worked in-container (`--use-bedrock
--aws-profile softmax`). Upload/run argv: `--run python --run=-m --run mentalist`
(without `--run`, the manifest's stub-player argv is applied to our image and crashes).

## Key operational facts

- Judge worker publicly callable unsigned: `https://cue-n-woo-worker.softmax-research.net`
  (slow + shared; batch and cache). Wire format: [`probe/worker_client.py`](probe/worker_client.py).
- Local real-config episode recipe: build an episode_request via
  `coworld.certifier.build_manifest_episode_job_spec` (variant `default`,
  `require_signing=false`, our image+run), then `coworld run-episode <manifest>
  <request.json> --use-bedrock --aws-profile softmax`.
- boto3 is NOT a repo dep (root stays game-agnostic); use `uv run --with boto3` for local
  writer experiments. The image installs its own.
- Library ↔ `config.PRIVATE_QUESTIONS` coupling is load-bearing (regenerate the library
  from live draws if the questions change — `mentalist/tools/build_library.py` reuses the
  probe cache).

## League infra incident (RESOLVED-PENDING-VERIFY, 2026-06-12 ~20:35Z)

The first submission (`lpm_dacf52a2…`) was **disqualified without playing**: every hosted
episode crashed game-side (`AccessDenied` reading the tournament signing key from S3 —
the episode-runner IAM role had no S3 permission and the bucket no cross-account grant;
kyle_policy died identically). We diagnosed it from `GET /jobs/{job_id}/artifacts/logs`
and applied a two-sided IAM hotfix from James's credentials, then **resubmitted**
(`sub_acfe6f8d…`). Full incident + the metta-Terraform reconciliation owed:
[`docs/league-infra-incident-2026-06-12.md`](docs/league-infra-incident-2026-06-12.md).

## Open threads

1. **NEXT: build + upload mentalist:v2** (the dual-backend writer) with
   `--use-bedrock` (re-stores secret-env post-#15616) — image `mentalist:v2dev` already
   built + Gate-1-verified locally. Optionally also `--secret-env ANTHROPIC_API_KEY=...`
   as belt-and-braces. Then pull one league episode's log and CONFIRM real Claude prose
   (not the `"<Style> speaking…"` fallback). Upload is routine/ungated; **submitting**
   v2 to the league is Gate-2 (human's call) — v1 is the current champion.
2. **Quantify the LLM lift.** v1 (fallback) already wins ~80% vs kyle on the style tilt
   alone; the open question is how much real prose adds. Once v2 is uploaded, run a
   matched eval v1-vs-v2 (experience requests). Expect the biggest gain on the
   mild/non-distinctive styles where the template had no floor (the v1 loss was a
   `friendly classroom teacher` game, 136 vs 524).
3. **Metta TF reconciliation** (from the signing-key incident) — replace the IAM hotfix
   with the proper Terraform change (see the incident doc) and tell the metta/tournament
   owners. Separate from the Bedrock-fallback issue, still owed.
4. **Other v2+ candidates (human direction):** runtime self-scoring via the public worker
   (design §6); ablate style-label vs transcript; proposal-bank tuning. Propose-and-pause.
5. The human still owes a review of `docs/designs/player-design.md` and the name
   `mentalist` (adopted under the goal directive; trivially renameable before it matters).

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness
gate. **Propose-and-pause.** Change one component per iteration. Gate 1 (yours, every
iteration): smoke/correctness, never comparative. Gate 2 (human's, rare): league
submission — *this session's submission was explicitly authorized by the human's goal.*
