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

> **Status (2026-07-06): lab just created — scaffolding only.** The game repo
> (`Metta-AI/coworld-heartleaf`) is cloned for reference and a live Observatory league
> exists, but **no player policy has been built yet**. Next step is human-directed: pick a
> build path and start the loop. Live state: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

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
    heartleaf-gameplay.md         self-contained game reference (rules, protocol, scoring, strategy)
  tools/                          lessons lifecycle hooks (rotate + stop-nudge)
  .claude/skills/lessons-review/  the ≈weekly lessons-graduation skill
  lessons_archive/                rotated per-session lesson buffers
```

A player policy directory (e.g. `heartleaf_lab/<policy>/`) gets added once the first policy
is built — mirroring `crewrift_lab/crewrift/` and `cue_n_woo_lab/mentalist/`.

The full evaluate → report → improve → submit cycle, and which skill drives each step, is in
[`AGENTS.md`](AGENTS.md) (Heartleaf layer) and [`../AGENTS.md`](../AGENTS.md) (the loop).
