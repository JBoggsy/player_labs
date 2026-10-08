# webdiplomacy_lab — agent guide

The **webDiplomacy** corner of player_labs: building, evaluating and improving player
policies for the `webdiplomacy` Coworld (classic 7-power Diplomacy on the real
webDiplomacy server). **Read the root [`../AGENTS.md`](../AGENTS.md) first.** It defines
the loop, speed-first, the submission gate and the shared skills. This file adds what
is specific to webDiplomacy.

## The game in one paragraph

Seven powers, 34 supply centres, simultaneous orders, 18 centres to solo. Two leagues:
`webDiplomacy Gunboat` plays `classic-gunboat` (no press, 1-minute phases, ends 1910 as a
draw) and `webDiplomacy` plays `classic-press` (public and private press, 4-minute
movement phases, ends 1908). A draw
scores SC² / Σ SC² over survivors, so being the **largest** survivor matters
quadratically. Full rules, player contract, gotchas and evidence formats are in
[`docs/webdiplomacy-gameplay.md`](docs/webdiplomacy-gameplay.md).

## Rules specific to this lab

- **Stratify every metric by power.** Country is random per episode and power strength
  dominates raw score. Compare against the **same-batch field par** for that power
  (`wd.py metrics` does this).
- **One copy of our policy per hosted episode** (one `policy_ref` seat, `slot: -1`) plus
  six opponents. Until other entrants exist, opponents are the league filler
  (`272d637a-6628-4040-a28c-8e9fb1ccf96f`, the bundled random bot) as explicit refs:
  `random` would sample the champion pool, which is only us.
- **No hosted self-play.** All-our-policy games run locally (`wd.py local`). A local
  gunboat game takes about 45 seconds.
- **Diff saved orders every phase.** Upstream silently drops invalid orders. Our bot
  logs `rejected` per decision, and any nonzero count is a bug.
- **Every behaviour change ships with activation tracing**: add a counter to the
  bot's `trace` in the same change.

## Instruments

Single entry point: `uv run python webdiplomacy_lab/tools/wd.py`.

| Command | Purpose |
| --- | --- |
| `wd.py metrics DIR... --policy NAME:vN [--json]` | Per-power score/final SCs/survival/solo vs field par, coverage, telemetry (rejections, exceptions, activation counters). Exit 2 = no target seats |
| `wd.py seats DIR... [--policy NAME:vN]` | One JSON row per seat (SC trajectory by year, adjudicated order stats, our log summary) |
| `wd.py local --image IMG --episodes N [--variant classic-press-short] [--use-llm]` | Local all-seat episodes (needs `coworld_pkg/` from `coworld download`). `--use-llm` needs `tools/llm_sidecar_local.py` running on the host and `COWORLD_LLM_ENDPOINT=http://host.docker.internal:<port>` (plus optional `COWORLD_LLM_MODEL`) in the host environment |
| `tools/llm_sidecar_local.py --port P --ledger FILE` | Host stand-in for the hosted LLM sidecar (same routes, stream rejection, stripped fields, spend header). Needs `OPENROUTER_API_KEY` from the token broker (`openrouter.inference`). Run it outside the command sandbox, or inbound connections never arrive |
| `uv run --with diplomacy==1.1.2 python webdiplomacy_lab/tools/game_viewer.py EPISODE_DIR [--out FILE]` | Post-game slide-show replay (one self-contained HTML file, default `EPISODE_DIR/viewer.html`): per movement phase an Orders slide (press as a chat log, map with adjudicated orders) and a Resolution slide (positions after adjudication and retreats, bounces, dislodgements, centre changes); per winter a Builds and a Resolution slide; a final Results slide with scores and LLM spend. Keys: ←/→, Home/End; `#N` links a slide |
| `wd.py costs DIR... [--json]` | Press-player LLM spend from seat logs: per seat/game, per movement phase, and projected `classic-press` game cost with 1 or 7 LLM seats |
| `wd.py arena --candidate POLICY[:K=V,...] [--field dumbbot_v1] --image TAG --episodes N --parallel P --out DIR` | **Local screening**: slot 0 = candidate, slots 1-6 = field, fresh seed per game. Read with `metrics DIR --slot 0`; parity is 1/7 = 0.143. Use a **distinct image tag per experiment**: rebuilding a tag mid-run silently switches later games to the new code. Killing an arena (`pkill -f <out dir>`) leaves its game/player containers running: remove them with `docker ps --format '{{.Names}}' \| grep <run id> \| xargs docker rm -f` |
| `tools/compare.py BASE CAND --baseline A:vN --candidate B:vM` | `coworld-ab` adapter (groups: all + each power) |
| `tools/features.py` | `coworld-hypothesis-miner` adapter over `wd.py seats` rows |

Evidence goes under `webdiplomacy_lab/evidence/<experiment>/` (gitignored). Request
bodies and creation responses go under `experiments/<experiment>/` (committed).

## Player

[`webdip_bot/`](webdip_bot/README.md) holds every agent in one image: DumbBot, SearchBot
(the champion line, with the fast adjudicator), NashBot, and the personality roster.
Platform policies:
- `webdip-dumbbot` is the champion lineage:
  - v1 DumbBot;
  - v2–v3 search;
  - v4 fastadj search;
  - v5 opponent-belief fix;
  - v6 Kissinger (level-1 opponents);
  - v7 convoy approximation;
  - v8 modular refactor + Nim adjudicator (behaviour identical to v7).
- `webdip-<personality>` policies are the league fillers. The league filler roster is
  curated through the filler-policies API (see the gameplay doc).

Build: `docker buildx build --platform linux/amd64 --load --build-arg POLICY=<name> -t
<tag> webdiplomacy_lab/webdip_bot`.

Self-play tooling:
- `wd.py tourney` runs mixed populations; `--fixed 'a;b'` gives league-sims and in-game A/Bs.
- `wd.py ratings` gives the power-adjusted leaderboard.
- `tools/evolve.py` runs continuous evolutionary self-play, with the champion as the anchor.
- `tools/value_fit.py` fits the learned evaluation.
- `tools/stop_run.sh` stops a run and its containers.
- `tools/paired.py DIR A B` gives the paired difference of two agents seated in the same games.
- `webdip_bot/golden.py` holds the behaviour contract (run `check` after any search refactor),
  `check_search_parity.py` runs the deeper differential check, and `profile_search.py` profiles
  or times frozen fixtures.
- The overnight runbook is [`LOOP.md`](LOOP.md).

## Identity hygiene

The Softmax CLI credential file (`~/.softmax/credentials.yaml`) is shared by every
session on this machine. Another session switching players (`coworld player use`)
silently changes what your commands can see. A private user-owned request then
returns 404, and `xp-request episodes` lists it as "unavailable". To avoid both
problems, run lab commands with a private copy:

```bash
H=<scratch>/home; mkdir -p $H/.softmax && cp ~/.softmax/credentials.yaml $H/.softmax/
HOME=$H uv run coworld player use ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce   # James Botts
HOME=$H uv run coworld upload-policy IMG --name NAME
HOME=$H uv run coworld player unset
```

Docker needs `DOCKER_CONFIG=~/.docker` when HOME is overridden.

## Working context and guidance

Current objective and next decision: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md).
Testable unresolved ideas: [`TENTATIVE_LESSONS.md`](TENTATIVE_LESSONS.md). Supported
game-specific rules: [`best_practices.md`](best_practices.md). Update in place; no
session logs.
