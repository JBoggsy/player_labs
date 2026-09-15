# heartleaf_lab

This README orients newcomers (human or agent). Two pointers do most of the work:

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

The implemented player lives in `cady/`; the game-hosted starter framework remains another supported design path.

The full evaluate → report → improve → submit cycle, and which skill drives each step, is in
[`AGENTS.md`](AGENTS.md) (Heartleaf layer) and [`../AGENTS.md`](../AGENTS.md) (the loop).
