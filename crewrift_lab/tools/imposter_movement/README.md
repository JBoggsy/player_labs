# Imposter movement lab — see how imposters hunt, spatially, over time

Tools to inspect and compare **how imposters move while trying to find victims**:
where our imposter goes when it's kill-ready and blind, where the top imposters go,
and where the crew actually are. Built 2026-07-02 to answer "why can't crewborg's
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

## Findings snapshot (2026-07-02, crewrift_prime 0.4.31 data)

Measured over `/tmp/prime_wh` (48 tournament eps), the ~200-ep ghost-A/B warehouses,
and 25 pinned-imposter killtrace probes (belief telemetry cross-checked):

- **Handoff is fine.** Median nearest-crew at the ready moment: crewborg ≈18px, 84% of
  windows start within 60px — as good as any top imposter. Cooldown positioning is
  best-in-field (same-room-with-crew ~85-95%).
- **Point-blank conversion leaks.** Windows starting within 60px convert 70-77% for the
  crewborg family vs 88-92% for notsus/relhalpha/daveey (witness-gate waits + ~7t
  strike latency vs their ~1t).
- **Blind recovery is catastrophic (the real deficit).** Windows starting >150px from
  crew last a median **519 ticks** for crewborg vs 91-218 for the field. Failure modes,
  both from the mode-gate design (`rule_based.py` routes ready+no-visible-victim to
  Recon *whenever any crew was ever seen*, so Search's room-checking FSM never runs
  while ready; `recon.py` beelines to `most_recent_victim`'s last-seen point with **no
  staleness bound, no arrival fallback, no timeout**):
    1. *Stale-point park*: walk to a minutes-old last-seen position and stand there
       (one killtrace game: parked 98.5% of an 8,452-tick ready window, nearest crew
       500px away; killtrace median parked share of blind ready ticks 87%).
    2. *Glimpse-chase circuit*: with players around, each belief-glimpse retargets the
       beeline → giant repeated map circuits that pass within ~20px of sitting crew
       through walls without ever entering the room to check (see the triple-pass-by
       exhibit) — near-misses a room-sweep would convert.
- **Coverage is NOT the problem.** crewborg's blind-search heat overlaps crew density
  *more* than anyone (0.48 vs notsus 0.26) — it goes everywhere; it just never
  checks rooms or persists near contacts while ready.
