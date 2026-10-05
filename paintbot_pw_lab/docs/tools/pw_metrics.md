# pw_metrics.py: the metric library

Every number the lab quotes about a match (result, Elo outcome score, glory composition,
combat, hearts, supplies, idle time) has exactly one definition here, computed from the
[tables](tables.md) at seat, policy and team level. A/B, mining, flags and reports all reuse
it. Source: `tools/pw_metrics.py`; the full catalog with units, definitions and evidence kind
is the `METRICS` dict in that file. Part of the lab tool set: [tool index](README.md)
(`pw.py metrics`).

## Commands

```bash
uv run python paintbot_pw_lab/tools/pw_metrics.py ROOT [ROOT ...] [--policy KEY_OR_NAME] [--csv DIR] [--tag TAG] [--json]
uv run python paintbot_pw_lab/tools/pw_metrics.py paintbot_pw_lab/episode_data/20260928T214433_* --json
```

Prints, per episode: each team's result, glory, Elo outcome score and glory composition
(start − countdown + each award kind − settled), meter, hearts, captures, K/D, accuracy,
trades, cogs out and longest supply gap; then one line per policy (only the `--policy` one
when given). `--csv` writes
`seat_metrics.csv`, `policy_metrics.csv`, `team_metrics.csv`. Exit 1 if any episode failed
to load (failures are printed).

