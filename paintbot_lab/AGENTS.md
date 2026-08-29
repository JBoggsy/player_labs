# paintbot_lab — agent guide

The **Paintbot** corner of player_labs: where we build, evaluate, and improve
**player policies** for Coworld Paintbot. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills. This file is the **Paintbot-specific layer**: the game,
the docs, the practices, and the policy we optimize. When the two disagree, the
root defines *process*; this file defines *Paintbot*.

> **Lab status (verified live 2026-08-29): v68 champion — the navigation
> rework is complete.** `stencil:v68` (the bounded follower, rework Layer 5)
> was submitted 2026-08-14 and is the active James Botts champion
> (`lpm_eeac47d3`); v58's reign ended then, and v54/v52/v47 are benched. A
> **second league, Elite Paintbot** (created 2026-08-19), also lists
> stencil:v68 competing (`lpm_243bbc99`). Always verify live rather than
> trusting this snapshot.
> Stencil lives at [`paintbot/stencil_nim/`](paintbot/stencil_nim/) and its
> immutable upload history is recorded in
> [`VERSION_LOG.md`](paintbot/stencil_nim/VERSION_LOG.md). The game repo is
> the SAME clone as CTF's
> (`~/coding/coworlds/coworld-ctf` — paintbot is a second manifest over the
> same binary; **ctf_lab itself is archived** — see [`../ctf_lab/README.md`](../ctf_lab/README.md)).
> Deployed canonical paintbot has advanced to **0.7.242** (verified
> 2026-08-29 via `coworld deploy-audit`); the lab **builds** against 0.7.215 /
> `6c7a4c0e` (`tools/versions.env`) — the widening game-pin gap has a parked
> review task in [`../TODO.md`](../TODO.md). GV41 brought the endgame grenade
> barrage and paint puddles; 0.7.212-215 added **team perks** and **cardboard
> barriers**, both config-gated and OFF in every deployed variant as of the
> last audit. v58+ evacuates
> toward map center on the barrage marker; **paint puddles, perks, and barriers
> all remain unmodeled**
> (see [`docs/recon/paintbot-gv41-hazards-2026-08-07.md`](docs/recon/paintbot-gv41-hazards-2026-08-07.md)
> and the perks/barriers section of [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md)).
> The league redeploys often and **an upstream manifest merge auto-uploads the
> next version**, so this pin goes stale without anyone here acting — check
> `uv run coworld deploy-audit | grep paintbot` at the start of game-mechanics
> work (`coworld list` no longer shows games you don't own as of CLI 0.1.39).
> Live state: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

## What Paintbot is

A 2-or-4-team capture-the-heart paintball shooter on **BitWorld Sprite-v1**,
sharing CTF's engine, mechanics, and protocol. What's different from the CTF
league, and why it reshapes the lab:

- **Procedurally generated maps** (all current variants, including `default`):
  five size classes, sides/corners/plus layouts, seed never on the wire. **No
  pre-baked navigation, no authored POIs, no battle plans** — every map fact is
  read from the init snapshot (walkability sprite, `game teams` marker,
  `endzone` markers, planted hearts).
- **2-or-4 teams** (red/blue/green/yellow), pure FFA when 4: capturing a heart
  **eliminates** that team; last team standing wins.
- **Pot scoring on tournament variants**: +2/-2 (2-team) or +4/-1/-1/-1
  (4-team); timeout draw = -1 for everyone. `default` retains classic scoring.
  Win rate is still the only metric that matters per battle.
- **The CAMPAIGN replaces the ladder** (live, verified): league standings are
  **territory** on a 10x10 cell board; an LLM commander per player (steered by
  a private standing-orders prompt) picks where to invade each 600s round, and
  each cell **permanently owns a map identity** (variant + pinned terrain seed;
  the current board leaves size unset),
  so battles over a cell replay the same terrain every time. Campaign rounds
  stamp `purpose: "ladder"` — don't misread them. Full model: the recon
  addendum + [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md).
- **Campaign-shaped full seating**: a cell's campaign **mode is independent of
  its variant** (since the 2026-08-11 commissioner change). `1v1` mode is true
  head-to-head (each policy owns one team's every seat); `2v2` mode seats four
  policies with an **even** captain/ally split per team (the old 7+7+1+1 is
  gone); four-team FFA gives one color to each policy. Inspect the cell mode
  and final roster instead of inferring from names — details in
  [`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md).

Full reference: [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md). The
founding recon (with `file:line` citations into the game repo, metta, and the
live league): [`docs/recon/paintbot-2026-08-03.md`](docs/recon/paintbot-2026-08-03.md).

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
  (adopted from the archived ctf_lab) supplies the re-keying machinery, and
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
[`docs/designs/stencil-v1-design.md`](docs/designs/stencil-v1-design.md) — it
carries the scrap-vs-port ledger and a completion addendum for the navigation
rework). The architecture in one breath: `perception`
reads labels **plus** the walkability sprite pixels and wire markers; the
runtime builds an **episode-scoped `WorldMap`** (L∞ clearance field +
predicates, clearance-derived nav grid, component labels, watershed
rooms/chokepoints + defense gates, directional cover, the map-wide post
atlas, stable-goal Dijkstra fields as the planner's oracle, spawn-aim —
replacing beacon's `nav.npz` bake + POIs + plans
wholesale); `belief` folds tracks,
danger, hearing, chat, per-color hearts (with retirement + steal-target
choice); `strategy` runs the ladder (`strategy.nim:decideBaseObjective`,
first match wins: carry-home > intercept-thief > grenade-clear > spray-flee >
**barrage-center** > early-defense > squad rejoin > escort-carrier (attackers)
> item fetch > convert-hunt > consensus squad order > defender post/hold >
steal; early-defense also gates squad consensus until it completes) and emits
one **typed `Intent`** — a pre-validated goal plus typed permissions
(movingGoal, clampToEndzone, suppressFireFreeze, cost profile, micro flag
set, arriveRadius; reason strings are telemetry-only since v66);
`action` resolves the Intent to the mask: the weighted-A* planner
(`planner.nim`, via `nav.nim`'s bounded follower with corridor-bounded micro
and a replan watchdog) routes all movement, and the combat layer overlays
lighthouse sweep, snap/lead aim, fire gate,
friendly-fire guard, peek-fire-duck, and the grenade overlay. Since v67 the
WorldMap carries an atlas of firing/duck posts everywhere there is cover;
defenders occupy ranked atlas posts scored situationally against believed
enemy tracks. Leaderless squads use the same atlas to execute
consensus hold/watch/move orders. Fixed-map battle plans, general POIs, and
anti-turtle remain cut.

Key invariants to respect when editing:

- **No module-level map caches.** All map state lives on `belief.worldmap`
  (episode-scoped). This was a deliberate fix to a latent beacon bug class.
- **The wire is the only map source.** If you need a map fact, derive it in
  `worldmap.nim` from the init snapshot; never constant-ize a generated map.
- **Multi-team throughout**: any code touching "the enemy" must handle 1-3
  enemy colors and hearts leaving play (`belief.heartsRetired`).
- Seat conventions must work when another entrant owns the trailing half of
  our team's seats (the current even captain/ally split in `2v2`-mode
  invasions). Do not assume the disabled ladder's equal four-seat entrant
  blocks, nor the retired 7+7+1+1 seating.

## Docs

- [`docs/README.md`](docs/README.md) — complete documentation index and ownership map.
- [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md) — game reference. **Start here.**
- [`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md) — required evaluation contract.
- [`docs/recon/paintbot-2026-08-03.md`](docs/recon/paintbot-2026-08-03.md) — the founding recon.
- [`docs/designs/stencil-v1-design.md`](docs/designs/stencil-v1-design.md) — stencil architecture.

## Skills

One paintbot-local skill exists: `lessons-review` (in
[`.claude/skills/`](.claude/skills/), the periodic lessons-archive review). No
paintbot-specific *loop* skills yet. The loop's **game-agnostic** halves (experience
requests, artifact download, build-and-upload, policy lifecycle, A/B,
hypothesis miner) live at the **lab root** (`../.claude/skills/`, indexed in
[`../AGENTS.md`](../AGENTS.md)). Still missing: a Paintbot event warehouse +
survey (per-variant win path) and a `compare.py` A/B metric adapter
(pot-scoring aware).

## Testing discipline

The hosted eval is the test; speed wins. For a targeted local question, use
`tools/self_play.py`; for a recorded wire regression, use
`tools/compare_stencil.py`. Do not rebuild a broad pre-upload test gate.

## Working context & tentative lessons

Two session-spanning files carry state forward — **read both on startup**:

- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — the live, minimal state of
  what we're working on right now. Keep it updated; clear/reseed on a pivot.
- **[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)** — this session's eager
  candidate-lessons buffer (auto-rotated by `tools/rotate_lessons.sh`, archived
  to [`lessons_archive/`](lessons_archive/); recurring lessons graduate to
  `best_practices.md` via the lessons-review flow).

**Cleanup step when wrapping a thread**: capture lessons; reconcile
WORKING_CONTEXT.

## Deferred tasks

Paintbot-specific parked work lives in the shared [`../TODO.md`](../TODO.md).

## Player policies

- **stencil** *(native Nim)* — at
  [`paintbot/stencil_nim/`](paintbot/stencil_nim/), the primary competing
  Paintbot policy. **Current as of 2026-08-29: `stencil:v68` is the active
  champion (submitted 2026-08-14, also competing in the new Elite Paintbot
  league); `stencil:v58` is the previous champion, benched**.
  Version
  history: [`paintbot/stencil_nim/VERSION_LOG.md`](paintbot/stencil_nim/VERSION_LOG.md).
  Behavior knobs are `STENCIL_*` env vars declared in `config.nim` and set at
  upload time for A/B.
  Build: `tools/build_player.sh stencil`.

- **rl** *(Qwen behavior cloning)* — at [`paintbot/rl/`](paintbot/rl/), a
  parallel research track, **not a competing policy**. Cross-era SFT over
  replay-extracted actions; the full replay-to-checkpoint pipeline is
  implemented, but no checkpoint has beaten previous-mask persistence, so
  nothing from this track has been uploaded. Design:
  [`docs/designs/rl-policy.md`](docs/designs/rl-policy.md); pipeline usage:
  [`paintbot/rl/README.md`](paintbot/rl/README.md). Its corpora and results
  (`paintbot/rl/data/`, `paintbot/rl/results/`) are deliberately untracked.
