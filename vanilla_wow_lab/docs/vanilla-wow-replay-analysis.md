# Vanilla WoW replay analysis

Retained `CWREPLAY` files are sufficient for stateful, post-hoc gameplay analysis now. The
canonical `coworld-vanilla-wow` owner repo ships `player.sdk.replay_diagnostics`, which replays
the recorded wire through the real client reducer. The lab consumes that supported reducer;
it does not maintain a parallel packet-state implementation.

## Batch profiler

Run the lab wrapper on one replay, an episode directory containing `replay.json`, or a batch
directory containing multiple episode directories:

```bash
uv run python vanilla_wow_lab/tools/wow_batch_profiler.py \
  vanilla_wow_lab/episode_data/MY_BATCH \
  --json-out /tmp/wowborg-profile.json
```

The owner repo defaults to `~/coding/coworlds/coworld-vanilla-wow`. Override it with
`--owner-repo PATH` or `VANILLA_WOW_OWNER_REPO`. The checkout must contain
`observe/inspect_party_wire_replay.nim`; the project dependency supplies the typed Python API,
while the owner checkout supplies the canonical reducer source omitted from the installed
package.

The text output is a fast triage view. The JSON sidecar retains row-level evidence for maps,
plots, joins, and comparisons.

## Available evidence

| Domain | Metrics available immediately |
| --- | --- |
| Progress | path distance, displacement, maximum excursion, efficiency, XP and level deltas |
| Stalls | longest stationary interval; clustered stuck episodes; raw Stuck invocations, outcomes, durations, and coordinates |
| Life | death times and coordinates; alive, dead, ghost, and unknown seconds; terminal life state |
| Recovery | release-spirit, corpse-reclaim, resurrection-response, and spirit-healer controls and confirmations |
| Combat | combat duration; incoming/outgoing damage and event counts; attack packets; damage-source name, entry, GUID, and location |
| Spells | requested spell IDs, starts, effects, failures, and failure codes |
| Forms and auras | requested Druid forms by name; start/end aura IDs; form/aura evidence at significant intervals |
| Control | meaningful client controls, movement/action counts, and control gaps in the underlying diagnostic report |

For movement-continuity work, download the whole experience-request episode so the directory
contains both `replay.json` and `game_logs.log`, then run:

```bash
uv run python vanilla_wow_lab/tools/movement_report.py EPISODE_DIR --json
```

On `vanilla-wow:0.1.208` and later, that joins the outbound movement wire to structured
environment-host telemetry. It separates active nonterminal stop/restarts from death/ghost
transitions and final scoring/logout artifacts; reports host stalls, rejected requests, and detached frames; counts direct turn
reversals and turns lasting at most 100 ms; and detects the former same-waypoint route-bearing
disappearance signature. The exact client `movement_time_ms` is the causal join key. Never join
host events to replay stops by nearby wall time.

A **stuck episode** is a cluster of Stuck requests within 60 seconds and 10 yards. This keeps
one retry storm from masquerading as many independent navigation failures. Raw invocation
counts remain beside the clustered count. `stuck_retry_window_seconds` sums individual retry
windows and can overlap; `stuck_union_seconds` merges overlap per replay for elapsed-time
accounting. Neither is all stationary time. `longest_stationary_interval` independently
catches quiet stalls where the policy never invoked Stuck.

Exact replay bytes are deduplicated across overlapping artifact sources. Adjacent
`episode.json` metadata supplies episode/request provenance, score, and wowborg version, and
the JSON includes aggregate `by_version` summaries.

Damage and death coordinates come from the stateful player replay, not from a static heatmap.
The JSON retains every damage event, so callers can build damage/death heatmaps or preserve
the time-ordered trajectory around an event.

Form requests and observed aura states are available now. Exact continuous form uptime is not
yet summarized by the canonical report; add that projection to the owner reducer if an uptime
question needs more than start/end/significant-interval evidence. Do not infer successful form
activation from a cast request alone.

## Direct owner report

For causal inspection of one local replay:

```bash
cd ~/coding/coworlds/coworld-vanilla-wow
uv run --extra supporting wow-sdk replay-report /path/to/replay.json
```

The same command can fetch current league evidence by league and player. Use it for discovery,
then pin the exact round and episode before making a causal claim. The lab batch profiler is
the aggregation layer; `wow-sdk replay-report` remains the source of truth for each replay.
