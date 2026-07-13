# ctf_lab — agent guide

The **CTF** corner of player_labs: where we build, evaluate, and improve **player
policies** for Coworld CTF. This file orients agents working here.

**Read the lab-root [`../AGENTS.md`](../AGENTS.md) first** — it defines the improvement
loop, your role in it (speed first), the submission gate, and the game-agnostic skills.
This file is the **CTF-specific layer** on top of it: the game, the docs, the
practices/preferences, and the policies we optimize. When the two disagree, the root
defines *process*; this file defines *CTF*.

> **Lab status (2026-07-10): first player `beacon` built, uploaded, and competing.** The
> game repo (`Metta-AI/coworld-ctf`) is cloned for reference at `~/coding/coworlds/coworld-ctf`.
> **`beacon` (Python, [`ctf/beacon/`](ctf/beacon/)) is on `beacon:v5`** (v4 is the currently
> submitted/competing version). It beats the co-gas opponents 20-0 by capture and, as of v5,
> takes games off the elite Nim `ctf-baseline-16` too (4-11, via carrier escort). Live state:
> [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md); versions: [`ctf/beacon/VERSION_LOG.md`](ctf/beacon/VERSION_LOG.md).

## What CTF is

CTF is a Coworld **two-team (8v8) capture-the-flag shooter** on the **BitWorld Sprite-v1**
protocol (same protocol family as Crewrift and Heartleaf). Two teams spawn on opposite
edges of a symmetric, cover-dense arena, each guarding a flag. You move (d-pad), aim a
continuous angle **decoupled from movement** (B/Select), and shoot an instant hitscan gun
(A). Vision is **fog-of-war** riding your aim (±45° cone + small omni bubble; walls
block). Win by **capturing** the enemy flag (carry it into your home zone) or **wiping**
the enemy team. **Scoring is win-only: +100 to the winning team, 0 otherwise** — the
objective is purely team victory, not kills.

For the full game — arena, aim/vision/combat mechanics, flags, exact tuning numbers, the
wire protocol, the baseline bot, and a strategy treatment — read
[`docs/ctf-gameplay.md`](docs/ctf-gameplay.md) (the lab's self-contained reference; you
rarely need to leave the repo). The game source in the `Metta-AI/coworld-ctf` repo
(server `src/ctf.nim`, rules `docs/RULES.md`, baseline `players/baseline/`) remains the
ultimate authority.

