# pw_fights.py: engagements, trades, opening duels

Answers "do we win the fights we take, who shoots first, and who wins the opening duel at
each heart?". It groups combat from the hash-checked [tables](tables.md) into engagements,
trades and opening duels, and reports who wins them per policy (the unit A/B and the miner
use). It reads the tables only, never the tape. Source: `tools/pw_fights.py`. Index of all
tools: [README.md](README.md).

## Commands

```bash
uv run python paintbot_pw_lab/tools/pw_fights.py ROOT [ROOT ...] [--policy KEY_OR_NAME] [--list] \
    [--csv DIR] [--vis-every M] [--tag coworld-vX.Y.Z]
```

The output starts with the thresholds line. Then, per episode, it prints the number of
engagements, contests and trades, and one line per policy: engagements won, first hits,
outnumbered fights, opening duels and trades. `--list` also prints every engagement and
contest. `--csv` writes `engagements.csv`, `opening_duels.csv`, `trades.csv` and
`fight_policy.csv`. `--vis-every M` traces with visibility sampling, which fills the
"saw first" columns. That trace is its own cache variant (`pw_cache@se6-ve<M>/`, or
`NAME@se6-ve<M>.pw_cache/` beside a local replay; see
[pw_episodes.md](pw_episodes.md#cache-variants)): the first run traces, later runs with the
same `M` reuse it, and the default cache other tools read is untouched. The tool exits 1 if
any episode failed to load. `--csv` writes nothing when no episode loaded.

```python
import pw_fights as pf
pf.engagements(ep)            # one row per engagement
pf.opening_duels(ep)          # one row per heart contest (capture attempt)
pf.trade_events(ep["kills"])  # one row per traded death
pf.fight_policy_metrics(ep)   # one row per (episode, policy_key): the A/B and miner unit
```

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py fights ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | roots; `--policy`, `--list`, `--csv DIR`, `--vis-every M` (re-traces), `--tag` |
| Outputs | `--csv DIR`: `engagements.csv`, `opening_duels.csv`, `trades.csv`, `fight_policy.csv` |
| `--json` result | `{thresholds, fight_policy: [rows per (episode, policy)], engagements, opening_duels, trades (counts), rows: note}`; engagement rows only through `--csv` |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments, roots with no episode, or an unknown selector (`--policy`; `result.valid` lists the valid values); 3 `pw_trace` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`) |
| Idempotence / cache | reads the `pw_episodes` caches; `--vis-every M` traces once into its own cache variant and reuses it after |
| Typical next step | `flags` or `report` on the episodes where we lose fights; `miner` for the batch |

## Definitions

| Output | Definition | Evidence |
| --- | --- | --- |
| engagement | Enemy damage events (not friendly, not self, attacker known) are single-linked. Two events join when they are ≤ `ENGAGEMENT_JOIN_TICKS` (48) apart and they share a seat or have participants ≤ `ENGAGEMENT_JOIN_DISTANCE` (1,500 units) apart. A kill is a damage event with `killed`. | exact events, chosen grouping |
| `n_0`, `n_1`, `seats_0/1` | Distinct attackers and victims per team | exact |
| `first_hit_team` | The team of the first event. If both teams hit on that tick, it is -2 (draw). | exact |
| `winner` | More kills, then more enemy HP removed, else -2 | exact |
| `saw_first_team`, `first_sight_t`, `sight_to_hit_ticks` | Each team's streak of seeing an opposing participant, counted back from the first hit over sampled `visibility` (at most `SIGHTING_LOOKBACK_TICKS`, 240). The earlier streak saw first. When both streaks run the whole lookback, the result is -2 and the tick is null. Without `--vis-every` every value is null. | sampled |
| `hearts`, `heart_events` | Capture events (start, complete, reset, contest) at a heart ≤ `HEART_AFFECT_RADIUS` (800) from any participant, from the engagement start to `HEART_AFFECT_AFTER_TICKS` (120) after it ends | exact events, chosen radius |
| trade | An enemy kills our seat, and our team kills that killer within `TRADE_WINDOW_TICKS` (72, shared with `pw_metrics.trades`) | exact |
| heart contest | One capture attempt: a `capture_start`, ending at the next capture event at that heart (complete, reset, or the other team starting) or at the match end. The attacker wins if the attempt completed, else the other team wins. | exact |
| opening duel | The first enemy kill whose victim is ≤ `OPENING_DUEL_RADIUS` (1,000) from the heart, from `OPENING_DUEL_LEAD_TICKS` (48) before the attempt to its end. `opening_team_won` says whether that team won the contest. | exact events, chosen radius |

CSV columns (the `--csv` files; `--list` prints the first two):

- `engagements.csv`: `episode_id, engagement, t_start, t_end, duration_ticks, events, x, z`
  (mean position of the events), `seats_0, seats_1, n_0, n_1, first_hit_t, first_hit_seat`
  (null when several seats hit on the first tick), `first_hit_team, kills_0, kills_1, hp_0,
  hp_1, winner, first_sight_t, saw_first_team, sight_to_hit_ticks, vision_sampled, hearts,
  heart_events` (JSON).
- `opening_duels.csv`: `episode_id, heart, t_start, t_end, attacker, owner_before, end_kind`
  (`capture_complete`, `capture_reset`, `capture_start` by the other team, or `match_end`),
  `opening_t, opening_killer, opening_victim, opening_team, contest_winner, opening_team_won`.
- `trades.csv`: `t_death, victim, victim_team, killer, t_trade, avenger, trade_ticks, episode_id`.
- `fight_policy.csv`: `episode_id, policy_key, policy_name, team` plus the metrics below.

`fight_policy_metrics` columns: `engagements`, `engagements_won`, `engagements_drawn`,
`engagements_first_hit`, `won_when_first_hit`, `engagements_outnumbered`,
`won_when_outnumbered`, `engagements_outnumbering`, `engagements_saw_first` (null without
visibility), `sight_to_hit_ticks_median`, `opening_duels`, `opening_duels_won`,
`contests_won_after_opening_win`, `trade_kills`, `deaths_traded` (descriptions:
`FIGHT_METRICS`). A policy that plays on both teams (a mirror match) gets only
`engagements` and the trade counts.

## Verified (2026-09-29, build coworld-v0.3.78)

- Ran on the 3 rules-44 samples and 12 public rules-48 league episodes (round 2373).
- Every enemy damage event falls in exactly one engagement.
- Policy trade counts equal `pw_metrics.trades`.
- Ran with `--vis-every 12` on one episode.
- Tests: `tools/tests/test_pw_fights_flags_scout.py`.

## Limits and calibration notes

- **The engine's "contested" state almost never happens.** It requires both teams within
  140 units of a heart. There were 0 contest events in 15 episodes, because the gun reaches
  5,250 units. That is why a contest here is a capture attempt.
- **Long-range shooting chains engagements.** With the 1,500-unit join, the opening
  minute of a match is often one engagement of 700+ ticks with all 16 cogs. One episode
  had 2 engagements lasting 1,181 and 1,357 ticks. Revisit the join thresholds after a
  larger batch, or read `n_0`/`n_1` and the duration before trusting a "won" rate.
- **"Saw first" is coarse.** Vision is an unlimited-range cone, so in the sample most
  engagements were -2: both teams saw each other in the same sample or for the whole
  lookback. The resolution is the `--vis-every` interval.
- The winner rule (kills, then HP) ignores armor and position. Heart impact is by distance,
  not causation.
