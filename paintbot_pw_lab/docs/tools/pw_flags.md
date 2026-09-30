# pw_flags.py: tick-linked anomaly flags

Answers "what went wrong in our worst losses, and at which tick?". Rule-based flags (stuck,
idle, dead VM, died alone, heart lost with allies near, wasted grenade, friendly fire, ...)
point a human or agent at moments worth watching, and `--policy` lists that policy's losses
worst first. Each flag is one row linked to ticks. Every threshold is a named constant at the
top of the file and is printed with the output. Source: `tools/pw_flags.py`. Index of all
tools: [README.md](README.md).

## Commands

```bash
uv run python paintbot_pw_lab/tools/pw_flags.py ROOT [ROOT ...] [--policy KEY_OR_NAME] \
    [--flags stuck,death_alone,...] [--top N] [--csv FILE] [--vis-every M] [--tag coworld-vX.Y.Z]
```

- The first line is the thresholds. Then come flag counts, then up to `--top` rows per
  episode. `--top 0` prints only each episode's counts per flag (no row tables).
- `--policy` narrows the flags to that policy's seats and to team flags on its team. It
  also prints the policy's **losses and draws, worst Elo outcome score first**, with its flag
  counts per episode. That is the triage order for diagnosis: review the worst loss first.
- `--vis-every M` fills `enemies_seeing` on `death_alone`. It traces once into its own cache
  variant (see [pw_episodes.md](pw_episodes.md#cache-variants)); the default cache is untouched.
- `--csv FILE` writes every flag row of the loaded episodes, filtered by `--flags` but not
  by `--policy` or `--top`.
- Exit 1 if any episode failed to load; exit 2 for an unknown `--flags` name, an unknown
  `--policy` (the valid keys and names are listed) or a negative `--top`.

```python
import pw_flags as pf
pf.episode_flags(ep)              # DataFrame: episode_id, flag, seat, team, policy_key, t_start, t_end, evidence, detail
pf.losses(batch, policy, flags)   # the policy's non-wins, worst Elo outcome score first
```

`detail` is a JSON string. `seat` is null for team flags (`heart_lost_with_allies`,
`zero_glory_win`), and `team` is then the team the flag is about. `detail` keys per flag:
`stuck` {pos, goal, goal_distance}; `oscillating` {flips}; `idle_alive` {ticks};
`vm_disabled_suspect` {final_idle_run_ticks} (inferred) or {log} (exact); `death_alone`
{killer, weapon, nearest_teammate, enemies_seeing}; `heart_lost_with_allies` {heart,
captured_by, allies_near, nearest}; `wasted_grenade` {pos, friendly_victims};
`friendly_fire` {victims, hp, kills, weapons}; `long_wade` {ticks, ended: left|died|match_end};
`zero_glory_win` {winner}.

`losses` columns (and `result.losses` rows): `episode_id, result, elo_outcome, glory_ours,
glory_theirs, opponent, ticks, flags` (the policy's flag total) plus one count column per flag
that fired (null where it did not).

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py flags ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | roots; `--policy`, `--flags a,b` (names from the Flags table), `--top N` (0 = counts only), `--csv FILE`, `--vis-every M`, `--tag` |
| Outputs | `--csv FILE`: every flag row |
| `--json` result | `{thresholds, flag_counts, rows_total, losses: [the policy's non-wins, worst Elo outcome score first] or null, rows: [at most --top per episode], rows_note}` |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments, roots with no episode, or an unknown selector (`--policy`, `--flags`, a negative `--top`; `result.valid` lists the valid values); 3 `pw_trace` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`) |
| Idempotence / cache | reads the `pw_episodes` caches (`--vis-every M`: its own cache variant); same output on rerun |
| Typical next step | `uv run python paintbot_pw_lab/tools/pw.py report <worst loss> --json`, then `viz movement` around a flag's `t_start` |

## Flags

| Flag | Rule (defaults) | Evidence |
| --- | --- | --- |
| `stuck` | Alive and walking (`cmd_walk`) with an unchanged walk goal ≥ 200 away, having moved < 200 units over ≥ 48 ticks. Overlapping windows merge. | sampled |
| `oscillating` | The walk goal flips back to within 100 units of where it was two changes earlier, the middle goal being ≥ 500 away, ≥ 3 times within 144 ticks | sampled |
| `idle_alive` | Alive at two consecutive samples with the engine's empty `Command()` for ≥ 48 ticks | sampled |
| `vm_disabled_suspect` | Empty commands from some tick to the end while alive, for ≥ `pw_metrics.VM_DISABLED_MIN_IDLE_TICKS` (240). A second, exact row (`evidence: exact`) is added for each `BASIC error:` line in a seat log (`policy_log.line_kind = vm_error`; seat logs exist only for our local `pw_intent record` episodes or downloaded hosted logs). | inferred / exact |
| `death_alone` | Killed with no living teammate within 1,280 units (the speech radius), using the last sample before death. `enemies_seeing` comes from the last visibility sample, or is null without `--vis-every`. | sampled |
| `heart_lost_with_allies` | A heart the team owned is captured while ≥ 1 living teammate is within 2,156 units (capture reach 140 + one 72-tick capture time of walking at 28 units/tick) | exact capture, sampled positions |
| `wasted_grenade` | A grenade blast that damaged no enemy | exact |
| `friendly_fire` | Damage to a teammate. One attacker's hits within 72 ticks merge into one flag, with HP, kills and weapons. | exact |
| `long_wade` | ≥ 96 ticks in water in one stretch. A stretch ends by leaving the water, dying, or the match ending (`ended`). | exact |
| `zero_glory_win` | The winner's final glory is 0. The ladder scores that as a draw (0.5). | exact |

## Thresholds (calibrated 2026-09-30)

Data: the 80 hash-verified main-league episodes at coworld-v0.3.79 in
`episode_data/audit-2026-09-29/` (1,280 seat-episodes, 4,187 deaths, 170,177 ticks), default
cache (`state_every` 6); `enemies_seeing` from a `--vis-every 12` variant. Engine constants
from [mechanics.md](../mechanics.md). Flag counts are over all 16 seats of the 80 episodes.

| Constant | Old → new | Evidence and rule | Flags (80 episodes) |
| --- | --- | --- | --- |
| `FLAG_STUCK_WINDOW_TICKS` | 72 → **48** | Runs of zero movement while walking to a far, unchanged goal: their density per tick falls ~7x from 6 to 48 ticks (short body blocks and sidesteps), then stays flat to 120. The break is at 48. | stuck 332 → 542 (374 seat-episodes, 78 episodes) |
| `FLAG_STUCK_MAX_DISPLACEMENT` | 200 (kept) | Max excursion over 72-tick walking windows: 28% of windows are exactly 0, then a flat trough from 10 to 400 (~20 windows per 10 units), then free walking near 2,000 (28 units/tick). 92% of windows under 200 are exactly 0, so any value in the trough gives the same flags. | |
| `FLAG_STUCK_MIN_GOAL_DISTANCE` | 200 (kept) | Goal distance of non-moving walkers: arrived (< 50, 7,324 samples) and blocked behind a wall (250-350, 7,296). 200-250 is the density minimum (132). | |
| `FLAG_OSCILLATION_MIN_JUMP` | 300 → **500** | Middle-goal jump among A→B→A returns: ~1,075 per 100 units at 300-500, ~250 per 100 units from 500 to 2,000. Below 500 it is goal jitter (goals change every 6-tick sample at the median). | oscillating 1,102 → 862 (547 seat-episodes) |
| `FLAG_OSCILLATION_GOAL_MATCH`, `_WINDOW_TICKS`, `_MIN_FLIPS` | 100, 144, 3 (kept) | No break in the return-distance or inter-flip-gap distributions. The flag concentrates on two policies (650 of the 1,102 old flags), so it separates policies. | |
| `FLAG_IDLE_MIN_TICKS`, `VM_DISABLED_MIN_IDLE_TICKS` | 48, 240 (kept) | The league data cannot calibrate them: `seats.idle_ticks` is 0 on all 1,280 league seat-episodes (1.93 M decision ticks) and `final_idle_run_ticks` is 0 everywhere. | idle_alive 0, vm_disabled_suspect 0 |
| `FLAG_ALONE_RADIUS` | 1,000 → **1,280** | Nearest living teammate at death vs. at alive samples (every 24 ticks): the death/alive ratio is < 1 below ~1,200 and 1.15-1.35 from 1,300 out. Being farther than ~1,300 from every teammate is where isolation starts to predict death, and it matches the speech radius (1,280). Isolation is a weak signal here (relative risk ~1.25); with `--vis-every 12`, 14% of the old flags had no enemy seeing the victim. | death_alone 2,084 → 1,742 (42% of deaths; 31% of alive samples are that isolated) |
| `FLAG_HEART_DEFENSE_RADIUS` | 700 → **2,156** | Engine rule: a defender within capture reach (140) pauses a capture, which takes 72 ticks. A teammate within 140 + 72 × 28 could have walked into reach during the capture. The nearest living defender at the 136 owned-heart flips has a median of 2,690 and no break; 700 fired on 6 (4%). | heart_lost_with_allies 6 → 37 (27% of owned-heart flips, 26 episodes) |
| `FLAG_FF_MERGE_TICKS` | 48 → **72** | Gaps between one attacker's friendly hits (376 hits): a spike at 24-36 (gun cooldown), 1.0 per tick at 48-72, then ~0.5 per tick background. 72 is the armored/trench gun cooldown. | friendly_fire 918 → 900 |
| `FLAG_LONG_WADE_TICKS` | 72 → **96** | The durations of 1,356 water stretches decay smoothly, with no break. Rule from the engine: water is quarter speed, so 96 ticks of wading cost 72 ticks (one respawn delay) against land. Stretches of 48-240 ticks are 80-85% within 400 of a heart (lake-heart play), and half of them end in death. | long_wade 432 → 346 (25% of stretches) |
| `wasted_grenade`, `zero_glory_win` | no threshold | | wasted_grenade 253; zero_glory_win 0 |

## Verified (2026-09-29, build coworld-v0.3.78)

- Ran on the 3 rules-44 samples and 12 public rules-48 league episodes. On those 12 (all
  seats): death_alone 283 (of 596 deaths), oscillating 168, friendly_fire 147,
  long_wade 46, stuck 37, wasted_grenade 29, and no heart_lost_with_allies, idle_alive, vm_disabled_suspect or
  zero_glory_win.
- Spot-checked one `stuck` flag against the states: a seat was walking toward (3200, 1250)
  and did not move from (767, 964) for 66 ticks.
- The sampled idle rule agrees with the exact `seats.idle_ticks` counter. An earlier
  version counted the empty commands of seats that died between samples; that bug is fixed
  and pinned by a test.
- `--vis-every 12` fills `enemies_seeing`.
- `--policy` loss ordering ran, but only on policies without losses in this sample
  (`aaron-coplay-coach`). The worst-first sort itself is a plain sort on `elo_outcome`.
  Re-checked 2026-09-29 at coworld-v0.3.79 on 3 local `base.bas` vs `jev.bas` recordings
  (`--policy jev.bas`): losses listed worst first (0.2305, 0.266), `--flags bogus` and
  `--top -1` exit 2.

## Limits

- Thresholds were calibrated on one league sample (see Thresholds). The idle and dead-VM
  thresholds are still plan defaults, because no league seat ever sent an empty command.
  `death_alone` still fires on 42% of deaths: cogs spread out and the gun is long range,
  so isolation raises death risk only about 1.25x. Read it as a rate to compare between policies,
  not as a per-death verdict.
- Sampled flags are accurate only to one `state_every` interval (6 ticks by default).
  `oscillating` can miss goal flips faster than the sampling.
- `vm_disabled_suspect` for other policies is a heuristic. A cog that holds still on
  purpose with an empty command looks the same.
- Not built: "died in enemy vision" as a hard filter, and "heart lost within reach" by
  traversable path. Both use straight-line distance.
