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

> **Status: `beacon` competing in the CTF league** (rank 3 as of 2026-07-23, v23
> champion / v24 qualifying). The game repo (`Metta-AI/coworld-ctf`) is cloned for
> reference at `~/coding/coworlds/coworld-ctf` — **the league redeploys often**; the
> deployed version at last audit is **ctf 0.7.69 (`72fb1b1`, GameVersion 21)**. Live
> state + open threads: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md); version history:
> [`ctf/beacon/VERSION_LOG.md`](ctf/beacon/VERSION_LOG.md).

## The game (one paragraph)

CTF is an **8-v-8 capture-the-flag shooter** on the **Sprite-v1** protocol (the engine
streams a labeled sprite scene; the player emits an 8-bit gamepad mask — no semantic
action API). Two teams (**Red** left, **Blue** right) spawn in a symmetric, cover-dense
arena, each guarding a flag on a home pedestal. You **move** with the d-pad, **aim** a
continuous angle *decoupled from movement* (B/Select rotate it), and **shoot** an
instant hitscan gun (A). Vision is **fog-of-war**: the static map is always visible, but
enemies only appear inside your **forward vision cone** (±45° around your aim) or a small
**omnidirectional bubble**. Steal the enemy flag and carry it home — or wipe the enemy
team — to win. **Scoring is win-only: winners +1, losers -1, and a time-limit draw is
-1 for both sides** (no tiebreak; stalling never beats losing) — so the objective is
purely **team victory before the clock**, not kills.

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
    tuning.py                     tunable-registry JSON + validated sweep-arm CLI
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

## Beacon tuning sweeps

Firefight sweep parameters are declared once in
[`ctf/beacon/config.py`](ctf/beacon/config.py): each registry entry supplies the live
config value and exposes its config name, environment variable, default, type, domain,
family, and description. Cross-knob invariants cover range geometry, target/claim
clocks, locality, and the bounded claim bias. An invalid assignment fails before an
upload command is emitted.

Dump the machine-readable registry:

```bash
uv run python -m ctf.beacon.tuning dump --family firefight \
  > /tmp/beacon-firefight-tunables.json
```

Build the image once, then upload each sweep arm with a validated assignment. The
`secret-env` command accepts config names or full `BEACON_*` names and prints the
repeatable Coworld arguments:

```bash
ctf_lab/tools/build_player.sh beacon --tag players-beacon:firefight-sweep

uv run coworld upload-policy players-beacon:firefight-sweep --name beacon \
  $(uv run python -m ctf.beacon.tuning secret-env \
    FIREFIGHT=true \
    FOCUS_CLAIMS=true \
    FF_WOUND_WEIGHT=0.60 \
    FF_RANGE_WEIGHT=0.25 \
    FF_CLAIM_WEIGHT=0.15) \
  --tag sweep=firefight-w060-r025-c015
```

Record the returned immutable beacon version and its full assignment, then create the
arm's matched hosted experience request with the same opponent, role, episode count,
and time window as the other arms. Start artifact streaming immediately, per the
root `coworld-experience-requests` workflow. Uploading is inert; do not submit a sweep
arm to the league without the human submission gate.
