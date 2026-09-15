# Imposter movement lab — see how imposters hunt, spatially, over time

Tools to inspect and compare **how imposters move while trying to find victims**:
where our imposter goes when it's kill-ready and blind, where the top imposters go,
and where the crew actually are. Use it to answer "why can't crewborg's
imposter find people to kill" — see the findings summary at the bottom.

All tools read a **per-tick event warehouse** (`crewrift-event-warehouse` skill, built
with the default `--snapshot-every 1`) and are **meeting-aware** throughout: only
Playing-phase ticks are analyzed (meetings freeze movement ~1300 ticks and teleport
players; including them poisons every latency/distance number).

## The unit of analysis: ready windows

`movement_lib.py` breaks each imposter-game into **ready windows** — maximal spans
where the imposter is alive, Playing, and kill-ready (`kill_cooldown == 0`). A window
ends at that imposter's kill, the next meeting (cooldown reset ⇒ a later kill does NOT
convert this window), death, or game end. Ticks split into `vis`/`novis` by whether a
live crew was in the imposter's **rendered view** (`player_visible_interval`; note this
is a viewport basis — the policy's own belief-level vision can be narrower). Per-tick
derived columns: `near_crew` (px to nearest live crew), `closing`, `speed`, `parked`
(net displacement < 40px over the trailing 120 ticks — the recon-stall signature),
`crew_room_ct`.

## Tools

```sh
# cross-policy scoreboard: one row per policy (per-game medians) — handoff quality,
# window conversion, blind-search behavior, cooldown positioning, room churn
uv run --with duckdb --with pandas --with numpy python compare_policies.py \
    WH [WH2 ...] [--csv out.csv] [--per-game games.csv]

# trajectory scenes: the N worst blind ready-windows for a policy, map + path
# (dark→bright over time) + crew paths + a nearest-crew distance strip per scene
uv run --with duckdb --with pandas --with numpy --with matplotlib python render_hunt.py \
    WH [WH2 ...] --policy crewborg --top 6 -o /tmp/worst.png
# ... or one specific window: --episode <id> --slot <n> --window <k>

# occupancy heat: imposter blind-ready positions vs live-crew positions (same ticks),
# side-by-side per policy + a Bhattacharyya overlap scalar
uv run --with duckdb --with pandas --with numpy --with matplotlib python heat_compare.py \
    WH [WH2 ...] --policies crewborg notsus relhalpha -o /tmp/heat.png
```

Related: `../positioning_viz/` renders single kill-ready *moments* (past/future paths
around one event, interactive server + PNG). This directory is the *window/cross-policy*
layer on top of the same warehouse data.