```python
seats = pm.seat_metrics(ep)          # (episode, seat)
policies = pm.policy_metrics(ep)     # (episode, policy_key): the unit for A/B and mining
teams = pm.team_metrics(ep)          # (episode, team)
```

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py metrics ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | roots as for `episodes`; `--policy KEY_OR_NAME`, `--csv DIR`, `--tag` |
| Outputs | nothing by default; `--csv DIR` writes `seat_metrics.csv`, `policy_metrics.csv`, `team_metrics.csv` (overwritten on rerun) |
| `--json` result | `{team: [rows], policy: [rows], seat_metrics: note}`: every column of `team_metrics` / `policy_metrics` (`policy` filtered by `--policy`); seat rows only through `--csv`. NaN is `null` |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments, roots with no episode, or an unknown selector (`--policy`; `result.valid` lists the valid values); 3 `pw_trace` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`) |
| Idempotence / cache | reads the `pw_episodes` caches; pure computation, same output on rerun |
| Typical next step | `uv run python paintbot_pw_lab/tools/pw.py flags ROOT --policy KEY --top 0 --json` for triage, or `report` on one episode |

## Levels and rules

- Policy and team rows **sum numerators and denominators** across seats and recompute
  ratios; they never average per-seat ratios.
- A policy on both teams in one episode (mirror match) has `team`, `result` and
  `elo_outcome` null.
- Null when the input is missing: `gun_accuracy` with 0 shots, `kd` with 0 deaths,
  `vm_errors`/`intent_lines` without a seat log, glory kinds before rules 37.
- `team_metrics` raises on two identities: initial + awards − countdown = unsettled glory,
  and heart-ticks = meter ticks (except a winner whose meter elimination filled).

## Headline definitions

| Metric | Definition | Kind |
| --- | --- | --- |
| `elo_outcome` | the **Elo outcome score**: `clamp(0.5 + (our glory − their glory) / 2000, 0, 1)` (ladder `margin_scale` 1000, [mechanics.md §1](../mechanics.md)) | exact |
| `glory_<kind>` | deduped awards: quiet_supplies, friendly_fire, glory_heart, behind_lives, behind_cogs | exact |
| `gun_accuracy`, `gun_enemy_accuracy` | hits / rays fired | exact |
| `gun_acc_band_<lo>_<hi>` | enemy hits at exact distance + misses at the aim-line target's distance, bands 0-1000-3500-5250 | inferred |
| `shots_inferred_blocked` | misses whose ray reached a shielded / just-dead cog or passed a trench cog | inferred |
| `dealt_hp_enemy[_weapon]`, `dealt_armor_enemy`, `taken_hp`, `taken_armor` | from damage events | exact |
| `kills`, `deaths`, `kd`, `trade_kills`, `deaths_traded` | trade window `TRADE_WINDOW_TICKS` = 72 | exact |
| `alive_share`, `heart_reach_share`, `*_territory_share` | per-tick counters from the trace | exact |
| `captures_completed`, `capture_starts`, `capture_resets`, `first_capture_tick`, `heart_ticks`, `hearts_held_mean` | from capture events | exact |
| `contests` | `contest_start` events (both teams in reach of one heart), including those that begin with no capture in progress; a contest involves both teams, so both team rows carry the same count. Rare in the league (12 contests in 9 of 80 0.3.79 episodes) | exact |
| `lead_changes` | sign changes of the meter difference across state samples | sampled |
| `pickups_<kind>`, `longest_supply_gap_ticks` | pickup events | exact |
| `shouts`, `shout_bytes`, `shouts_heard_by_enemy` | shouts + earshot recompute | exact |
| `idle_share` | empty-command decision ticks / decision ticks | exact |
| `stuck_ticks` | sampled: < 10 units per sample toward an unchanged goal ≥ 200 away | sampled |
| `vm_disabled_suspect` | empty commands for the last ≥ 240 alive ticks | inferred |
| `vm_errors` | `BASIC error:` lines in our seat log | exact (our seats only) |

All thresholds are named constants at the top of the file (`TRADE_WINDOW_TICKS`,
`DISTANCE_BANDS`, `STUCK_*`, `VM_DISABLED_MIN_IDLE_TICKS`, `ELO_MARGIN_SCALE`).

## Thresholds (calibrated 2026-09-30)

Data: the 80 hash-verified main-league episodes at coworld-v0.3.79 in
`episode_data/audit-2026-09-29/` (12,961 enemy gun hits, 22,198 misses, 1,280 seat-episodes), default cache.

| Constant | Old → new | Evidence and rule | Effect on the sample |
| --- | --- | --- | --- |
| `DISTANCE_BANDS` | 0-750-1500-2500-5250 → **0-1000-3500-5250** | Enemy gun accuracy (hits / (hits + aim-targeted misses)) in 500-unit bins: 0.53 and 0.49 under 1,000, flat 0.45-0.47 from 1,000 to 3,500, then 0.39, 0.35, 0.34 and 0.35 beyond 3,500. The old last band held 76% of shots and crossed the drop at 3,500. The new bands split where accuracy changes. **Renames the band columns** (`gun_shots_band_*`, `gun_acc_band_*`); `features.long_range_shot_share` now reads `3500_5250`. | shots / accuracy: 1,096 / 0.50; 14,810 / 0.46; 15,829 / 0.36 |
| `STUCK_MAX_DISPLACEMENT` | 30 → **10** units per 6-tick sample | Steps of walkers with a far, unchanged goal (105,523): 9,823 are exactly 0, then ~95 per unit from 2 to 12, then peaks from legitimate slow movement (12-14, 30-32, 36-38 and 42-44 = water, 7 units/tick). 30 also counted those slow movers. Under 10, 92% of the steps are exactly 0. | stuck_ticks 88,307 → 63,854; seats with any 969 → 641 of 1,280 |
| `STUCK_MIN_GOAL_DISTANCE` | 200 (kept) | The same break as `pw_flags` (arrived < 50, blocked behind a wall 250-350). | |
| `TRADE_WINDOW_TICKS` | 72 (kept) | Killer-vs-teammate death hazard. Evidence in [pw_fights.md](pw_fights.md#thresholds-calibrated-2026-09-30). | 758 trades of 3,828 enemy kills |
| `VM_DISABLED_MIN_IDLE_TICKS` | 240 (kept) | The league data cannot calibrate it: no league seat ever sent an empty command (`idle_ticks` 0 everywhere). | 0 suspects |
| `pw_trace` `AimTolerance` (feeds `aim_target`, `shots_untargeted`, band shots) | 150 → **110** | For enemy hits whose `aim_target` is the victim, the offset across the aim line is p99 82, p99.9 107, max 134; wrongly inferred targets sit at a median of 91; targeted misses spread evenly over 0-150. Applied and re-traced 2026-09-30: `aim_target` now matches the victim on 12,149 of 12,961 enemy hits (93.7%, was 91.6%), and misses tagged with a guessed target fell from 18,818 to 14,958. |

## Verified (2026-09-29)

Re-run on build `coworld-v0.3.79`: the 3 samples (`--json`, exit 0) and 8 local recordings
with `--policy base.bas --csv DIR` (the three CSVs written and listed in `outputs[]`); an
unknown `--policy` exits 2 with `result.valid`; every metric named in the table above is a
`METRICS` key and an output column.

Earlier (0.3.78) it ran on 8 episodes (3 league samples, 3 local, 2 hosted 0.3.78): both identities held on all
16 team rows; policy kills sum to team kills; shots and hits sum to the `shots` table. Tests:
`paintbot_pw_lab/tools/tests/test_pw_metrics.py` (Elo outcome, trade rule, heart-tick
accounting, summed ratios and mirror policies, a sample episode end to end).

## Not yet covered

- Budget headroom (instructions and work units per decision). BASIC cannot read its own
  instruction count, so no policy line (the PWI intent line included) can report it. Measure
  it with `PW_BASIC_PEAKS=1` on a local `paintbot-headless` run, which prints per-seat peaks
  ([evidence-pipeline.md](../evidence-pipeline.md), [policy-surface.md](../policy-surface.md)).
- Win-probability credit ([pw_winprob.md](pw_winprob.md)) and engagement segmentation ([pw_fights.md](pw_fights.md)).
- Spray and grenade effectiveness count bursts/blasts with at least one enemy victim; they
  do not attribute a miss to a target.

Rules49 damage breakdowns include `self_destruct`; pickup counters include `mister`,
`sniper`, and `radar`. Grenade throw-efficiency metrics exclude self-destruct. Aim-line
distance bands remain uncalibrated under the new gun spread; use them descriptively.
