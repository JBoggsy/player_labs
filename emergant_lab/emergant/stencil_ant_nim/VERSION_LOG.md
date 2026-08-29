# stencil-ant version log

> Archived GameVersion 52 history. Current versions are recorded in
> [`../stencil_ant_gv57_nim/VERSION_LOG.md`](../stencil_ant_gv57_nim/VERSION_LOG.md).

Append one entry per uploaded version, newest first. Key every upload by stable
`name:version` and immutable policy-version UUID. Uploading is inert; submission is
always a separate human-gated action.

## v2 — Trace-contract cleanup, uploaded 2026-08-20

- **Policy:** `stencil-ant:v2`
- **Immutable version ID:** `6d7c656f-8431-49ae-9925-e4ee3c2ea0a7`
- **Created:** `2026-08-20T19:01:28.008492Z`
- **Local image:** `players-stencil-ant:dev`
- **Image ID:** `sha256:8082c39be01ed337f7c269d576297055aa56ac73b17db4f6efd09ae09a3ca0ae`
- **Platform / entrypoint:** `linux/amd64`, `/bin/stencil-ant`
- **Game source:** `Metta-AI/coworld-emerg-ant@1ea732ad68793ac25c6f888285eb90e6bccb188d`
- **Upload tags:** `purpose=emerg-ant-v2-trace-contract`,
  `game-ref=1ea732ad68793ac25c6f888285eb90e6bccb188d`

Behavior is identical to v1. This version finishes the contract migration before the
first evaluation: internal `steal` identifiers and trace reasons are now `raid`, and
the trace counters report cumulative ticks by selected objective. Use v2 for the first
hosted evaluation.

**Build evidence:** the pinned `linux/amd64` Docker build completed successfully with
Nim 2.2.6. No local play or smoke-test gate was run, per the lab contract.

**Hosted evidence:** none yet. v2 is uploaded and inert, not submitted to a league.

## v1 — Emerg-ant food-cache port, uploaded 2026-08-20

- **Policy:** `stencil-ant:v1`
- **Immutable version ID:** `1904c2fd-e303-48a0-b521-f48b0f48c4c5`
- **Created:** `2026-08-20T18:48:34.460219Z`
- **Local image:** `players-stencil-ant:dev`
- **Image ID:** `sha256:9649f93e2382b7139ee1d5fb28c379353831574f5f52fed7030b5aba775e7962`
- **Platform / entrypoint:** `linux/amd64`, `/bin/stencil-ant`
- **Game source:** `Metta-AI/coworld-emerg-ant@1ea732ad68793ac25c6f888285eb90e6bccb188d`
- **Upload tags:** `purpose=emerg-ant-v1-port`,
  `game-ref=1ea732ad68793ac25c6f888285eb90e6bccb188d`

Adapted from Paintbot Stencil v68. Retains the native retained-Sprite client,
walkability-derived map/navigation, combat, items, chat, and trace pipeline. Replaces
the objective surface with canonical Emerg-ant GV52 behavior:

- consumes `food <team> cache` / `food <team> carried` labels;
- returns carried food home, then immediately raids the replenished enemy cache;
- removes all permanent cache-retirement state and team-wipe retirement inference;
- uses a fixed eight-seat colony with three defenders and five foragers;
- records visible public pheromones by position/team/kind without following them;
- pins five lives, 1,050px gun range, and 60-degree vision half-angle;
- disables early-defense and squad-command experiments for an attributable baseline.

**Build evidence:** the pinned `linux/amd64` Docker build completed successfully with
Nim 2.2.6. No local play or smoke-test gate was run, per the lab contract.

**Hosted evidence:** none. Superseded before evaluation by v2's trace-contract cleanup;
v1 remains inert and was never submitted to a league.
