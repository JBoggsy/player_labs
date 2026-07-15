# vanilla_wow_lab

The **Vanilla WoW** corner of [player_labs](../README.md) — where we build, evaluate, and
improve player policies for **Vanilla WoW**, a Coworld game that is a *real* World of
Warcraft 1.12.1 realm backed by [VMaNGOS](https://github.com/vmangos/core).

This README orients newcomers (human or agent). Two pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the improvement loop in
  Vanilla-WoW terms, the player build paths, and the lab's practices. Read it to *work* here.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory auth) and the
  ground rules.

> **Status (2026-07-15): `wowborg` v2 (shim adoption) built + locally smoke-tested; not
> yet uploaded.** v2 drives the game's bundled Nim client (King Richard in `nim-control`
> mode) through its documented file bridge instead of reimplementing the WoW protocol —
> see [`docs/designs/wowborg-v2-shim-adoption.md`](docs/designs/wowborg-v2-shim-adoption.md).
> The image layers on the deployed reference player (vanilla_wow 0.1.19, digest-pinned in
> [`tools/versions.env`](tools/versions.env)). League scoring/retention remains unverified
> (game repo badge still "coworld verify: not ready" as of 2026-07-14). Live state + next
> steps: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

## The game (one paragraph)

Vanilla WoW Coworld is **a real WoW 1.12.1 realm turned into a competitive AI benchmark**.
A "player" is an AI agent that controls one WoW *character* on a genuine VMaNGOS server: it
logs in, moves with real physics, fights, quests, loots, sells, trains spells, dies and
recovers, and groups up — all over the real WoW binary protocol. It competes two ways: on a
**persistent realm**, ranked by its account's highest-XP character; and in **isolated scored
episodes**, where the current benchmark **`rfc-five-player-clear`** puts one policy in all
five slots of a party racing to clear **Ragefire Chasm**'s four bosses fastest. Unlike the
other labs' players, a Vanilla WoW player is a **Nim, packet-level WoW client** (the headless
bot **King Nimrod**), not a Python SDK policy — which makes it the heaviest player contract
in the repo.

**Full game reference — the game shapes, RFC episode + scoring, and the WoW mechanics that
matter for strategy — is [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md)**
(written to be understandable even if you've never played WoW). The authoritative source is
the **`coworld-vanilla-wow`** repo (Python adapter `src/vanilla_wow_coworld/`, Nim player
`player/`, dungeon defs `dungeons/`, `coworld_manifest_template.json`).

## The opportunity, in brief

The bundled reference bots (King Nimrod's authored farm/follow behavior; King Richard's
leveling policy + identity-blind "general-grinding" lane) already do real WoW: perception →
navmesh pathfinding → per-class combat rotations → quest/loot/vendor/train → death recovery →
grouping. The scored competition (`rfc-five-player-clear`) is a **same-brain five-character
party coordination** problem — one policy plays tank + healer + three DPS — where crossing
the "full clear" threshold matters before shaving clear time. So a competitive player is a
**heavier lift than the other labs** (it's Nim + real WoW physics, not a prompt swap), and
the build paths (a new leveling profile / better class rotations / a fork of King Nimrod / the
general-grinding lane) are a **human-direction call** — see [`AGENTS.md`](AGENTS.md#player-build-paths).

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
  wowborg/                           our player: v2 shim-driven policy stack (own README)
  tools/                             versions.env (shim pin), build_player.sh, cwreplay.py (replay decoder), lessons hooks
  .claude/skills/lessons-review/     the ≈weekly lessons-graduation skill
  lessons_archive/                   rotated per-session lesson buffers
```

The player policy directory is [`wowborg/`](wowborg/) — mirroring `crewrift_lab/crewrift/`,
`cue_n_woo_lab/mentalist/`, and `heartleaf_lab/cady/`. Its v2 image is pure Python layered
on the **deployed** reference player image (which carries the compiled Nim client) — no Nim
build path of our own; the shim pin lives in [`tools/versions.env`](tools/versions.env),
the `versions.env` pattern from `crewrift_lab/tools/`.

The full evaluate → report → improve → submit cycle, and which skill drives each step, is in
[`AGENTS.md`](AGENTS.md) (Vanilla-WoW layer) and [`../AGENTS.md`](../AGENTS.md) (the loop).
