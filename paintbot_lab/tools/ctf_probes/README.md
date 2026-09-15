# ctf_probes — replay and shell probes for the Season 2 engine

Small Nim programs that answer "what did the cogs actually do" from a hosted
replay, and "what would the engine-hosted body do on this map" without any
policy. Use the probes for targeted engine and protocol questions.

They are NOT standalone: each one imports the coworld-ctf engine by relative
path, so build them from inside a coworld-ctf checkout. Every source file
reads config/data assets relative to the current directory, so run from the
checkout root too.

```sh
cd ~/coding/coworlds/coworld-ctf
cp ~/coding/personal_labs/personal_paintbot/paintbot_lab/tools/ctf_probes/move_probe.nim tools/zz_move_probe_tmp.nim
export WASMTIME_C_API=$PWD/tools/runtime_spike/.deps/installed/aarch64-macos/wasmtime-c-api
nim c -d:release -d:noSignalHandler --threads:on --hints:off -o:/tmp/move_probe tools/zz_move_probe_tmp.nim
/tmp/move_probe path/to/episode.replay
rm tools/zz_move_probe_tmp.nim
```

A probe only loads replays whose GameVersion is in the engine's
`ReplayCompatibleGameVersions`; build against the commit that produced the
replay (GV50 replays need a pre-GV51 checkout).

| file | what it prints |
|---|---|
| `move_probe.nim` | per cog: alive ticks, ticks with displacement, distance, kills/deaths, ticks outside the zone, death tick and whether it died outside the zone (hash-validated re-simulation) |
| `hash_probe.nim` | tick-1 hash of a replay versus playback, then structural sweeps of `gameHash` (which config-driven field layout reproduces the recorded hash) — how the `num_agents` echo bug was found |
| `nav_probe.nim` | drives the real shell episode (`initFirstLightEpisode`, default play + reflexes, no policy) on the replay's map with the real zone schedule for N seats; per seat first move, ticks outside the zone while still, and plan-job dumps — how the reflex/budget/replan defects were found |
| `plan_probe.nim` | cost (units, ticks) of single body plans between fixed points on the replay's map |
| `verify_round.sh` | one-shot: round id → episodes → first replay → `move_probe` → agent-3 log grep for names/huddle (expects the probe binary in the session scratchpad; adjust the path) |

Replays: `uv run coworld episodes -r <round_id> --json` (the round **id**, not
the number) gives `replay_url`; logs need `uv run coworld
episode-logs <ereq> --game|--agent N -d <dir>`.

**Access contract:** use normal participant access only. Private opponent evidence remains unavailable.
