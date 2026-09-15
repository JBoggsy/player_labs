# paintbot_lab — agent guide

The **Paintbot** corner of player_labs: where we build, evaluate, and improve
**player policies** for Coworld Paintbot. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills. This file is the **Paintbot-specific layer**: the game,
the docs, the practices, and the policy we optimize. When the two disagree, the
root defines *process*; this file defines *Paintbot*.

## What Paintbot is

Read [the game reference](docs/paintbot-gameplay.md) and selected league manifest.
The public variant is a sixteen-seat solo battle royale using play-calling control.
Stencil is a direct-input capture-the-heart policy; compatibility must be established
against a matching configuration before evaluating it.

## The loop, in Paintbot terms

The root loop (evaluate → report → direction → implement → rebuild+reupload →
repeat → human gate → submit) runs **unchanged**. Paintbot-specific instruments:

- **Evaluate** (step 1) — experience requests against the uploaded stencil
  version. Natural cuts: **variant/battle mode** (default / 2v2 / 4ffa /
  4ffa8; in league play the mix follows the campaign's contested cells),
  **map size class**, **entrant index / team color**, **ally composition**,
  **team color**, **win path** (capture-elimination vs wipe vs survival vs
  timeout). Because scoring is win-only, win rate per cut is the metric.
  **Only full-seat campaign-shaped episodes count as tests.** Follow
  [`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md):
  the correct commissioner field expanded across every seat of a current
  live-board `1v1`, `2v2`, or `4ffa` cell. Partial-seat games are debug
  probes only.
  League-side, the ultimate KPI is **territory** — battle win rate is the
  instrument; the commander prompt (see WORKING_CONTEXT) is a second lever.
- **Debug locally** — `tools/self_play.py` runs the native production simulator.
  Local and partial-seat scenarios may expose a mechanism or reproduce a
  failure, but are explicitly non-representative and never count as gameplay
  tests. A `1v1` map ref is representative only when hosted with its current
  full 16-seat campaign roster. All performance conclusions require the
  campaign-shaped hosted format above.
- **Report** (step 2) — pull artifacts with `coworld-episode-artifacts`. There
  is **no paintbot survey/warehouse skill yet**. [`tools/event_warehouse.py`](tools/event_warehouse.py)
   supplies the re-keying machinery, and
  ctf_lab's `analyze_reporter_warehouse.py` remains a pattern to copy. The
  warehouse is **not yet Paintbot-correct**: it projects only red/blue and scores
  green/yellow wins as draws (see `../TODO.md`). Replays carry exact `mapSpec`
  geometry, so per-map analysis is possible post-hoc. Building a paintbot
  warehouse is the highest-leverage tooling investment once we have batches.
- **Implement** (step 4) — change [`paintbot/stencil_nim/`](paintbot/stencil_nim/);
  knobs live in `config.nim` (`STENCIL_*` env vars) so each iteration is
  attributable.
- **Rebuild / upload / submit** (steps 5-8) — `tools/build_player.sh stencil`,
  then the game-agnostic skills. The hosted eval is the test; `coworld-local-run`
  is a debugging tool only.

## The player: stencil

A deterministic native Nim cyborg descended from ctf_lab's **beacon** and
validated exactly against its bootstrap Python implementation (read
 — it
carries the scrap-vs-port ledger and a completion addendum for the navigation
rework). The architecture in one breath: `perception`
reads labels **plus** the walkability sprite pixels and wire markers; the
runtime builds an **episode-scoped `WorldMap`** (L∞ clearance field +
predicates, clearance-derived nav grid, component labels, watershed
rooms/chokepoints + defense gates, directional cover, the map-wide post
atlas, stable-goal Dijkstra fields as the planner's oracle, spawn-aim —
derived from observations); `belief` folds tracks,
danger, hearing, chat, per-color hearts (with retirement + steal-target
choice); `strategy` runs the ladder (`strategy.nim:decideBaseObjective`,
first match wins: carry-home > intercept-thief > grenade-clear > spray-flee >
**barrage-center** > early-defense > squad rejoin > escort-carrier (attackers)
> item fetch > convert-hunt > consensus squad order > defender post/hold >
steal; early-defense also gates squad consensus until it completes) and emits
one **typed `Intent`** — a pre-validated goal plus typed permissions
(movingGoal, clampToEndzone, suppressFireFreeze, cost profile, micro flag
set, arriveRadius; reason strings are telemetry-only);
`action` resolves the Intent to the mask: the weighted-A* planner
(`planner.nim`, via `nav.nim`'s bounded follower with corridor-bounded micro
and a replan watchdog) routes all movement, and the combat layer overlays
lighthouse sweep, snap/lead aim, fire gate,
friendly-fire guard, peek-fire-duck, and the grenade overlay. The
WorldMap carries an atlas of firing/duck posts everywhere there is cover;
defenders occupy ranked atlas posts scored situationally against believed
enemy tracks. Leaderless squads use the same atlas to execute
consensus hold/watch/move orders. Fixed-map battle plans, general POIs, and
anti-turtle remain cut.

Key invariants to respect when editing:

- **No module-level map caches.** All map state lives on `belief.worldmap`
  (episode-scoped).
- **The wire is the only map source.** If you need a map fact, derive it in
  `worldmap.nim` from the init snapshot; never constant-ize a generated map.
- **Multi-team throughout**: any code touching "the enemy" must handle 1-3
  enemy colors and hearts leaving play (`belief.heartsRetired`).
- Seat conventions must work when another entrant owns the trailing half of
  our team's seats (the current even captain/ally split in `2v2`-mode
  invasions). Resolve actual positions from the selected match configuration.

## Docs

- [Documentation index](docs/README.md).
- [Game contract and resources](docs/paintbot-gameplay.md).
- [Evaluation setup](docs/tournament-like-experience-requests.md).
- [Analysis tools](docs/analysis-tools.md).


## Skills

One paintbot-local skill exists: `lessons-review` (in
[`.claude/skills/`](.claude/skills/), the current lesson review). No
paintbot-specific *loop* skills yet. The loop's **game-agnostic** halves (experience
requests, artifact download, build-and-upload, policy lifecycle, A/B,
hypothesis miner) live at the **lab root** (`../.claude/skills/`, indexed in
[`../AGENTS.md`](../AGENTS.md)). Use [the analysis reference](docs/analysis-tools.md) for the warehouse and comparison adapter.

## Testing discipline

The hosted eval is the test; speed wins. For a targeted local question, use
`tools/self_play.py`; for a recorded wire regression, use
`tools/compare_stencil.py`. Do not rebuild a broad pre-upload test gate.

## Working context and guidance

Keep the active objective, scope, unresolved constraints and next decision in
[WORKING_CONTEXT.md](WORKING_CONTEXT.md). Keep testable unresolved ideas in
[TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md); promote supported rules to
best_practices.md and remove resolved claims. Follow the
[shared learning workflow](../docs/learning.md). Update these documents in place;
do not create session archives, version logs or change narratives.

## Deferred tasks

Paintbot-specific parked work lives in the shared [`../TODO.md`](../TODO.md).

## Player policies

- **stencil** *(native Nim)* — at
  [`paintbot/stencil_nim/`](paintbot/stencil_nim/), the primary competing
  Paintbot policy. Resolve the selected league’s champion and artifact live.