**The one architectural fact that shapes everything here:** CTF is a **fork of Crewrift**
and keeps its Sprite-v1 protocol, continuous movement, line-of-sight, and replay
infrastructure. So the tooling and player patterns from `crewrift_lab/` (perception
decoder, movement controller, nav cost field) and the SDK-bridge wiring from
`heartleaf_lab/cady/` transfer directly — see [Player build paths](#player-build-paths).

## The loop, in CTF terms

The root loop (evaluate → report → direction → implement → rebuild+reupload → repeat →
human gate → submit) runs **unchanged** here. The CTF-specific instruments:

- **Evaluate** (step 1) — experience requests against the uploaded version of the policy
  under optimization. The game is **team-symmetric (8v8)**, so the natural cuts are
  **team (Red/Blue) and seat/role** (slot parity = team; `slot div 2` = seat), **win
  rate** (the only scored outcome), and the **win path** taken (capture vs wipe vs
  timeout-tiebreak). Because scoring is win-only (+100/0), win rate — not kills — is the
  metric; kills/deaths/captures are recorded for diagnosis but never scored.
- **Report** (step 2) — pull artifacts with the game-agnostic `coworld-episode-artifacts`
  skill, then distill. **There is no CTF-specific report skill yet** — see
  [Skills](#skills); building one (a per-episode win-path / kill-map / flag-event survey,
  analogous to `crewrift-survey`) is the highest-leverage tooling investment once
  episodes exist. `tools/build_expand_replay.sh` builds a version-matched replay reader
  that already emits a structured event timeline (kills, flag steals/returns, captures,
  score) to build on.
- **Implement** (step 4) — change the policy under optimization (see
  [Player build paths](#player-build-paths)); keep tunable knobs (aim-scan cadence, fire
  gate, role assignment, nav exposure cost) in a config layer separate from logic so each
  iteration is attributable.
- **Rebuild / upload / submit** (steps 5–8) — build the policy image, then the
  game-agnostic skills + [`../player-build.md`](../player-build.md) for the upload/submit
  flow. The hosted eval is the test; **do not** buy pre-upload confidence with local runs
  (the `coworld-local-run` skill is a debugging tool for a broken artifact, not a gate).

## Player build paths

> **Chosen: path 1** — `beacon` is a Python Player-SDK policy on the SpriteV1 bridge. The
> paths below stay as reference for future policies / a rebuild decision.

CTF is a fork of Crewrift with no bundled *Python* framework to reuse (unlike Heartleaf's
`talking_villager`), so the paths are, cheapest first. **Which one to pursue is a
human-direction decision (loop step 3), not a default** — surface the fork, don't
pre-commit.

1. **Python Player-SDK policy on the SpriteV1 bridge (recommended).** Wire it the modern
   way — `run_sprite_bridge(env_ws_url(), decide, ...)` from `players.player_sdk` (the SDK
   owns transport + exit-0-on-close) — and borrow proven CTF-adjacent logic: Crewrift
   `crewborg`'s perception decoder (`perception/`, `cramjam.snappy` sprite-mask decode)
   and d-pad movement controller (`action.py`), plus Heartleaf `cady`'s bridge/`AgentRuntime`
   wiring. Write CTF's own decision layer: aim+vision management, seat-based roles, flag
   steal/carry/escort/defend logic, a nav cost field with exposure penalty. Most reuse,
   full control, no LLM cost.
2. **Fork the Nim `baseline`.** The bundled `baseline.nim` (~1440 lines) is already a
   strong, complete bot (tracks, roles, Dijkstra cost field, peek-fire-duck turret). Edit
   its tuning constants / decision functions and rebuild via a clone-at-ref Dockerfile
   (mirroring `crewrift_lab`'s `notsus`). Fastest to a *working* competitor; tests whether
   the baseline is tuning-limited. Downside: Nim, and you inherit the baseline's
   architecture.
3. **From scratch (any language).** Implement Sprite-v1 directly and package in Docker.
   Only if paths 1–2 hit a ceiling.

When a path is chosen, vendor the policy under this lab (e.g. `ctf_lab/<policy>/`),
mirroring how `crewrift_lab/crewrift/` and `heartleaf_lab/cady/` vendor theirs, and record
a design doc under `docs/designs/`. The **game ref** the Nim path compiles against, and
the **Python SDK pin**, follow the root `pyproject.toml` + the `crewrift_lab/tools/versions.env`
pattern (a `versions.env` gets added here when the first buildable policy lands).

## CTF lab docs

- **[`docs/ctf-gameplay.md`](docs/ctf-gameplay.md)** — the self-contained game reference:
  arena, teams, aim/vision/combat mechanics, flags, win-only scoring, exact tuning
  numbers, the Sprite-v1 wire protocol + SDK bridge, the baseline bot, replay tools, and a
  strategy treatment. **Start here** to build a mental model before reasoning about play
  or setting direction.

More docs (a protocol deep-dive, a player design doc, a replay-reading guide) get added as
the loop generates the need — mirroring `crewrift_lab/docs/`.

## Skills

CTF-specific skills live in `ctf_lab/.claude/skills/`:

- **`ctf-event-warehouse`** — build/query the CTF event warehouse: a policy-indexed
  DuckDB/Parquet store of ground-truth replay events (kills, flag steals/returns, captures,
  scores — via the version-matched `expand_replay_json` binary) **plus** beacon's belief
  traces (snapshots + objective/alive/engage transitions), both re-keyed slot → policy /
  version / team / seat / role. The deep-dig tool for mechanistic, cross-episode questions
  (delivery rate, where carriers die, objective time-share). Built on
  `tools/event_warehouse.py`.
- **`lessons-review`** — the ≈weekly lessons-graduation skill.

The loop's **game-agnostic** halves (experience requests, artifact download, local run,
build-and-upload, policy lifecycle) live at the **lab root** (`../.claude/skills/`, indexed
in [`../AGENTS.md`](../AGENTS.md)) — use those to *create*, *pull*, and *ship* episodes.

**Observability quick reference:**
- `tools/agg_eval.py <dir>` — fast one-line scoreline from a results dir.
- `tools/build_expand_replay.sh` — builds two host-native, version-matched replay readers:
  `expand_replay` (human timeline) and `expand_replay_json` (JSONL for the warehouse).
- **beacon tracing** — structured `TraceEvent`s to the SDK `TraceOutputs` (default
  `jsonl@artifact`; `BEACON_TRACE_OUTPUTS` to override, `BEACON_DIAG_EVERY_TICKS=1` for a
  per-tick trace); falls back to `CTF_DIAG` stderr lines with no artifact URL.

Still worth building: a **CTF survey/report** HTML skill (win rate by team/seat, win path)
analogous to `crewrift-survey`.

## CTF best practices

[`best_practices.md`](best_practices.md) holds CTF-specific practices layered on top of the
root [`../best_practices.md`](../best_practices.md) — things true of *this game's* tooling
and failure modes. It starts near-empty and fills in via the lessons pipeline below.
**Read both**; root first.

## CTF user preferences

There is no CTF-specific `user_preferences.md` yet; the root
[`../user_preferences.md`](../user_preferences.md) applies. When the human states a
CTF-specific durable preference, create `user_preferences.md` here and record it
(mirroring the other labs' layering).

## Testing discipline (CTF-specific)

**Do minimal, tightly-focused testing.** Write a test only when it covers something
genuinely *critical* — a load-bearing invariant, a rule the game enforces strictly (e.g.
the button-mask encoding, aim-brad arithmetic, or a flag state transition), or a
regression that would silently lose games or crash an episode — and be **sparing** even
with those. The hosted eval is the test; speed wins (root AGENTS.md). No
coverage-for-its-own-sake. When unsure whether a test earns its place, prefer not writing
it — or ask.

## Working context & tentative lessons

Two session-spanning files carry state and learning forward between sessions — **read both
on startup** alongside the preferences above:

- **[`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)** — the **live, minimal, high-signal state
  of what we're working on right now**: the current objective plus the few facts worth
  carrying forward (active policy/version, the working lens, live findings, open threads).
  Read it to resume, **keep it updated as you learn**, and **clear/reseed it when we
  pivot**.
- **[`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md)** — **this session's** eager, noisy
  buffer of candidate lessons: write here freely, AS YOU GO, the moment something *looks*
  like a reusable lesson. Most entries are noise; the value is the occasional gem. **The
  lifecycle is automated**: a SessionStart hook archives each session's buffer to
  [`lessons_archive/`](lessons_archive/) and creates a fresh one
  (`tools/rotate_lessons.sh`); the **`/lessons-review`** skill
  (≈weekly, human-driven) clusters lessons that RECUR across archived sessions and
  graduates keepers to `best_practices.md`. Recurrence across sessions — not in-session hit
  counts — is the graduation signal. (The hook is registered in the **root**
  `.claude/settings.json`, alongside crewrift's, cue-n-woo's, and heartleaf's. Writing
  lessons as you go is the agent's discipline — there is no Stop-hook nudge; it was
  removed 2026-07-13.)

**Cleanup step — run when you wrap up a thread (and before you push/land work).**

1. **Capture all tentative lessons** into [`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md) —
   eagerly; an un-recorded lesson is a lost one.
2. **Reconcile working context** — prune completed/stale detail from
   [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md), update the active policy/version, and
   clear/reseed it on a pivot.

## Deferred tasks

CTF-specific parked work lives in the **shared** [`../TODO.md`](../TODO.md) alongside the
rest of the lab's deferred tasks. Check it at the start of focused work.

## Player policies

- **beacon** *(Python)* — at [`ctf/beacon/`](ctf/beacon/), the primary (only) CTF policy.
  A **deterministic cyborg Player-SDK policy on the SDK's SpriteV1 bridge**
  (`players.player_sdk.run_sprite_bridge` — no vendored wire layer, build path 1):
  `perceive` reads the raw `SpriteWorld` labels into a `CtfState`, `belief` folds it
  (team/seat from slot, dead-reckoned aim), a seat-based `strategy` picks one objective
  (carry-home > intercept-visible-thief > defender-hold / attacker-steal), and
  `action` emits a `Button` mask — d-pad movement + a **lighthouse aim sweep** across the
  threat axis that snaps to a visible enemy, behind a fire-gate with a **friendly-fire
  guard**. Navigation is **offline-baked** (`tools/bake_map.py` → `mapdata/nav.npz`: an 8px
  walkable grid, two Dijkstra flow fields per team, and a cover-cell grid); online A*
  handles dynamic goals. Design:
  [`docs/designs/ctf-player-v1-design.html`](docs/designs/ctf-player-v1-design.html).
  **Current: `beacon:v5`** — seat-based roles (**3 defenders** on cover / **5 attackers**),
  friendly-fire gate, carry-detection fix (a carried flag rides ~10px above its carrier),
  and **carrier escort** (attackers converge on a teammate carrier and move home with it).
  Beats both co-gas opponents 20-0 **by capture**, and **takes games off `ctf-baseline-16`**
  (4-11 vs the champion, up from 0-20 — it wins by capturing before being wiped, not by
  out-fighting). Version history: [`ctf/beacon/VERSION_LOG.md`](ctf/beacon/VERSION_LOG.md).
  Behavior knobs are env vars in `ctf/beacon/config.py` (`BEACON_DEFENDERS`,
  `BEACON_FF_CORRIDOR_PX`, …), set at upload time for A/B. Build: `tools/build_player.sh beacon`.
  **Next (open thread):** raise the baseline win rate above 26% — survive the grab-and-run
  better (tighter escort, staggered pushes), enemy-track memory, exposure-aware routing.
