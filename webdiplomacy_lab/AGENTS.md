# webdiplomacy_lab — agent guide

The **webDiplomacy** corner of player_labs: building, evaluating and improving player
policies for the `webdiplomacy` Coworld (classic 7-power Diplomacy on the real
webDiplomacy server). **Read the root [`../AGENTS.md`](../AGENTS.md) first.** It defines
the loop, speed-first, the submission gate and the shared skills. This file adds what
is specific to webDiplomacy.

## The game in one paragraph

Seven powers, 34 supply centres, simultaneous orders, 18 centres to solo. The league
plays `classic-gunboat` (no press, 1-minute phases, ends 1910 as a draw). A draw
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
| `wd.py local --image IMG --episodes N` | Local all-seat episodes (needs `coworld_pkg/` from `coworld download`) |
| `wd.py arena --candidate POLICY[:K=V,...] [--field dumbbot_v1] --image TAG --episodes N --parallel P --out DIR` | **Local screening**: slot 0 = candidate, slots 1-6 = field, fresh seed per game. Read with `metrics DIR --slot 0`; parity is 1/7 = 0.143. Use a **distinct image tag per experiment**: rebuilding a tag mid-run silently switches later games to the new code. Killing an arena (`pkill -f <out dir>`) leaves its game/player containers running: remove them with `docker ps --format '{{.Names}}' \| grep <run id> \| xargs docker rm -f` |
| `tools/compare.py BASE CAND --baseline A:vN --candidate B:vM` | `coworld-ab` adapter (groups: all + each power) |
| `tools/features.py` | `coworld-hypothesis-miner` adapter over `wd.py seats` rows |

Evidence goes under `webdiplomacy_lab/evidence/<experiment>/` (gitignored). Request
bodies and creation responses go under `experiments/<experiment>/` (committed).

## Player

[`webdip_bot/`](webdip_bot/README.md): SearchBot (best response to sampled DumbBot
opponents, adjudicated with the `diplomacy` package) on top of a DumbBot port. Policy
lineage name on the platform: `webdip-dumbbot` (v1 = DumbBot, v2+ = SearchBot). Build:
`docker buildx build --platform linux/amd64 --load -t webdip-bot:<tag>
webdiplomacy_lab/webdip_bot`. Upload as a player identity (James
Botts by default) using the isolated-credential recipe below.

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
