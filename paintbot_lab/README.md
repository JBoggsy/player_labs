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

> **Status: aim fix + generated-post defense hosted-validated 2026-08-04.**
> `stencil:v12` (a beacon fork with online per-episode navigation) is uploaded
> with full tracing; defenders occupy distinct homeward-ranked firing posts and
> the aim controller matches GameVersion 36's 32-slot/five-slot turn. It is
> **not submitted**. The live
> Paintbot league runs the **campaign (territory)
> round brain, not a ladder**: an LLM commander per player invades cells on a
> 10x10 board where **each cell permanently owns a map** (pinned terrain seed +
> size); standings are territory — at campaign round 202, daveey held 80/100
> cells and richard held 8. Deployed game: paintbot **0.7.184**. Live state + open
> threads: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md). Defensive experiment
> verdict: [`docs/reports/stencil-defensive-mechanics-2026-08-04.md`](docs/reports/stencil-defensive-mechanics-2026-08-04.md).

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
| `1v1` | 2 | 2 | generated | 1 (fast local micro/self-play) |
| `default` | 16 | 2 | fixed classic arena | ~8 (near-1v1 of policies) |
| `2v2` | 16 | 2 | generated | 4 (team split across 2 policies) |
| `4ffa` | 16 | 4 | generated | 4 (one policy per team) |
| `4ffa8` | 32 | 4 | generated (manifest defaults giant; campaign cell size wins) | 8 (one policy per team) |

