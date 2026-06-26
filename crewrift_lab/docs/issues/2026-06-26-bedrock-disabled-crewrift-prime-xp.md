# Bedrock backend not reaching player containers in Crewrift Prime experience-request jobs

**Filed:** 2026-06-26 · **Reporter:** James Boggs (player side) · **Owner:** Infra / Observatory platform
**Severity:** High for LLM players — silent, not a crash. All LLM-backed behavior degrades to deterministic fallback with no error.

## UPDATE 2026-06-26 — confirmed + player-side workaround shipped

Infra review confirmed the mechanism: in **sidecar mode** the runner **strips `USE_BEDROCK`** (and direct AWS
identity) from the player container and injects **`AWS_ENDPOINT_URL_BEDROCK_RUNTIME`** + dummy creds
(`kubernetes_runner.py`). The SDK's `bedrock_enabled()` still gates on `USE_BEDROCK`/`CLAUDE_CODE_USE_BEDROCK`,
so it reports "no backend" before reaching the (working) sidecar-routing path.

**Verified live (crewborg:v62, XP `xreq_5a87445f` on Crewrift Prime):** with the player changed to also treat
`AWS_ENDPOINT_URL_BEDROCK_RUNTIME` as a Bedrock signal, `commander_started` shows
`{enabled:true, backend:bedrock, env_seen:{USE_BEDROCK:false, AWS_ENDPOINT_URL_BEDROCK_RUNTIME:true}}` and
**672 successful Bedrock calls, 0 errors**. So **the sidecar is deployed and working** for crewrift_prime XP
jobs — only the `USE_BEDROCK` flag was missing. The player-side workaround unblocks crewborg now.

**Still recommended on the platform/SDK side** (so the documented `--use-bedrock` contract holds and *all*
players work without per-player workarounds — including those still gating on `USE_BEDROCK`, e.g. the crewborg
**meeting LLM**, which remains disabled in-pod): in sidecar mode keep injecting `USE_BEDROCK=true` into the
player container (strip only real AWS identity), and/or have the SDK's `bedrock_enabled()` treat
`AWS_ENDPOINT_URL_BEDROCK_RUNTIME` as a Bedrock signal.

---

## TL;DR

In **Crewrift Prime experience-request episodes**, the player container does **not** see any Bedrock-enable
environment variable (`USE_BEDROCK`, `CLAUDE_CODE_USE_BEDROCK`) nor an Anthropic key — even though the policy
was uploaded with `--use-bedrock` (which is documented to set `USE_BEDROCK=true`) plus an explicit
`--secret-env USE_BEDROCK=true`. As a result **every LLM feature in the player silently disables itself and
falls back to deterministic logic.** A *different* user secret-env set in the same upload (`CREWBORG_LLM_COMMANDER`)
**does** reach the container, so the secret-env channel itself works — the problem is specific to the
Bedrock enablement/sidecar for these jobs. This previously worked (≈2026-06-25, "v50") after a manual sidecar
enablement for crewrift_prime XP jobs; that state appears to have **reverted** (a Terraform reconciliation was
noted as owed at the time).

## Impact

- The crewborg player's **meeting/chat LLM** falls back to deterministic on **every** meeting (observed
  184/184 meetings across a batch — see Evidence). This affects the **currently-deployed champion**, not just
  experimental versions.
- A new **gameplay-commander LLM** (in development) is likewise fully disabled in-pod.
- Failure is **silent**: no exceptions, no crashes, episodes complete normally. Without per-feature tracing it
  looks like "the LLM just isn't doing anything." Any A/B eval of an LLM feature run in these pods is invalid
  because the LLM never executes.

## Environment / identifiers

| Field | Value |
|---|---|
| League | **Crewrift Prime** — `league_a12f5172-0907-4d04-8bcb-ca02f5360e3a` |
| Game | `game_138c2a93-6166-4a2f-9cec-90486131a595` (coworld `crewrift_prime`, `cow_5e21fb01-1fdf-4441-9acc-2e0cd66832ed`, v0.4.9) |
| Job type | **experience-request episodes** (hosted episode runners; `jobs` namespace) |
| Policy | `crewborg` (player "James Boggs"); diagnostic versions **v59**, **v60** uploaded 2026-06-26 |
| Upload flags | `coworld upload-policy … --use-bedrock --secret-env USE_BEDROCK=true --secret-env CREWBORG_LLM_COMMANDER=1 --secret-env CREWBORG_LLM_MEETINGS=1 …` |
| Repro experience requests | `xreq_36815db3-4faa-4100-a11e-7d6e4d9de0fa` (1 ep, both LLMs on), `xreq_325214cc-2306-441a-8d9b-f866e6d3e851` (6 eps) |

## What the player needs (the contract)

The player uses the shared `players.player_sdk` LLM helpers. Two independent things must both be true in the
**player container** for Bedrock to work:

