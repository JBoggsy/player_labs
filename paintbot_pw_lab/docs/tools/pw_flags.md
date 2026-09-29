# pw_flags.py: tick-linked anomaly flags (T12)

Rule-based flags that point a human or agent at moments worth watching. Each flag is one
row linked to ticks. Every threshold is a named constant at the top of the file and is
printed with the output. Source: `tools/pw_flags.py`.

## Commands

```bash
uv run python paintbot_pw_lab/tools/pw_flags.py ROOT [ROOT ...] [--policy KEY_OR_NAME] \
    [--flags stuck,death_alone,...] [--top N] [--csv FILE] [--vis-every M] [--tag coworld-vX.Y.Z]
```

- The first line is the thresholds. Then come flag counts, then up to `--top` rows per
  episode. `--top 0` prints only each episode's counts per flag (no row tables).
- `--policy` narrows the flags to that policy's seats and to team flags on its team. It
  also prints the policy's **losses and draws, worst Elo outcome first**, with its flag
  counts per episode. That is the triage order for diagnosis: review the worst loss first.
- `--vis-every M` fills `enemies_seeing` on `death_alone`, and re-traces.
- Exit 1 if any episode failed to load; exit 2 for an unknown `--flags` name, an unknown
  `--policy` (the valid keys and names are listed) or a negative `--top`.

```python
import pw_flags as pf
pf.episode_flags(ep)              # DataFrame: episode_id, flag, seat, team, policy_key, t_start, t_end, evidence, detail
pf.losses(batch, policy, flags)   # the policy's non-wins, worst Elo outcome first
```

`detail` is a JSON string. `seat` is null for team flags (`heart_lost_with_allies`,
`zero_glory_win`), and `team` is then the team the flag is about.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py flags ROOT... --json` (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | roots; `--policy`, `--flags a,b` (names from the Flags table), `--top N` (0 = counts only), `--csv FILE`, `--vis-every M`, `--tag` |
| Outputs | `--csv FILE`: every flag row |
| `--json` result | `{thresholds, flag_counts, rows_total, losses: [the policy's non-wins, worst Elo outcome first] or null, rows: [at most --top per episode], rows_note}` |
| Exit codes | 0 ok; 1 some episodes failed to load or verify (the rest are used; one `failures[]` entry each, `counts.failed_by_code`); 2 usage error: bad arguments, roots with no episode, or an unknown selector (`--policy`, `--flags`, a negative `--top`; `result.valid` lists the valid values); 3 `pw_trace` not built (`next[0]` = `paintbot_pw_lab/tools/build_tools.sh`) |
| Idempotence / cache | reads the `pw_episodes` caches; same output on rerun |
| Typical next step | `uv run python paintbot_pw_lab/tools/pw.py report <worst loss> --json`, then `viz movement` around a flag's `t_start` |

## Flags

| Flag | Rule (defaults) | Evidence |
| --- | --- | --- |
| `stuck` | Alive and walking (`cmd_walk`) with an unchanged walk goal ≥ 200 away, having moved < 200 units over ≥ 72 ticks. Overlapping windows merge. | sampled |
| `oscillating` | The walk goal flips back to within 100 units of where it was two changes earlier, the middle goal being ≥ 300 away, ≥ 3 times within 144 ticks | sampled |
| `idle_alive` | Alive at two consecutive samples with the engine's empty `Command()` for ≥ 48 ticks | sampled |
| `vm_disabled_suspect` | Empty commands from some tick to the end while alive, for ≥ `pw_metrics.VM_DISABLED_MIN_IDLE_TICKS` (240). It is exact (`evidence: exact`) when our seat log has `BASIC error:`. | inferred / exact |
| `death_alone` | Killed with no living teammate within 1,000 units, using the last sample before death. `enemies_seeing` comes from the last visibility sample, or is null without `--vis-every`. | sampled |
| `heart_lost_with_allies` | A heart the team owned is captured while ≥ 1 living teammate is within 700 units | exact capture, sampled positions |
| `wasted_grenade` | A grenade blast that damaged no enemy | exact |
| `friendly_fire` | Damage to a teammate. One attacker's hits within 48 ticks merge into one flag, with HP, kills and weapons. | exact |
| `long_wade` | ≥ 72 ticks in water in one stretch. A stretch ends by leaving the water, dying, or the match ending (`ended`). | exact |
| `zero_glory_win` | The winner's final glory is 0. The ladder scores that as a draw (0.5). | exact |

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

## Limits

- All thresholds are uncalibrated defaults from the plan. `death_alone` fires on most
  deaths at the 1,000-unit radius, because cogs spread out and the gun is long range.
  Raise the radius, or require `enemies_seeing > 0`, before using it as a behavior metric.
- Sampled flags are accurate only to one `state_every` interval (6 ticks by default).
  `oscillating` can miss goal flips faster than the sampling.
- `vm_disabled_suspect` for other policies is a heuristic. A cog that holds still on
  purpose with an empty command looks the same.
- Not built: "died in enemy vision" as a hard filter, and "heart lost within reach" by
  traversable path. Both use straight-line distance.
