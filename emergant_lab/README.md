# Emerg-ant lab

The Emerg-ant corner of `player_labs`: a human-in-the-loop lab for evaluating,
building, and improving Coworld players for **Emerg-ant**.

> **Status (2026-08-21): `stencil-ant:v6` remains the promoted player and is not
> submitted.** It is compatible with Emerg-ant 0.9.1 / GameVersion 57. The uploaded
> v7 crowd-aware-food experiment split the real champion 2–2 with a 60–48 delivery
> lead, but its redirect objective appeared in zero local or hosted transitions.
> V7 was therefore rejected as an unvalidated mechanism and exact v6 source restored.
> See [WORKING_CONTEXT.md](WORKING_CONTEXT.md).

## Start here

1. Read the root [AGENTS.md](../AGENTS.md) and
   [best_practices.md](../best_practices.md).
2. Read this lab's [AGENTS.md](AGENTS.md), [best_practices.md](best_practices.md),
   and [user_preferences.md](user_preferences.md).
3. Read the current [gameplay contract](docs/emerg-ant-gameplay.md).
4. Use the dated recon documents only for their matching release.

## Current game

Emerg-ant 0.9.1 is a 32-seat, two-colony artificial-life duel. Each colony begins
with a fixed queen, seven active workers, and eight reserve brood. Eight neutral food
patches replenish; delivering food to the queen hatches one reserve ant. The first
colony to 16 active ants wins. Combat is contact-only, and killing a queen collapses
its colony. Agents communicate through public typed, rate-controlled pheromones.

The canonical deployed source is
`Metta-AI/coworld-emerg-ant@1e0be3f1ecabf2fc70adb8af81818a9947281cc9`
(GameVersion 57). Exact deployment pins live in
[tools/versions.env](tools/versions.env).

## Player

The current player is a minimal adaptation of the exact GV57 canonical Nim baseline.
It preserves the known-compatible protocol, labels, and navigation, adds per-frame
telemetry, routes carriers through two offset delivery lanes, and gives the colony a
bounded queen-defense alarm. Brood keep foraging rather than joining the alarm, which
avoids the late-game overreaction observed in the rejected unbounded candidate.

```text
emergant_lab/
  WORKING_CONTEXT.md
  docs/
    emerg-ant-gameplay.md
    recon/
  emergant/stencil_ant_gv57_nim/
    Dockerfile
    stencil.nim
    VERSION_LOG.md
  tools/
    build_player.sh
    versions.env
```

Build from the repository root with `emergant_lab/tools/build_player.sh stencil-ant`.
Uploads are routine and inert; league submission remains explicitly human-gated.
