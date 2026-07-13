# ctf_lab

The **CTF** corner of [player_labs](../README.md) — where we build, evaluate, and
improve player policies for **Coworld CTF**, a two-team capture-the-flag shooter on the
**BitWorld Sprite-v1** protocol.

This README orients newcomers (human or agent). Two pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the improvement
  loop in CTF terms, the player build paths, and the lab's practices. Read it to *work*
  here.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory auth) and
  the ground rules.

> **Status (2026-07-10): first player `beacon` built and competing.** The game repo
> (`Metta-AI/coworld-ctf`) is cloned for reference at `~/coding/coworlds/coworld-ctf`.
> **`beacon` (Python, at [`ctf/beacon/`](ctf/beacon/)) is uploaded and submitted to the
> CTF league** (currently `beacon:v5`) — it dominates the co-gas opponents (20-0, by
> capture) and, as of v5, takes games off the elite Nim `ctf-baseline-16` too (4-11, via
> carrier escort). Live state + open threads: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md);
> version history: [`ctf/beacon/VERSION_LOG.md`](ctf/beacon/VERSION_LOG.md).

## The game (one paragraph)

CTF is an **8-v-8 capture-the-flag shooter** on the **Sprite-v1** protocol (the engine
streams a labeled sprite scene; the player emits an 8-bit gamepad mask — no semantic
action API). Two teams (**Red** left, **Blue** right) spawn in a symmetric, cover-dense
arena, each guarding a flag on a home pedestal. You **move** with the d-pad, **aim** a
continuous angle *decoupled from movement* (B/Select rotate it), and **shoot** an
instant hitscan gun (A). Vision is **fog-of-war**: the static map is always visible, but
enemies only appear inside your **forward vision cone** (±45° around your aim) or a small
**omnidirectional bubble**. Steal the enemy flag and carry it home — or wipe the enemy
team — to win. **Scoring is win-only: +100 to the winning team, 0 otherwise** — so the
objective is purely **team victory**, not kills.

**Full game reference — rules, arena, aim/vision/combat mechanics, the wire protocol,
exact tuning numbers, the baseline bot, and strategy — is
[`docs/ctf-gameplay.md`](docs/ctf-gameplay.md).** Read that to understand the game
without leaving the repo. The authoritative source is the **`Metta-AI/coworld-ctf`**
repo (Nim server `src/ctf.nim`, rules `docs/RULES.md`, baseline `players/baseline/`).

## The opportunity, in brief

CTF is a **fork of Crewrift**: it keeps Crewrift's continuous movement, line-of-sight,
Sprite-v1 protocol, and replay infrastructure, and swaps social deduction for teams,
guns, flags, and fog-of-war. That makes the cheapest path to a competitive player a
**Python Player-SDK policy on the SDK's SpriteV1 bridge** (`run_sprite_bridge`),
borrowing Crewrift `crewborg`'s perception decoder + movement controller and Heartleaf
`cady`'s bridge wiring, with CTF's own decision layer (aim/vision management, roles,
flag logic). The bundled **Nim `baseline`** bot is a strong, fully-featured reference to
beat. Which build path to pursue is a human-direction call — see
[`AGENTS.md`](AGENTS.md#player-build-paths).

## Layout

```
ctf_lab/
  README.md                       this file
  AGENTS.md                       operating model: the loop in CTF terms, build paths
  WORKING_CONTEXT.md              live cross-session state — read first
  best_practices.md               CTF-specific practices (near-empty until lessons graduate)
  TENTATIVE_LESSONS.md            this session's candidate-lessons buffer (auto-rotated)
  ctf/beacon/                     THE PLAYER — Python Player-SDK SpriteV1 policy (see below)
  docs/
    ctf-gameplay.md               self-contained game reference (rules, protocol, tuning, strategy)
    designs/ctf-player-v1-design.html   beacon's strategic/tactical design
  tools/
    build_player.sh               build the beacon image (linux/amd64)
    versions.env                  pinned SDK + game refs for builds
    build_expand_replay.sh        build version-matched replay readers (human + JSONL)
    expand_replay_json.nim        JSONL event emitter (feeds the warehouse)
    event_warehouse.py            build a DuckDB/Parquet event warehouse from episodes
    agg_eval.py                   aggregate an eval results dir into a scoreline
    rotate_lessons.sh             SessionStart hook (archive the lesson buffer)
  .claude/skills/
    ctf-event-warehouse/          build + query the event warehouse (deep-dig analysis)
    lessons-review/               the ≈weekly lessons-graduation skill
  lessons_archive/                rotated per-session lesson buffers
```

The player policy lives at `ctf_lab/ctf/beacon/` (a deterministic Player-SDK SpriteV1
cyborg — perception / belief / strategy / nav / action modules, offline-baked nav in
`mapdata/`, tests, and a Dockerfile), mirroring `crewrift_lab/crewrift/` and
`heartleaf_lab/cady/`.

The full evaluate → report → improve → submit cycle, and which skill drives each step, is
in [`AGENTS.md`](AGENTS.md) (CTF layer) and [`../AGENTS.md`](../AGENTS.md) (the loop).
