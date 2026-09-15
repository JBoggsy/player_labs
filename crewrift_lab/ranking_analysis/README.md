# Crewborg ranking and differential analysis

Tools for comparing role-specific behavior across scored episodes. Resolve fresh
matched data before interpreting the results as field performance.

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
    ├── voting_metrics.json       # voting_metrics.py output (voting_report_gen.py input)
    └── RESULTS_bt.txt
```

## Regenerate from committed data (no warehouse needed)

The ranking, the Bradley-Terry model, the differential analysis and the report
all regenerate from the committed `data/` — the 1.4 GB event warehouse is **not**
required for these:

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

Build a fresh warehouse using the Crewrift event-warehouse skill. Match the
replay decoder to the recorded game artifact, validate identity joins and inspect
trace completeness before running `voting_metrics.py`.

## Method notes

Exclude operationally invalid games as whole episodes and report their counts.
Separate player roles, condition tactical metrics on opportunity and include
uncertainty. Associations do not establish that a behavior causes wins. A fresh
matched experiment is required to assess a proposed policy change.
