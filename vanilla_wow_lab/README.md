# vanilla_wow_lab

The **Vanilla WoW** corner of [player_labs](../README.md) — where we build, evaluate, and
improve player policies for **Vanilla WoW**, a Coworld game that is a *real* World of
Warcraft 1.12.1 realm backed by [VMaNGOS](https://github.com/vmangos/core).

This README orients newcomers (human or agent). Two pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the improvement loop in
  Vanilla-WoW terms, the player build paths, and the lab's practices. Read it to *work* here.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory auth) and the
  ground rules.

> **Status (2026-07-29): `wowborg` uses the game's canonical Gymnasium `/env`
> interface.** Its Python policy consumes `AgentFrame` and submits `AgentAction`
> directly; the game owns the WoW client and all protocol/admission/settlement
> machinery. The exact deployed accelerated-wow image and matching owner commit are
> pinned in [`tools/versions.env`](tools/versions.env). Live state + next steps:
> [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

## The game (one paragraph)

Vanilla WoW Coworld is **a real WoW 1.12.1 realm turned into a competitive AI benchmark**.
A "player" is an AI agent that controls one WoW *character* on a genuine VMaNGOS server: it
logs in, moves with real physics, fights, quests, loots, sells, trains spells, dies and
recovers, and groups up — all over the real WoW binary protocol. It competes two ways: on a
**persistent realm**, ranked by its account's highest-XP character; and in **isolated scored
episodes**, where the current benchmark **`rfc-five-player-clear`** puts one policy in all
five slots of a party racing to clear **Ragefire Chasm**'s four bosses fastest. A submitted
policy is now a synchronous Python Gymnasium agent over the game's canonical `/env`; the
game owns the Nim packet-level WoW client.

**Full game reference — the game shapes, RFC episode + scoring, and the WoW mechanics that
matter for strategy — is [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md)**
(written to be understandable even if you've never played WoW). The authoritative source is
the **`coworld-vanilla-wow`** repo (`environment/` contract and runtime, `player/` policy
SDK/reference implementation, `dungeons/`, and `infra/` manifests).

## The opportunity, in brief

The bundled reference bots (King Nimrod's authored farm/follow behavior; King Richard's
leveling policy + identity-blind "general-grinding" lane) already do real WoW: perception →
navmesh pathfinding → per-class combat rotations → quest/loot/vendor/train → death recovery →
grouping. The scored competition (`rfc-five-player-clear`) is a **same-brain five-character
party coordination** problem — one policy plays tank + healer + three DPS — where crossing
the "full clear" threshold matters before shaving clear time. So a competitive player is a
**heavier lift than the other labs** because it must reason over real WoW physics and a
large semantic action space, not because the lab must own a WoW client. Strategy remains a
**human-direction call** — see [`AGENTS.md`](AGENTS.md#player-build-paths).

## Layout

```
vanilla_wow_lab/
  README.md                          this file
  AGENTS.md                          operating model: the loop in Vanilla-WoW terms, build paths
  WORKING_CONTEXT.md                 live cross-session state — read first
  best_practices.md                  Vanilla-WoW practices (near-empty until lessons graduate)
  TENTATIVE_LESSONS.md               this session's candidate-lessons buffer (auto-rotated)
  docs/
    vanilla-wow-gameplay.md          self-contained, accessible game reference (START HERE)
    vanilla-wow-player-contract.md   the Nim packet-level player: connect / observe / emit / ship
    vanilla-wow-protocol.md          exhaustive interface-protocol reference (every message/schema/format)
    vanilla-wow-rfc-roles.md         the 5 RFC roles (commissioner/grader/…) + round scoring
    vanilla-wow-strategy-guide.md    how to PLAY WoW well: beginner's guide + pro tips + RFC/leveling strategy
    designs/                         player design docs (obs/action spaces, v2 shim adoption)
    recon/                           citation-backed recon reports (navigation obs/actions)
  wowborg/                           our player: Python policy over canonical /env (own README)
  tools/                             versions.env (environment pin), build_player.sh, route_lab.py,
                                     cwreplay.py (replay decoder), movement_report.py (movement
                                     continuity from a replay), lessons hooks
  .claude/skills/lessons-review/     the ≈weekly lessons-graduation skill
  lessons_archive/                   rotated per-session lesson buffers
```

The player policy directory is [`wowborg/`](wowborg/) — mirroring `crewrift_lab/crewrift/`,
`cue_n_woo_lab/mentalist/`, and `heartleaf_lab/cady/`. Its image is pure Python and copies
the canonical environment contract plus navmesh SDK from the **deployed** game image. It
does not contain a Nim client or local adapter; the environment pin lives in
[`tools/versions.env`](tools/versions.env).

The full evaluate → report → improve → submit cycle, and which skill drives each step, is in
[`AGENTS.md`](AGENTS.md) (Vanilla-WoW layer) and [`../AGENTS.md`](../AGENTS.md) (the loop).
