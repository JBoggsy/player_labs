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

## Status (2026-06-12, session 2): mentalist v1 QUALIFIED — CHAMPION in the Competition division

The player ([`mentalist/`](mentalist/)) is implemented per the design, passed Gate-1
(cert smoke + a real-config local episode against the live worker), was uploaded as
**`mentalist:v1`** (policy-version UUID `9fcac03b-a8b8-4195-8402-7c887a7574c0`),
submitted to the live Cue N Woo league, and — after we diagnosed and hotfixed a
league-side IAM bug that was disqualifying every entrant (see incident section below) —
**qualified on resubmission and was promoted to CHAMPION** (membership `lpm_8f547834…`,
division Competition `div_82c69031…`, `status=competing`, `champion=True`, ~20:50Z).
The session goal (*upload a policy and have it qualify*; human-set, authorized the league
submission and the naming/scope decisions below) is **met**.

**Environment:** git worktree, branch `worktree-cue-n-woo-lab`, dir
`.claude/worktrees/cue-n-woo-lab`. Run everything from the worktree root.

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

1. **Qualification of the resubmission** — new membership in Qualifiers (`qualifying`);
   qualifier ereq `ereq_c096e209…` running as of 20:40Z. Monitor:
   `policy_lifecycle.py monitor --name mentalist`. If it crashes again, pull
   `/jobs/{job_id}/artifacts/logs` (game-container logs; not covered by the
   episode-artifacts skill).
2. **Metta TF reconciliation** — replace the IAM hotfix with the proper Terraform change
   (see the incident doc) and tell the metta/tournament owners (role authored by
   nishu-builder, PR #10428; game by Kyle Herndon).
3. **v2 candidates (human direction needed):** runtime self-scoring via the public worker
   (design §6); ablate style-label vs transcript; proposal-bank tuning. Propose-and-pause.
4. The human still owes a review of `docs/designs/player-design.md` and the name
   `mentalist` (adopted under the goal directive; trivially renameable before it matters).

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness
gate. **Propose-and-pause.** Change one component per iteration. Gate 1 (yours, every
iteration): smoke/correctness, never comparative. Gate 2 (human's, rare): league
submission — *this session's submission was explicitly authorized by the human's goal.*
