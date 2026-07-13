# Vanilla WoW — RFC roles & round scoring

Coworld games ship not just a *game* and a *player*, but a set of **support roles** that
run the competition around them: a **commissioner** that schedules rounds, a **grader** and
**diagnoser** that analyze finished episodes, an **optimizer** seed, and a **reporter** that
renders results. This doc explains each role for the Vanilla WoW game's `rfc-five-player-clear`
benchmark, plus the exact round-scoring math that turns episodes into a ranking.

Read [`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md) first for what an episode *is* and
the per-slot raw score; this doc is the layer above it — how episodes become a ranked round.

Citations are `file:line` into `~/coding/coworlds/coworld-vanilla-wow` (read 2026-07-13).

---

## The picture

The four Python support roles (**commissioner, grader, diagnoser, optimizer**) all ship in
one dedicated **`{{COWORLD_SUPPORTING_IMAGE}}`** ("coworld-supporting"), kept separate from
the reference-player image so the Coworld runner's dependencies stay out of the player
(`docs/coworld-rfc-roles.md:40-42`). The **reporter** is a repo-owned **Rust/Wasm**
component. Only the commissioner runs *automatically* (it's the league's scheduling
service); grader and diagnoser are **on-demand** post-episode tools the runner does not
invoke on its own (`docs/coworld-rfc-roles.md:61-62`).

```
                       ┌─────────────────────────────────────────────┐
   entrants ──────────▶│  COMMISSIONER  (vanilla-wow-rfc-commissioner) │
   (policy versions)   │  /round WS: schedules 1 episode per entrant,  │
                       │  5 slots = same policy; emits round rankings  │
                       └───────────────┬─────────────────────────────┘
                                       │ episodes run (isolated servers)
                                       ▼
                          results.json + CWREPLAY bundle
                                       │
        on-demand ┌────────────────────┼───────────────────────┐
                  ▼                     ▼                        ▼
             GRADER               DIAGNOSER                  REPORTER (Rust/Wasm)
        0..1 boss fraction   missing bosses + advice      recap / events / stats
        → COGAME_GRADE_URI   → COGAME_DIAGNOSIS_URI        (softmax:reporter@0.1.0)

             OPTIMIZER (reserved seed): reads manifest + optional report/grade/diagnosis
                       → RfcOptimizerPlan at COGAME_OPTIMIZER_OUTPUT_URI
```

---

## The five roles

### Commissioner — `vanilla-wow-rfc-commissioner`

The league's scheduling service (`src/vanilla_wow_coworld/rfc_commissioner.py`; manifest
`coworld_manifest_template.json:476-484`; doc `docs/coworld-rfc-roles.md:43-46`).

- **Image / entry:** `{{COWORLD_SUPPORTING_IMAGE}}`, run `vanilla-wow-rfc-commissioner`.
- **Interface:** implements `/healthz` + the Coworld `/round` WebSocket
  (`rfc_commissioner.py:262-329`).
- **What it does:** declares one division **"RFC Speedrun"** (`RFC_DIVISION_NAME`,
  `rfc_commissioner.py:40`, `:51-61`), handles league migration (`:64-80`), **schedules one
  five-slot RFC episode per entrant** with `self_play=True` and
  `policy_version_ids = [entrant] * 5` (`:95-157`), and emits per-division rankings
  (`:195-259`).
- **Runs automatically** — it *is* the WebSocket the platform drives. It consumes
  `RoundStart` / `EpisodeResult` protocol messages and the league
  `commissioner_config.game_config_overlay_secret` (the pointer to the confidential roster
  snapshot), not episode-artifact env vars (`rfc_commissioner.py:124-131`).

### Grader — `vanilla-wow-rfc-grader`

A post-episode scorer that reduces an episode to a single 0..1 number
(`src/vanilla_wow_coworld/rfc_grader.py`; manifest `:486-494`; doc `:48-50`).

- **Consumes:** env `COGAME_EPISODE_BUNDLE_URI`. **Produces:** `COGAME_GRADE_URI`
  (`rfc_grader.py:30-34`).
- **Output — `RfcGrade` JSON:** `score = round(bosses_defeated / bosses_total, 6)` (the
  fraction of the four RFC boss kill objectives completed), plus `bosses_defeated`,
  `bosses_total`, `full_clear`, and `full_clear_seconds` (elapsed only on a full clear)
  (`rfc_grader.py:20-27`, `:37-50`).
- **On-demand** — the episode runner does not invoke it automatically (`:61-62`).

### Diagnoser — `vanilla-wow-rfc-diagnoser`

A post-episode explainer (`src/vanilla_wow_coworld/rfc_diagnoser.py`; manifest `:496-504`;
doc `:51-54`).

- **Consumes:** `COGAME_EPISODE_BUNDLE_URI` + `COGAME_TARGET_POLICY_URI`. **Produces:** a
  deterministic zip at `COGAME_DIAGNOSIS_URI` (`rfc_diagnoser.py:47-52`).
- **Output zip:** `manifest.json`, `diagnosis.md`, `findings.json` (`:124-131`). Findings
  name the **`missing_bosses`** and give route/survival/god-view recommendations **without
  claiming evidence that is absent** — e.g. it only recommends god-view inspection when a
  god-view stream actually exists (`_has_godview_stream`) (`:55-102`).
- **On-demand** (`:61-62`).

### Optimizer — `vanilla-wow-rfc-optimizer`

A reserved, deterministic seed-plan generator (`src/vanilla_wow_coworld/rfc_optimizer.py`;
manifest `:506-514`; doc `:55-59`).

- **Consumes:** `COWORLD_MANIFEST_URI` (required) + `COGAME_OPTIMIZER_OUTPUT_URI` (output),
  plus optional `COGAME_OPTIMIZER_ID`, `COGAME_POLICY_WORKSPACE_URI`, and comma-separated
  URI lists `COGAME_REPORT_URIS`, `COGAME_GRADER_OUTPUT_URIS`, `COGAME_DIAGNOSER_OUTPUT_URIS`
  (`rfc_optimizer.py:50-63`).
- **Output — `RfcOptimizerPlan` JSON:** coworld name, variant id, workspace uri, input
  counts, recommendations (`:41-92`).
- **Status:** "The Coworld optimizer contract is still reserved; this entry is useful as
  game-specific seed context, not a replacement for the canonical interactive workbench"
  (`docs/coworld-rfc-roles.md:58-59`). Coworld's Executable verifier intentionally skips
  optimizers (`docs/coworld-readiness.md:21`).

### Reporter — `vanilla-wow-rfc-episode-report`

The human-facing renderer, and the one role that is **not** Python — it's a repo-owned
**Rust/Wasm** component targeting **`softmax:reporter@0.1.0`** (`docs/coworld-rfc-roles.md:64-87`;
manifest `:438-474`, `world: "softmax:reporter@0.1.0"`, wasm at
`reporters/rfc/vanilla_wow_rfc_reporter.wasm`).

- **Consumes:** `results.json` for each explicitly supplied episode (it accepts only the
  reporter world's explicit `episodes` subject; round/league/player/freeform discovery
  **fails clearly rather than guessing**) (`:69-70`, `:80-82`).
- **Produces three parts** (manifest `:445-462`):
  - **`recap`** (`render-markdown`) — a Markdown table of outcome, boss progress, clear
    time, and party deaths.
  - **`events`** (`event-log`) — one final-tick event per boss objective, plus the
    full-clear time when all four bosses are complete.
  - **`stats`** (`json`) — conforms to `reporters/rfc/rfc-stats.schema.json`.
- Same clear rule as everywhere: full clear only when *every* kill objective is complete,
  and only full clears get a clear time (`:78-80`). Reproducible from a pinned Cargo
  lockfile + WIT contract; build with `python3 tools/build_rfc_reporter.py` (`--check` for a
  byte-for-byte compare) (`:84-87`).

The shared IO models for the on-demand roles (`RfcEpisode` / `RfcResults` / `RfcDungeonRun`,
computing `boss_objectives`, `missing_bosses`, `bosses_defeated`, `full_clear`,
`elapsed_seconds`) live in `src/vanilla_wow_coworld/supporting_role_io.py:57-99`; they
require the replay be a canonical v4 `CWREPLAY` with a world-session POV (`:155-161`).

---

## Round scoring — how episodes become a ranking

The commissioner turns each entrant's episode into one **round score**
(`rfc_commissioner.py:184-192`):

```python
if full_clear:
    return max(1.0, 1_000_000.0 - clear_seconds)   # faster clear → higher score
else:
    return bosses_defeated / bosses_total           # a fraction in [0, 1)
```

Consequences:
- **Every full clear (≥ 1.0) outranks every partial run (< 1.0).**
- **Among full clears, the fastest wins** (subtracting `clear_seconds`).
- A **full clear** requires **all four** boss kill objectives complete; only full clears get
  a recorded `best_clear_seconds` (else `None`) (`rfc_commissioner.py:160-181`).

The commissioner derives the per-episode metadata in `_dungeon_metadata`
(`rfc_commissioner.py:160-181`): boss objectives are the `kind == "kill"` objectives;
`bosses` = how many are complete; `full_clear` = non-empty boss set AND all complete;
`best_clear_seconds` = max `elapsed_seconds` across score rows, but only when `full_clear`.

Round ranking then sorts entrants by `(-score, best_clear_seconds or +inf, policy_version_id)`
and assigns ranks; each `RankingEntry` carries `result_metadata` with `full_clear`,
`best_clear_seconds`, `bosses_defeated`/`bosses_total`, `variant_id`, `party_size`,
`failed`, and `mean_game_score = fmean(scores)` (`rfc_commissioner.py:216-246`).

> **How the round score relates to the per-slot raw score.** The per-slot raw score
> (`objectives×1e6 + bosses×250k + xp − deaths×10k − elapsed`, see
> [`vanilla-wow-gameplay.md`](vanilla-wow-gameplay.md#the-per-slot-raw-dungeon-score)) is
> what each of the five characters earns. The **round** score above is computed from the
> episode's *clear status and time*, not by summing slot scores — XP does not change the
> round ordering, only whether-and-how-fast the party cleared. `mean_game_score` (the mean
> of the five raw slot scores) is carried in metadata for context, not as the ranking key.

---

## What this means for the lab (once real rounds exist)

- **The competition metric is clear-then-speed.** Our first job for any RFC-targeting
  player is *cross the "full clear" threshold* — a partial run scores < 1.0 regardless of
  XP or how many bosses fell. Only after reliable clears does shaving `clear_seconds` pay.
- **The grader/diagnoser/reporter are our analysis surface.** When real episodes exist, the
  reporter's `recap`/`events`/`stats` and the diagnoser's `missing_bosses` findings are the
  natural inputs to a lab report — analogous to how `crewrift-survey` distills Crewrift
  episodes. Building a Vanilla-WoW survey/report skill on top of them is the top tooling gap
  (see [`../AGENTS.md`](../AGENTS.md#skills)).
- **Readiness gate.** The "ready" badge is gated on one *retained* hosted commissioner round
  + one XP-request episode on Kubernetes, neither yet created
  (`docs/coworld-readiness.md`) — so this round machinery is certified but has not produced
  a retained scored round yet. Verify current state before relying on it.
