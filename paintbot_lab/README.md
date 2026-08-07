# paintbot_lab

The **Paintbot** corner of [player_labs](../README.md) — where we build,
evaluate, and improve player policies for **Coworld Paintbot**, a 2-or-4-team
capture-the-heart paintball shooter on the **BitWorld Sprite-v1** protocol, with
**procedurally generated maps**.

This README orients newcomers (human or agent). Three pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the
  improvement loop in Paintbot terms, the player, and the lab's practices.
- **[`docs/README.md`](docs/README.md)** — the documentation index: current
  references, operations, designs, historical reports, and audit status.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory
  auth) and the ground rules.

> **Status (verified 2026-08-06): `stencil:v54` is the active James Botts
> champion; `stencil:v53` was rejected and `stencil:v52` is the previous
> champion.** V54's 60-episode round-385 field test finished 49-3-8. The canonical game is
> Paintbot **0.7.208**. The live league uses a
> 10x10 campaign board; normal invasions use four policies, with 7+7+1+1
> captain/ally seating on two-team maps and one policy per team in FFA. Current work and live IDs:
> [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md). The required evaluation shape:
> [`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md).

## The game (one paragraph)

Paintbot is CTF's expanded sibling — **the same engine, repo, and Nim binary**
(`Metta-AI/coworld-ctf`), registered as a second Coworld game whose manifest
adds variants. Teams (2 or 4: red/blue/green/yellow) guard a **heart** on a
pedestal inside their endzone; steal any rival's heart and carry it home to
**eliminate that team** — last team standing wins. Maps are **procedurally
generated per episode** (five size classes; sides / corners / plus layouts).
The historical `default` fixed-arena behavior changed; canonical 0.7.208 also
uses generated terrain for `default`. Scoring is **pot** for the tournament
variants: every team antes 1, winner takes all (+2/-2 two-team,
+4/-1/-1/-1 four-team); a timeout draw pays -1 to everyone. Paint is cosmetic.
**Full reference: [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md)**;
deep recon with citations:
[`docs/recon/paintbot-2026-08-03.md`](docs/recon/paintbot-2026-08-03.md).

## Variants at a glance

| variant | seats | teams | map | our agents |
|---|---|---|---|---|
| `1v1` | 16 | 2 | generated | campaign mode `2v2`: normally captain 7 + ally 1 per team |
| `default` | 16 | 2 | generated | scheduler-dependent; absent from the current campaign board |
| `2v2` | 16 | 2 | generated | normally captain 7 + ally 1 per team |
| `4ffa` | 16 | 4 | generated | 4 (one policy per team) |
| `4ffa8` | 32 | 4 | generated (manifest defaults giant; campaign cell size wins) | 8 (one policy per team) |

The `1v1` variant was added in 0.7.179 as a two-agent custom game, then changed
in 0.7.205 to a 16-seat two-team format. The campaign classifies it as mode
`2v2` and normally seats four policies 7+7+1+1; the variant name does not mean
two policies. A correctly seated full campaign cell is representative;
partial-seat and arbitrary-map variants remain debug-only. Which map a
campaign episode plays is decided by the
**campaign**: each territory cell
permanently owns a variant + terrain seed (round-381 board: 26x `1v1`, 26x
`2v2`, 48x `4ffa`; every `map_size` is currently unset), and battles replay
the target cell's map identity. See the campaign section of
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
  paintbot/rl/             cross-era Qwen policy experiments
  docs/
    README.md             documentation index + source-of-truth map
    paintbot-gameplay.md   self-contained game reference
    tournament-like-experience-requests.md  required hosted-eval contract
    audits/                dated documentation-audit records
    recon/                 the founding deep-dive (citations into game + metta)
    reports/               hosted experiment evidence and verdicts
    designs/stencil-v1-design.md   stencil's architecture + scrap/port ledger
    designs/stencil-nim-port.md    native port contract + parity evidence
    designs/rl-policy.md           Qwen policy architecture + decisions
  tools/
    analyze_giant_carries.py  one-off historical v22 giant-duel analyzer
    build_player.sh        build the stencil image (linux/amd64)
    self_play.py           native, fast-ready, parallel local self-play
    render_nav.py          static navigation-knowledge viewer
    compare_stencil.py     A/B metric adapter over the shared stats engine
    campaign_order_controller.py        campaign standing-orders controller
    manage_campaign_order_launch_agent.py  install/status the macOS LaunchAgent
    versions.env           pinned game/dependency provenance
    rotate_lessons.sh      SessionStart hook (archive the lesson buffer)
  infra/campaign_order_controller/  the controller's service docs + cycle test
  lessons_archive/         rotated per-session lesson buffers
```

The player lives at [`paintbot/stencil_nim/`](paintbot/stencil_nim/): a
deterministic native Nim Sprite-v1 cyborg descended from ctf_lab's beacon. The
defining difference from beacon: **no offline map bake** — an episode-scoped `WorldMap`
(`worldmap.nim`) is built online from the walkability sprite + wire markers
(nav grid, cover, lazy Dijkstra flow fields, derived chokes/rallies/spawn-aim,
and per-opponent firing/duck posts). Beacon's authored POIs and fixed-map
battle-plan data remain scrapped; leaderless squads now form consensus on
hold/watch/move orders and ground them in the generated posts. Defenders consume the online posts while heart-theft
interception remains higher priority. Multi-team support: color lock from the self sprite, per-color
hearts with retirement tracking, steal target = nearest live enemy heart, and
the convert trigger generalized to the weakest enemy team.

## Quick commands

```sh
paintbot_lab/tools/build_player.sh stencil           # build the image (amd64)
uv run coworld upload-policy players-stencil:dev --name stencil   # upload (inert)
uv run python paintbot_lab/tools/self_play.py --variant 1v1 --episodes 1  # debug only
```

## Local debugging

Local self-play—including full-seat variants—is not a tournament test because
it does not reproduce the live opponent field and campaign cell contract. Use it to profile, reproduce,
or inspect a mechanism. Use hosted requests that satisfy the
[`tournament-like experience-request contract`](docs/tournament-like-experience-requests.md)
for every gameplay conclusion.

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
# Local debug reproduction; current 1v1 itself has 16 seats.
uv run python paintbot_lab/tools/self_play.py \
  --variant 1v1 --episodes 20 --workers 4

# Local mechanism probe. Only the candidate team's processes get this env.
uv run python paintbot_lab/tools/self_play.py \
  --variant 2v2 --episodes 20 --workers 2 \
  --candidate-env STENCIL_CHOKE_FRACTION=0.52

# Full-roster local structural/debug run (still not a tournament verdict).
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
by that team-colored agent. Fully traced artifacts also overlay that specific
agent's assigned post, paired duck point, and scored sightline axis.
The opt-in keeps routine multi-seat telemetry from duplicating large grids.

The harness uses `~/coding/coworlds/coworld-ctf` only as a source clone: it
fetches `origin` but never changes that checkout's branch or working tree. Every
summary records the live Coworld ID/version, manifest hash, source URL, and
exact source commit. Local self-play is a debugging instrument, never evidence
against the live opponent field. In campaign `2v2` mode, a normal captain owns
seven seats and an allied entrant owns one seat; local candidate/control
seating does not automatically reproduce that commissioner layout.

## Replay viewers: belief overlay versus navigation knowledge

These are different tools:

- **Agent belief replay overlay** — [`ctf_lab/tools/viewer.html`](../ctf_lab/tools/viewer.html), fed by a
  `viewer_bundle.json` from [`ctf_lab/tools/viewer_bundle.py`](../ctf_lab/tools/viewer_bundle.py). It synchronizes
  ground-truth replay positions with each Stencil agent's tick-by-tick belief,
  objective, tracks, item state, danger field, and heard-event traces. It also
  shows a conservative ally-covered heatmap: currently visible allies' fuzzed
  16-step headings projected through the guaranteed vision cone and clipped by
  pixel-wall line of sight. The belief panel reports covered-cell share,
  visible/headed ally counts, heading precision, and danger mean/max at the
  selected snapshot. Ground-truth player and flag colors come from the
  episode's authoritative slot-team configuration, including four-team FFA.
  The exact-version replay reader
  supplies the episode's startup walkability mask; generated Paintbot maps do
  not use Beacon's baked arena. Use this for gameplay diagnosis.
- **Navigation knowledge viewer** — `paintbot_lab/tools/render_nav.py`. It
  renders one agent's static/generated map knowledge, posts, rays, and cached
  flows. It does not replay the agent's changing belief state.

For one fetched, full-seat hosted episode:

```sh
ctf_lab/tools/build_expand_replay.sh
uv run python ctf_lab/tools/viewer_bundle.py <episode-dir>
python3 -m http.server -d ctf_lab/tools 8766
# Open http://localhost:8766/viewer.html and load <episode-dir>/viewer_bundle.json.
```

The bundle needs the fetched replay plus Stencil `policy_artifact_<slot>.zip`
files for overlays. Start with the shipped replay-reader build script. If the
bundler reports a replay/source hash mismatch, rebuild the reader at the
episode's exact source commit before trusting tick alignment or events.

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
