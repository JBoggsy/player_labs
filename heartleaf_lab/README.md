# heartleaf_lab

The **Heartleaf** corner of [player_labs](../README.md) — where we build, evaluate, and
improve player policies for **Heartleaf**, a cozy 9-gnome garden-dinner Coworld game on
the BitWorld Sprite-v1 protocol.

This README orients newcomers (human or agent). Two pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the improvement loop
  in Heartleaf terms, the player build paths, and the lab's practices. Read it to *work*
  here.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory auth) and
  the ground rules.

> **Repository status (audited 2026-09-14):** [Cady](cady/) is implemented, with [build tools](tools/) and an [event warehouse](.claude/skills/heartleaf-event-warehouse/SKILL.md). The original scaffolding status is obsolete. Historical evaluation and deployment records are in [working context](WORKING_CONTEXT.md); re-resolve live state before operations.

## The game (one paragraph)

Heartleaf is a **9-gnome gridworld** on the **Sprite-v1** protocol (the engine streams a
labeled sprite scene; the player emits gamepad input — no semantic action API). Each gnome
gathers vegetables from shared gardens during an 8am–10pm day, then at **6pm dinner**
scores **only by *hosting*** a party at its own house that other gnomes attend:
**`score = hosted food items × number of guests`**. Visitors eat for free (and keep their
food for their own future hosting) but score nothing. So the game is **social coordination**
— recruiting a full table to *your* house over chat — on top of **efficient gathering**,
across ~9 cumulative days.

**Full game reference — rules, day cycle, scoring math, the wire protocol, the bundled
behavior framework, and strategy — is [`docs/heartleaf-gameplay.md`](docs/heartleaf-gameplay.md).**
Read that to understand the game without leaving the repo. The authoritative source is the
**`Metta-AI/coworld-heartleaf`** repo (Nim server `src/heartleaf.nim`, bundled players
`players/`).

## The opportunity, in brief

Heartleaf ships a substantial Nim behavior framework — **`talking_villager`** (~3000 lines)
— that already handles perception → pathfinding → an 8-verb semantic action layer → LLM
decision → chat. The four bundled league players (`shy_/chatty_/friendly_/fatherly_villager`)
are that *same engine* driven by different `soul.md` personality prompts. That makes the
cheapest path to a competitive player **a better prompt or a deterministic decision layer on
top of the existing engine** — not a raw protocol build. The three build paths (and their
tradeoffs) are in [`AGENTS.md`](AGENTS.md#player-build-paths); which to pursue is a
human-direction call.

## Layout

```
heartleaf_lab/
  README.md                       this file
  AGENTS.md                       operating model: the loop in Heartleaf terms, build paths
  WORKING_CONTEXT.md              live cross-session state — read first
  best_practices.md               Heartleaf-specific practices (near-empty until lessons graduate)
  TENTATIVE_LESSONS.md            this session's candidate-lessons buffer (auto-rotated)
  docs/
    heartleaf-gameplay.md         self-contained game reference (rules, protocol, scoring, exact timing)
    villager-dinner-attendance.md how the starter villagers decide/accept dinners (what we exploit)
    replay-tools.md               how to expand a replay + draw travel-line debug images
    designs/                      cady player + social-LLM-controller designs
  tools/                          lessons hooks + replay/analysis viz (expand_replay, viz_replay,
                                  viz_occupancy, build/viz_flow_field — movement + heatmap over the map)
  .claude/skills/lessons-review/  the ≈weekly lessons-graduation skill
  lessons_archive/                rotated per-session lesson buffers
```

The implemented player lives in `cady/`; the game-hosted starter framework remains another supported design path.

The full evaluate → report → improve → submit cycle, and which skill drives each step, is in
[`AGENTS.md`](AGENTS.md) (Heartleaf layer) and [`../AGENTS.md`](../AGENTS.md) (the loop).
