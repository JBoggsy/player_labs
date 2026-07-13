# vanilla_wow_lab

The **Vanilla WoW** corner of [player_labs](../README.md) — where we build, evaluate, and
improve player policies for **Vanilla WoW**, a Coworld game that is a *real* World of
Warcraft 1.12.1 realm backed by [VMaNGOS](https://github.com/vmangos/core).

This README orients newcomers (human or agent). Two pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the improvement loop in
  Vanilla-WoW terms, the player build paths, and the lab's practices. Read it to *work* here.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory auth) and the
  ground rules.

> **Status (2026-07-13): lab just created — docs + scaffolding only, no player yet, and the
> loop is BLOCKED.** The game repo (`coworld-vanilla-wow`) is cloned for reference at
> `~/coding/coworlds/coworld-vanilla-wow`, but its README badge reads **"coworld verify: not
> ready"**: the package `vanilla_wow:0.1.4.post8` passed executable certification + a local
> isolated-RFC smoke, but the "ready" badge is gated on a *retained* hosted round + XP-request
> episode that **haven't been created**, and **no live scored Observatory league exists yet**
> (only a persistent *practice* realm). So the evaluate→improve loop can't run until the game
> certifies and a league opens — the immediate next step is human-directed. Live state:
> [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

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
    designs/                         player design docs (empty until a policy is designed)
  tools/                             lessons hooks (rotate_lessons.sh, lessons_stop_nudge.sh)
  .claude/skills/lessons-review/     the ≈weekly lessons-graduation skill
  lessons_archive/                   rotated per-session lesson buffers
```

A player policy directory (e.g. `vanilla_wow_lab/<policy>/`) gets added once the first policy
is built — mirroring `crewrift_lab/crewrift/`, `cue_n_woo_lab/mentalist/`, and
`heartleaf_lab/cady/`. Because the player is Nim, that will also bring a Nim build path and
(if it forks the bundled engine) a pinned game commit — the `versions.env` pattern from
`crewrift_lab/tools/`.

The full evaluate → report → improve → submit cycle, and which skill drives each step, is in
[`AGENTS.md`](AGENTS.md) (Vanilla-WoW layer) and [`../AGENTS.md`](../AGENTS.md) (the loop).
