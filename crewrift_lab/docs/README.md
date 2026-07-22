# Crewrift &amp; Coworld reference

The ground-truth reference for the **game** crewborg plays and the **platform** it runs on — for a
coding agent that needs to look up a rule, a constant, or a protocol detail and **verify it against
the source** when something changes. Every claim is cited to a `file:Symbol` with a re-check recipe.

> **These describe the game/platform, not crewborg.** How crewborg *handles* them is in the
> [package docs](../crewrift/crewborg/docs/README.md); the disciplines for *using* them are in
> [`../best_practices.md`](../best_practices.md).

> **⚠️ Version &amp; variant — read before trusting any number.** Verified against `coworld-crewrift`
> @ `a3e2859` (`src/crewrift`, `sim.nim:GameVersion`="1"). Crewrift's constants **differ across
> variants and versions** (e.g. the deployed Prime league uses `KillCooldownTicks`=500; this repo's
> master uses 800) and are **config-overridable per episode**. The authoritative value for a game you
> are actually playing is that build's `src/crewrift/sim.nim` const block, or the episode's baked
> `game_config` — re-derive there; don't trust a hardcoded number. The deployed game ref is pinned in
> the optimizer toolkit's `versions.env` (`CREWRIFT_REF`).

## The docs

| Doc | What it covers |
|---|---|
| [crewrift-gameplay.md](./crewrift-gameplay.md) | The game as gameplay — roles, win conditions, the phase machine, mechanics (tasks / kill / vent / report / emergency button / voting), the scoring table, and the constants (each with its source symbol). Includes the meeting → kill-cooldown reset rule (body/unknown reset; the button does **not**). |
| [crewrift-protocol.md](./crewrift-protocol.md) | The Sprite-v1 wire I/O contract any player must speak — the three scene tables, camera-relative coordinates, label + object-id-range identity (no computer vision), the walkability/shadow masks, and the input encoding (button bitmask, chat, per-phase A-press semantics). |
| [crewrift-replays.md](./crewrift-replays.md) | Reading a finished game — the visual viewer vs the `expand_replay` event timeline vs policy logs; the `.bitreplay` format; the version-matched `expand_replay` build + `hash failed` recovery; slot↔policy mapping; the league-vs-experience-request episode split. |
| [coworld-platform.md](./coworld-platform.md) | The Coworld platform — what a Coworld is, the player-image contract, the `coworld_manifest.json` structure, the runner lifecycle (league vs experience-request), artifacts, roles, and the in-pod Bedrock sidecar. |
| [report-style.md](./report-style.md) | The **Ink & Print** house style for the analysis skills' HTML reports (survey / diagnose / experiment / ab) — the non-negotiables, the reusable building blocks, and how to *adapt* (not Mad-Libs) a report and verify it by looking. |
| [top3-advantage-reporter-guidance.md](./top3-advantage-reporter-guidance.md) | Methodology guidance (written for an external reporter builder) on making top-N-vs-rest differential reports find *skill*, not outcome echoes — outcome stratification, opportunity-conditioned stats, early-game panels, out-of-sample ranking, FDR — plus a verified appendix of sim/replay data-availability facts. |
| [telemetry-harvest.md](./telemetry-harvest.md) | The league telemetry harvest — `tools/harvest_artifacts.py` (idempotent, cron-able puller of crewborg's league `policy_artifact_*.zip` bundles into `telemetry_harvest/`), the crontab line, and the resolved 2026-07 "artifacts are ephemeral" retention scare (they're durable; the July-1 disappearance was a read-path/auth artifact, with metta refs). Standing consumer: `tools/harvest_liars.py` (Honor Society distrust list). |
| [bedrock-quota-ask.md](./bedrock-quota-ask.md) | **Escalation one-pager for James**: the measured Bedrock daily-token-pool contention on tournament account `583928386201` (9,102 calls → 78% fail, 99% of failures the daily-token 429; league decision coverage ~26–38%), the counterfactual (removing 429s lifts coverage to ~99%), and the concrete quota ask + verification recipe. |
| [hs1-ecosystem-notes.md](./hs1-ecosystem-notes.md) | Notes **for the HS1 spec author (Alex Smith)** from our implementation cycle — the same-key multi-seat vs first-poster-wins collision, the base64url-vs-standard encoding canonicalization stance, and spec-worthy findings (publish the compact form, pin the palette, verifier cost at scale, registry/liar-ledger interop). A document for James to send. |

> 🔌 **Debugging an LLM in a hosted episode (403, silent non-LLM fallback)?** The Bedrock runtime
> contract — the *One Rule* (route through `AWS_ENDPOINT_URL_BEDROCK_RUNTIME`, **InvokeModel not
> Converse**) + a troubleshooting table + how to check crewborg's telemetry — is in
> [**coworld-platform.md → Bedrock**](./coworld-platform.md#bedrock--in-pod-llm).

## When something stops behaving as expected

These docs exist so you can find **where to check**, not just what the value was. If the game behaves
differently than a doc says:

1. The doc names the source `file:Symbol` — open it **at the ref you're playing** (the deployed
   `CREWRIFT_REF`, or the episode's own `game_config`) and re-derive.
2. Constants are config-overridable — read the **episode's baked config**, not just the source default.
3. The platform contract lives in **metta** (`packages/coworld`) — `git pull` it (a separate,
   read-only repo) before relying on it.