The `1v1` variant was added in 0.7.179 as a cheap duel instrument; campaign
battles still use the four established variants, where a policy must handle
owning 1-8 seats. Which variant a campaign episode plays is decided by the
**campaign**: each territory cell
permanently owns a variant + terrain seed + size class (live board: 29x
`4ffa8`, 26x `4ffa`, 25x `default`, 20x `2v2`), and battles replay the target
cell's exact map. Campaign `mapSize` overrides the variant default, so map
dimensions do not identify 16-seat `4ffa` versus 32-seat `4ffa8` — see the campaign section of
[`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md).

## Layout

```
paintbot_lab/
  README.md                this file
  AGENTS.md                operating model: the loop in Paintbot terms
  WORKING_CONTEXT.md       live cross-session state — read first
  best_practices.md        Paintbot-specific practices (fills via lessons)
  TENTATIVE_LESSONS.md     this session's candidate-lessons buffer (auto-rotated)
  paintbot/stencil_nim/    THE PLAYER — native Nim Sprite-v1 policy
  docs/
    paintbot-gameplay.md   self-contained game reference
    recon/                 the founding deep-dive (citations into game + metta)
    reports/               hosted experiment evidence and verdicts
    designs/stencil-v1-design.md   stencil's architecture + scrap/port ledger
    designs/stencil-nim-port.md    native port contract + parity evidence
  tools/
    build_player.sh        build the stencil image (linux/amd64)
    self_play.py           native, fast-ready, parallel local self-play
    versions.env           pinned game/dependency provenance
    rotate_lessons.sh      SessionStart hook (archive the lesson buffer)
  lessons_archive/         rotated per-session lesson buffers
```

The player lives at [`paintbot/stencil_nim/`](paintbot/stencil_nim/): a
deterministic native Nim Sprite-v1 cyborg descended from ctf_lab's beacon. The
defining difference from beacon: **no offline map bake** — an episode-scoped `WorldMap`
(`worldmap.nim`) is built online from the walkability sprite + wire markers
(nav grid, cover, lazy Dijkstra flow fields, derived chokes/rallies/spawn-aim,
and per-opponent firing/duck posts). Beacon's authored POIs and battle plans
remain scrapped. Defenders consume the online posts while heart-theft
interception remains higher priority. Multi-team support: color lock from the self sprite, per-color
hearts with retirement tracking, steal target = nearest live enemy heart, and
the convert trigger generalized to the weakest enemy team.

## Quick commands

```sh
paintbot_lab/tools/build_player.sh stencil           # build the image (amd64)
uv run coworld upload-policy players-stencil:dev --name stencil   # upload (inert)
uv run python paintbot_lab/tools/self_play.py --variant 1v1 --episodes 20 --workers 4
uv run python paintbot_lab/tools/self_play.py --variant 1v1 --candidate-runtime docker
```

## Fast local self-play

Before every batch, `tools/self_play.py` resolves the live canonical Paintbot
version, fetches its exact commit-pinned `coworld-ctf` source, and builds in a
managed detached worktree under `.cache/`, synchronizing the commit's pinned
Nim dependencies first. It fails without starting episodes
if live resolution, fetching, or source verification fails, so a stale or dirty
local checkout cannot silently contaminate an optimization run. It runs that
Nim simulator and every control seat as native processes;
`--candidate-runtime docker` exercises the release image for the candidate
team. The default avoids Docker/Rosetta and sends Sprite-v1's `0x87`
sprites-off and `0x85` ready packets
after every decision, reducing bot-only traffic and letting the server advance
as soon as every seat has acted instead of sleeping at 24 ticks/s. Every
episode writes `results.json`, replay, events, game log, and
per-seat logs. The harness shortens only the pre-game countdown and post-game
end card; gameplay ticks, observations, decisions, and outcomes use the real
simulator unchanged.

```sh
# High-throughput micro/combat screening (candidate side rotates by episode).
uv run python paintbot_lab/tools/self_play.py \
  --variant 1v1 --episodes 20 --workers 4

# Candidate-vs-control knob test. Only the candidate team's processes get this env.
uv run python paintbot_lab/tools/self_play.py \
  --variant 2v2 --episodes 20 --workers 2 \
  --candidate-env STENCIL_CHOKE_FRACTION=0.52

# Full worst-case board validation.
uv run python paintbot_lab/tools/self_play.py --variant 4ffa8

# Profile online WorldMap construction and first-decision flow fields.
uv run python paintbot_lab/tools/self_play.py \
  --variant 1v1 --map-size giant --episodes 20 --workers 8 \
  --max-ticks 40 --profile-nav-init

# Capture the exact nav grid, cover, posts, anchors, and lazy flow fields, then view them.
uv run python paintbot_lab/tools/self_play.py \
  --variant 1v1 --episodes 1 --max-ticks 40 --visualize-nav
uv run python paintbot_lab/tools/render_nav.py \
  paintbot_lab/self_play/<run>/episode-0000/players/slot-00.trace.jsonl
```

`--visualize-nav` enables the otherwise off `STENCIL_TRACE_NAVIGATION=1`
payload. The trace contains `navigation_map` once per map and a
`navigation_flow` event whenever the policy lazily computes a new Dijkstra
goal. `render_nav.py` accepts either that JSONL trace or a hosted player artifact
ZIP and writes a standalone HTML viewer with toggles and per-cell inspection.
Post-front selection overlays the bounded candidates, selected firing cells,
nearby duck cells, score components, and forward firing rays actually computed
by that team-colored agent.
The opt-in keeps routine multi-seat telemetry from duplicating large grids.

The harness uses `~/coding/coworlds/coworld-ctf` only as a source clone: it
fetches `origin` but never changes that checkout's branch or working tree. Every
summary records the live Coworld ID/version, manifest hash, source URL, and
exact source commit. Local self-play is a fast screening and tuning
instrument, not proof against the live opponent field; promote candidates only
after a broader hosted check. In `2v2`, the local candidate owns the full team
rather than one campaign captain block, so it does not reproduce split-policy
ally coordination.

## Native parity evidence

The accepted port matched **169,235 exact decisions** against its legacy Python
implementation across 1v1, 2v2, 4-player FFA, giant 8-player FFA, a major-
features-disabled profile, and squads/command mode. That oracle is preserved
in Git commit `1129931` and no longer exists in the working tree.
`tools/self_play.py --record-wire` now records native streams for diagnostics;
`tools/compare_stencil.py` can replay historical captured decisions. See
[`docs/designs/stencil-nim-port.md`](docs/designs/stencil-nim-port.md) for the
module mapping, equivalence boundary, and performance evidence.

Upload freely; **submitting to the league is the human-gated step** (root
[`AGENTS.md`](../AGENTS.md); note beacon's CTF entrants auto-mirror into
Paintbot, so a *submitted* stencil coexists with the mirrored beacon under the
same account — see the `coworld-player-swap` skill if identity matters).