1. **Enablement flag:** `players.player_sdk.llm.bedrock_enabled(env)` returns true **iff** `USE_BEDROCK` or
   `CLAUDE_CODE_USE_BEDROCK` is a truthy env var. If neither is set, the SDK never constructs a Bedrock client
   and the player logs "no LLM backend configured" and uses deterministic fallback. **This is the check that is
   currently failing.**
2. **Routing + credentials (the sidecar):** the actual Bedrock call is routed to the pod's loopback Bedrock
   proxy **sidecar** via `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` (SDK support added in coworld-tools PR #12 /
   `bedrock_base_url`), backed by the sidecar's IAM credentials. (We can't even reach this step today because
   step 1 fails first.)

The `coworld upload-policy --use-bedrock` flag is documented to set `USE_BEDROCK=true` in the policy
environment (`coworld/cli.py:652`).

## Observations (evidence)

We added explicit per-feature tracing to the player so enablement is observable in-pod.

**1. Bedrock enable-flags are absent in the player container.** On every slot, the commander's startup trace
reports which Bedrock env vars it can see:

```json
"domain.commander_started": {
  "enabled": false,
  "disabled_reason": "no LLM backend configured",
  "env_seen": { "USE_BEDROCK": false, "CLAUDE_CODE_USE_BEDROCK": false, "ANTHROPIC_API_KEY": false }
}
```

This is read directly from the container's `os.environ` at runtime, with a 20×/0.5s retry to rule out a
late-populated env — all false at startup **and** after retries, on all 8 slots.

**2. The meeting/chat LLM is disabled for the same reason.** Across `xreq_325214cc…` (6 self-play episodes),
**184 meetings → 184 fallback events**, all identical:

```json
"domain.meeting_llm_fallback": { "reason": "llm_disabled", "detail": "no LLM backend configured" }
```

**3. The secret-env channel itself works.** In the *same* upload/pod, `CREWBORG_LLM_COMMANDER=1` (a plain
`--secret-env`) **is** present — the player's commander feature-gate passes and its worker starts. Only the
Bedrock-related vars are missing.

**4. It works locally.** The exact same image, run locally with real Bedrock credentials and `USE_BEDROCK=true`,
shows `commander_started {enabled:true, backend:"bedrock", env_seen:{USE_BEDROCK:true}}` and successful
`commander_call {outcome:"ok", latency_ms:~2000}`. So this is environment/deploy, not player code.

## Root-cause hypothesis (for infra to confirm)

The asymmetry — a user `--secret-env` (`CREWBORG_LLM_COMMANDER`) arrives, but `USE_BEDROCK` does not — suggests
the platform/runner **consumes `USE_BEDROCK` as a signal to attach the Bedrock sidecar and strips it from the
container env**, and for **crewrift_prime experience-request jobs the sidecar attachment is currently disabled
or misconfigured**, so neither the enable flag (`CLAUDE_CODE_USE_BEDROCK`/`USE_BEDROCK`) nor the routing
(`AWS_ENDPOINT_URL_BEDROCK_RUNTIME`) nor the IAM creds land in the player container. This matches the prior
"v50 saga," where meetings worked in crewrift_prime XP jobs only after a **manual** sidecar enablement that was
noted as not yet reconciled into Terraform — consistent with a revert.

(Filed as a hypothesis; infra owns the ground truth on how `--use-bedrock` is translated into pod spec for
experience-request jobs.)

## What we need from infra

1. Confirm whether the **Bedrock sidecar is attached** to **crewrift_prime experience-request** episode pods,
   and whether the player container receives `USE_BEDROCK`/`CLAUDE_CODE_USE_BEDROCK`, `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`,
   and working IAM credentials.
2. **(Re-)enable and persist** that configuration for crewrift_prime XP jobs (the v50-era enablement appears to
   have reverted; please land it in Terraform so it survives reconciliation).
3. Clarify the intended contract for `--use-bedrock` on `upload-policy` for XP jobs: does it set `USE_BEDROCK`
   as a readable container env var, or is it consumed/stripped to gate the sidecar? (This determines whether the
   player should rely on `USE_BEDROCK` at all, or detect Bedrock some other way.)

## How to verify the fix (one episode)

Re-run a single Crewrift Prime experience request with policy **`crewborg:v60`** (already uploaded; it has both
LLMs enabled and the diagnostic tracing on, via `CREWBORG_TRACE_GROUPS=commander,llm,meeting,voting`). Pull the
episode artifacts and check the player telemetry:

- **Fixed** ⇒ `domain.commander_started` shows `enabled:true, backend:"bedrock", env_seen.USE_BEDROCK:true`, and
  `domain.commander_call` events with `outcome:"ok"` + latency; **and** `domain.meeting_llm_fallback` events
  disappear (replaced by `domain.meeting_llm_*` success traces).
- **Still broken** ⇒ `env_seen` stays all-false / `meeting_llm_fallback "no LLM backend configured"` persists,
  and the `env_seen` values point to exactly which var is missing.

The player side will confirm and report back once the change is live.
