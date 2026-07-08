# crewborg ranking & differential analysis (v96)

Where crewborg ranks among the live Crewrift Prime champion field, and which
measured behaviours most separate it from the top players — as crew and as
imposter. Built from a **728-clean-game** balanced eval (v96 vs the 12-policy
champion pool, natural roles). The report is a self-contained HTML page.

## Headline findings

- **Rank:** crewborg is upper-middle — overall **4th / 13** (44%); crew BT rank
  **7 (4–9)**; imposter BT rank **6 (4–8)**. Tier is certain; the middle cluster
  is a set of statistical ties at this N.
- **Crew weakness is a *voting* deficit, not tasks/chat:** crewborg skips votes
  ~2× as often as top crew (d=+0.78), calls half the meetings (d=−0.65), casts
  half the player-votes (d=−0.61) — while chatting *more* and completing *more*
  tasks. 256 clean crew losses had 6+/8 tasks done.
- **Imposter weakness is passive hunting + quiet meetings, not kill count:** same
  kills as top imposters (1.77 vs 1.78) but follows 37% less (d=−0.80), chats 39%
  less (d=−0.76), first kill ~20% later (d=+0.36).

Effect sizes are **associational, not causal**.

## Layout

```
ranking_analysis/
├── README.md              # this file
├── _data.py               # shared: clean-game seat table from episode_players.parquet
├── bt_model.py            # team Bradley-Terry rating + bootstrap rank CIs
├── rank_analysis.py       # role-conditional marginal win rates (Wilson CIs)
├── features.py            # per-seat behavioural features from the EVENT WAREHOUSE
├── differential.py        # crewborg vs top-3, Cohen's d + Mann-Whitney, per role
├── report_gen.py          # renders the self-contained HTML report + charts
├── voting_metrics.py      # per-policy vote/chat rate, vote accuracy, ejection effectiveness (event warehouse)
├── voting_report_gen.py   # renders the self-contained HTML voting-behaviour report (reads voting_metrics.json)
├── serve.sh               # serve the report over Tailscale/localhost
├── requests/              # the exact 15-request eval definition (rebuild recipe)
│   ├── req_01.json … req_15.json
│   └── xreqs.txt
└── data/                  # committed inputs + outputs (all small)
    ├── episode_players.parquet   # per-seat policy/role/win/tasks/kills (728 clean games)
    ├── clean_eids.txt            # the 728 clean episode ids (dead connect-timeouts dropped)
    ├── features.json             # DISTILLED per-seat feature table (differential input)
    ├── bt_ranks.json  overall.json  differential.json  rooms.json  replays.json
    ├── report.html               # the deliverable
    ├── voting_metrics.json       # voting_metrics.py output (voting_report_gen.py input)
    ├── voting_report.html        # the voting-behaviour deliverable
    └── RESULTS_bt.txt
```

## Regenerate from committed data (no warehouse needed)

The ranking, the Bradley-Terry model, the differential analysis and the report
all regenerate from the committed `data/` — the 1.4 GB event warehouse is **not**
required for these:

```bash
# from repo root, inside the uv env (deps: duckdb pandas numpy scipy scikit-learn matplotlib)
cd crewrift_lab/ranking_analysis
python bt_model.py        # -> data/bt_ranks.json  (+ prints rank tables)
python rank_analysis.py   # marginal win rates
python differential.py    # -> data/differential.json (reads data/features.json)
python report_gen.py      # -> data/report.html
./serve.sh                # http://<tailscale-ip>:8811/report.html
```

## Extract NEW behavioural features (needs the event warehouse)

`features.py` is the only script that needs the full **event warehouse** (the
1.4 GB DuckDB/Parquet fact table). To add features beyond the committed
`data/features.json`, point `RANK_WH` at a warehouse and re-run it, then
`differential.py` + `report_gen.py`:

```bash
RANK_WH=/path/to/v96_rank_wh python features.py   # rewrites data/features.json
python differential.py && python report_gen.py
```

## Voting behaviour report (crew games only)

`voting_metrics.py` extracts per-policy voting behaviour from the event warehouse — vote rate,
chat rate, vote accuracy, ejection effectiveness (conversion when the target is truly the
imposter; friendly fire when the target is truly a crewmate), and crew win rate — scoped to games
played as crew. Ejection ground truth has no native warehouse event, so it's derived from a `died`
event falling inside a meeting's `vote_called_body`/`vote_called_button` → next-meeting window (see
the module docstring for the derivation and its validation). Same clean-game + `trace_warning`
exclusion philosophy as the rest of this directory.

```bash
# needs a full event warehouse (RANK_WH, default /tmp/v96_rank_wh) — see "Extract NEW
# behavioural features" above for how to get one
python voting_metrics.py       # -> data/voting_metrics.json (+ prints a per-policy summary table)
python voting_report_gen.py    # -> data/voting_report.html
```

Get the warehouse one of two ways:

**A. Transfer the existing one** (fastest). It lives at `/tmp/v96_rank_wh`
(ephemeral) and is archived at `~/v96_rank_wh.tar` on the build machine:

```bash
scp buildhost:~/v96_rank_wh.tar .  &&  tar -xf v96_rank_wh.tar -C /tmp
```

**B. Rebuild from the eval definition** (`requests/`). Fire the 15 requests,
stream the episodes, then build the warehouse. **Note the v0.4.42 quirk:** the
platform stopped zlib-compressing `replay.json.z` (it's now raw `CREWRIFT`
bytes), but `build_warehouse` still zlib-decompresses it — re-compress each raw
replay first:

```bash
S=.claude/skills/coworld-experience-requests/scripts/experience_request.py
for f in crewrift_lab/ranking_analysis/requests/req_*.json; do uv run python "$S" create "$f"; done
# stream/fetch episodes (crewrift-event-warehouse skill: stream_eval.py --xreq … --out /tmp/v96_rank_wh)
python - <<'PY'   # v0.4.42 zlib fix (skip on <=0.4.40)
import glob, zlib
for z in glob.glob('/tmp/v96_rank_wh_episodes/*/replay.json.z'):
    d = open(z,'rb').read()
    if d[:8] == b'CREWRIFT': open(z,'wb').write(zlib.compress(d))
PY
uv run python crewrift_lab/.claude/skills/crewrift-event-warehouse/scripts/build_warehouse.py \
  --episodes /tmp/v96_rank_wh_episodes --out /tmp/v96_rank_wh \
  --expand-replay crewrift_lab/tools/bin/expand_replay --elevated
```

## Method notes

- **Clean games only.** 772 / 1500 games were dead connect-timeouts (a crew
  seat's container never started — heavy LLM cold-start vs a tight platform
  deadline; crewborg's own rate was 24%). Those are dropped at the **game level**
  (`clean_eids.txt`); every stat here is on the 728 fully-played games. Reportedly
  fixed platform-side — a fresh batch should retain full N and tighten every CI.
- **Ranking unit.** Crewrift is a team game (all 6 crew share the outcome), so the
  Bradley-Terry model rates the *game* outcome as `logit P(crew win) = b0 +
  Σ crew_skill − Σ imposter_skill`, attributing the shared result to individuals
  (controls for teammates/opponents, which raw win rates cannot). Rank CIs are
  bootstrapped over games.
- **Differential unit.** One row per (episode, seat); crewborg vs the pooled top-3
  per role; Cohen's d + Mann-Whitney U; ranked by |d|.
