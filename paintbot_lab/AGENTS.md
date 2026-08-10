# paintbot_lab — agent guide

The **Paintbot** corner of player_labs: where we build, evaluate, and improve
**player policies** for Coworld Paintbot. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the
improvement loop, your role in it (speed first), the submission gate, and the
game-agnostic skills. This file is the **Paintbot-specific layer**: the game,
the docs, the practices, and the policy we optimize. When the two disagree, the
root defines *process*; this file defines *Paintbot*.

> **Lab status (2026-08-07): v54 champion, v58 newest.** `stencil:v54` is the
> active James Botts champion, a hosted-validated GV40 continuous-aim correction
> retaining v52's squad behavior; v52 is the previous champion. Versions v55-v58
> are uploaded but **inert** (never submitted); v53 is rejected. Always verify
> live rather than trusting this snapshot.
> Stencil lives at [`paintbot/stencil_nim/`](paintbot/stencil_nim/) and its
> immutable upload history is recorded in
> [`VERSION_LOG.md`](paintbot/stencil_nim/VERSION_LOG.md). The game repo is
> the SAME clone as CTF's
> (`~/coding/coworlds/coworld-ctf` — paintbot is a second manifest over the
> same binary; **ctf_lab itself is archived** — see [`../ctf_lab/README.md`](../ctf_lab/README.md)).
> Deployed paintbot is **0.7.216 / GameVersion 41**; the lab **builds** against
> 0.7.215 / `6c7a4c0e` (`tools/versions.env`), one sprite-only release behind —
> 0.7.216's `config_schema` and `variants` are byte-identical to 0.7.215's, so
> nothing in the pin's contract moved. GV41 brought the endgame grenade
> barrage and paint puddles; 0.7.212-215 added **team perks** and **cardboard
> barriers**, both config-gated and OFF in every deployed variant. v58 evacuates
> toward map center on the barrage marker; **paint puddles, perks, and barriers
> all remain unmodeled**
> (see [`docs/recon/paintbot-gv41-hazards-2026-08-07.md`](docs/recon/paintbot-gv41-hazards-2026-08-07.md)
> and the perks/barriers section of [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md)).
> The league redeploys often and **an upstream manifest merge auto-uploads the
> next version**, so this pin goes stale without anyone here acting — check
> `uv run coworld list | grep paintbot` at the start of game-mechanics work. Live
> state: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).

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
- **Campaign-shaped full seating**: normal invasions use four policies. Current
  two-team variants—including map ref `1v1`—are campaign mode `2v2` and use
  7+7+1+1 captain/ally seating; four-team FFA gives one color to each policy.
  Inspect the cell mode and final roster instead of inferring from names.

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
carries the scrap-vs-port ledger). The architecture in one breath: `perception`
reads labels **plus** the walkability sprite pixels and wire markers; the
runtime builds an **episode-scoped `WorldMap`** (eroded nav grid, cover, lazy
per-goal Dijkstra flow fields, derived chokes/rallies/spawn-aim — replacing
beacon's `nav.npz` bake + POIs + plans wholesale); `belief` folds tracks,
danger, hearing, chat, per-color hearts (with retirement + steal-target
choice); `strategy` runs the ladder (carry-home > intercept-thief >
escort-carrier > grenade-clear > **barrage-center** > early-defense > items >
convert-hunt > consensus squad order > role split — barrage-center evacuates to
the generated map center once the GV41 barrage marker reports `depth > 0`, so
only carry-home, thief interception, and immediate grenade warnings outrank it);
`action` emits the mask (lighthouse sweep, snap/lead aim, fire gate,
friendly-fire guard, peek-fire-duck, grenade overlay). The post-v1 WorldMap
derives per-opponent firing/duck post candidates from online geometry;
defenders occupy distinct homeward-ranked posts and sweep toward the associated
opponent front. Leaderless squads also use those generated posts to execute
consensus hold/watch/move orders. Fixed-map battle plans, general POIs, and
anti-turtle remain cut.

Key invariants to respect when editing:

- **No module-level map caches.** All map state lives on `belief.worldmap`
  (episode-scoped). This was a deliberate fix to a latent beacon bug class.
- **The wire is the only map source.** If you need a map fact, derive it in
  `worldmap.nim` from the init snapshot; never constant-ize a generated map.
- **Multi-team throughout**: any code touching "the enemy" must handle 1-3
  enemy colors and hearts leaving play (`belief.heartsRetired`).
- Seat conventions must work when another entrant owns one allied seat on our
  team in a normal campaign `2v2`-mode invasion. Do not assume the disabled
  ladder's equal four-seat entrant blocks.

## Docs

- [`docs/README.md`](docs/README.md) — complete documentation index and ownership map.
- [`docs/paintbot-gameplay.md`](docs/paintbot-gameplay.md) — game reference. **Start here.**
- [`docs/tournament-like-experience-requests.md`](docs/tournament-like-experience-requests.md) — required evaluation contract.
- [`docs/recon/paintbot-2026-08-03.md`](docs/recon/paintbot-2026-08-03.md) — the founding recon.
- [`docs/designs/stencil-v1-design.md`](docs/designs/stencil-v1-design.md) — stencil architecture.

## Skills

No paintbot-specific skills yet. The loop's **game-agnostic** halves (experience
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
  Paintbot policy. **Current as of 2026-08-07: `stencil:v54` is the active
  champion; `stencil:v58` is the newest uploaded version and is inert — its only
  hosted run is a one-episode mechanism probe, not a performance verdict;
  `stencil:v53` is rejected; `stencil:v52` is the previous champion**.
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
