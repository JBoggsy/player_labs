# paintbot_lab

The **Paintbot** corner of [player_labs](../README.md) — where we build,
evaluate, and improve player policies for **Coworld Paintbot**, a 2-or-4-team
capture-the-heart paintball shooter on the **BitWorld Sprite-v1** protocol, with
**procedurally generated maps**.

This README orients newcomers (human or agent). Two pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the
  improvement loop in Paintbot terms, the player, and the lab's practices.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory
  auth) and the ground rules.

> **Status: lab bootstrapped 2026-08-03.** `stencil` (a beacon fork with online
> per-episode navigation) is implemented and tested but **not yet uploaded or
> evaluated**. The live Paintbot league runs the **campaign (territory)
> round brain, not a ladder**: an LLM commander per player invades cells on a
> 10x10 board where **each cell permanently owns a map** (pinned terrain seed +
> size); standings are territory — daveey holds 84/100 cells, and the
> auto-mirrored `beacon:v67` holds 0 (its fixed-arena bake can't navigate
> generated maps). Deployed game: paintbot **0.7.178**. Live state + open
> threads: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

## The game (one paragraph)

Paintbot is CTF's expanded sibling — **the same engine, repo, and Nim binary**
(`Metta-AI/coworld-ctf`), registered as a second Coworld game whose manifest
adds variants. Teams (2 or 4: red/blue/green/yellow) guard a **heart** on a
pedestal inside their endzone; steal any rival's heart and carry it home to
**eliminate that team** — last team standing wins. Maps are **procedurally
generated per episode** (five size classes; sides / corners / plus layouts) for
every competitive variant except `default`, which is literally the classic CTF
arena. Scoring is **pot**: every team antes 1, winner takes all (+2/-2 two-team,
+4/-1/-1/-1 four-team); a timeout draw pays -1 to everyone. Paint is cosmetic.
**Full reference: [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md)**;
deep recon with citations:
[`docs/recon/paintbot-2026-08-03.md`](docs/recon/paintbot-2026-08-03.md).

## Variants at a glance

| variant | seats | teams | map | our agents |
|---|---|---|---|---|
| `default` | 16 | 2 | fixed classic arena | ~8 (near-1v1 of policies) |
| `2v2` | 16 | 2 | generated | 4 (team split across 2 policies) |
| `4ffa` | 16 | 4 | generated | 4 (one policy per team) |
| `4ffa8` | 32 | 4 | generated giant | 8 (one policy per team) |

There is **no "1v1" variant**; a policy must handle owning 1-8 seats. Which
variant an episode plays is decided by the **campaign**: each territory cell
permanently owns a variant + terrain seed + size class (live board: 29x
`4ffa8`, 26x `4ffa`, 25x `default`, 20x `2v2`), and battles replay the target
cell's exact map — see the campaign section of
[`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md).

## Layout

```
paintbot_lab/
  README.md                this file
  AGENTS.md                operating model: the loop in Paintbot terms
  WORKING_CONTEXT.md       live cross-session state — read first
  best_practices.md        Paintbot-specific practices (fills via lessons)
  TENTATIVE_LESSONS.md     this session's candidate-lessons buffer (auto-rotated)
  paintbot/stencil/        THE PLAYER — Python Player-SDK SpriteV1 policy
  docs/
    paintbot-gameplay.md   self-contained game reference
    recon/                 the founding deep-dive (citations into game + metta)
    designs/stencil-v1-design.md   stencil's architecture + scrap/port ledger
  tools/
    build_player.sh        build the stencil image (linux/amd64)
    versions.env           pinned SDK ref + game provenance
    rotate_lessons.sh      SessionStart hook (archive the lesson buffer)
  lessons_archive/         rotated per-session lesson buffers
```

The player lives at [`paintbot/stencil/`](paintbot/stencil/): a deterministic
Player-SDK SpriteV1 cyborg forked from ctf_lab's beacon. The defining
difference from beacon: **no offline map bake** — an episode-scoped `WorldMap`
(`worldmap.py`) is built online from the walkability sprite + wire markers
(nav grid, cover, lazy Dijkstra flow fields, derived chokes/rallies/spawn-aim),
and everything map-shaped that beacon hand-authored (POIs, battle plans, posts)
is scrapped. Multi-team support: color lock from the self sprite, per-color
hearts with retirement tracking, steal target = nearest live enemy heart, and
the convert trigger generalized to the weakest enemy team.

## Quick commands

```sh
uv run pytest paintbot_lab/paintbot/stencil/tests    # the invariant suite
paintbot_lab/tools/build_player.sh stencil           # build the image (amd64)
uv run coworld upload-policy players-stencil:dev --name stencil   # upload (inert)
uv run python -m paintbot.stencil.tuning dump        # tunables registry
```

Upload freely; **submitting to the league is the human-gated step** (root
[`AGENTS.md`](../AGENTS.md); note beacon's CTF entrants auto-mirror into
Paintbot, so a *submitted* stencil coexists with the mirrored beacon under the
same account — see the `coworld-player-swap` skill if identity matters).
