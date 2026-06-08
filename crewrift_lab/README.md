# crewrift_lab

Experimentation and optimization for **Crewrift** players. See the
[lab-wide README](../README.md) for the player contract, setup, and gotchas.

## The game

Crewrift is an 8-player social-deduction game (Among Us–style: crewmates do
tasks and vote out imposters; imposters kill, vent, and blend in). It speaks the
**binary Sprite-v1 protocol** — the engine streams sprite/screen frames and the
player emits gamepad bytes. There is **no semantic "do task / vote" API**; a
player decodes pixel positions + sprite IDs into game state itself.

- Engine source: `~/coding/coworlds/coworld-crewrift` (`src/crewrift/sim.nim`,
  `global.nim`); reference player `players/notsus`.
- World manifest: `~/coding/metta/worlds/crewrift/coworld_manifest_template.json`.

## The target player: crewborg

`~/coding/players_checkouts/players/players/crewrift/crewborg/` — a mature
Player-SDK agent that plays both roles end-to-end. Three tiers: **strategy**
(mode selector over belief) → **mode** (one intent/tick) → **action layer**
(intent → wire command). Key pieces: Bayesian `strategy/suspicion.py`
(posterior `P(imposter)` per player), `agent_tracking.py` (reachability-disc
location beliefs), `perception/` (Sprite-v1 decoder), `nav.py` (baked A* nav
graph), `modes/` (idle/normal/attend_meeting/report_body/flee + evade/pretend/
search/hunt). Its `design.md` and `AGENTS.md` are the source of truth.

## Workflow A — evaluate / measure

Use the `crewrift-experience-analysis` skill to run hosted experience-request
batteries vs the live roster and produce role-broken-down stats + replay picks:
resolve live standings → choose experiment shape (random / requester-mix /
imposter round-robin) → poll → analyze (`analysis.sqlite`, `role_summary.csv`,
pairwise effect sizes) → download replays. Crewborg's
`scripts/fetch_episodes.sh -n N` pulls full data (episode + replay + per-slot
stderr trace) for its most recent league episodes, viewable in `viewer/`.

Always resolve the **current** league/division/policy-version IDs first — never
reuse cached IDs.

## Workflow B — build / iterate

Local test against a Crewrift dev server, then build + submit:

```sh
# from the crewborg checkout root (~/coding/players_checkouts/players)
uv run pytest players/crewrift/crewborg/tests
players/crewrift/crewborg/scripts/play_local.sh        # vs a local Crewrift server
players/crewrift/crewborg/build.sh                     # build amd64 image + manifest snippet
```

Open optimization surfaces (start here):
- **`design.md §12` tuning parameters** — suspicion thresholds, vote bar, flee
  threshold, kill isolation/urgency bars — explicitly await tuning against the
  live server. Measure each change with Workflow A.
- **Imposter aggression** — `CREWBORG_BE_DUMB=1` (search-and-hunt-only) vs the
  default pretend/evade behavior.
- **LLM meetings** — `CREWBORG_LLM_MEETINGS=1` (+ `ANTHROPIC_API_KEY`) Haiku-class
  chat/vote vs the deterministic canned-chat fallback.

This lab holds the experiment configs, parameter sweeps, and analysis outputs;
player code changes land in the crewborg checkout and ship as new policy
versions.
