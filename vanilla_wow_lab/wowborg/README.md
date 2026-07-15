# wowborg

`wowborg` is our Python Vanilla WoW Coworld player. **v2 architecture: our Python policy
drives the game's bundled Nim client (the "shim") through its file bridge** — we do not
speak the WoW wire protocol ourselves. Design and rationale:
[`../docs/designs/wowborg-v2-shim-adoption.md`](../docs/designs/wowborg-v2-shim-adoption.md);
the target typed observation/action spaces:
[`../docs/designs/wowborg-observation-action-spaces.html`](../docs/designs/wowborg-observation-action-spaces.html).

## v2 layout (the live player)

- `shim.py` — King-Richard-aware supervisor, launched by the base image's WS wrapper via
  `KING_NIMROD_COMMAND`. Spawns `king_richard --scenario=nim-control` (autonomous planner
  off), waits for `state.json`, runs the policy loop, exits 0. **The swap point**: a new
  shim means replacing this module + the adapter half of `bridge.py`.
- `bridge.py` — the typed seam over the file bridge (`state.json` / `action.json` /
  `action-results.jsonl`). The only module that imports `wow_sdk` (present in the base
  image). Adapts snapshots/results into `types.py` shapes.
- `types.py` — dependency-free policy-facing types (`Observation`, `ActionOutcome`,
  `Position`). Policies import only this.
- `trace.py` — structured tracing: every observation tick, intent, and typed outcome to
  `trace.jsonl` AND stdout (`WOWBORG-TRACE` prefix) — dual channels because hosted log
  retention has failed us before. `WOWBORG_TRACE_FILE` overrides the path.
- `artifact.py` — session-end evidence bundle (trace + action-results + final state)
  zipped and PUT to `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` — fetchable per slot via the
  `policy-artifact` job routes, immune to the stdout log cap/retention gap.
- `policies/` — the policy registry (`WOWBORG_POLICY` env; default `random_walk`).
  `random_walk.py` is the T0 navigator: random 10–20 yd legs, one typed settlement each.
- `Dockerfile` — layers `wowborg/` onto the **deployed reference player image** (pinned by
  digest in [`../tools/versions.env`](../tools/versions.env)) and repoints
  `KING_NIMROD_COMMAND` at our shim. The base's CMD (`vanilla_wow_coworld.player` WS
  wrapper), Nim binaries, navmesh data, and `wow_sdk` are inherited unchanged.

Container env knobs: `WOWBORG_POLICY` (default `random_walk`),
`WOWBORG_DURATION_SECONDS` (default 120), `WOWBORG_RUNTIME_DIR`,
`WOWBORG_STARTUP_TIMEOUT_SECONDS`, `WOWBORG_TRACE_FILE`,
`WOWBORG_KING_RICHARD_BINARY` (test seam).

**Evidence channels (ordered by retention confidence):** ① the policy-artifact zip
(`artifact.py`), ② `trace.jsonl` + stdout, ③ `/say` breadcrumbs (`ShimBridge.say`,
rate-limited) which land inside the CWREPLAY itself — decode with
[`../tools/cwreplay.py`](../tools/cwreplay.py) (`summary` / `packets --say-only`).
Replay tooling landscape: [`../docs/recon/replay-tooling-2026-07-15.md`](../docs/recon/replay-tooling-2026-07-15.md).

## v1 modules (kept as a debugging asset — not in the v2 image path)

- `wire.py`, `srp6.py`, `crypt.py`: pure byte/crypto protocol core.
- `realmd.py`: SRP6 realmd login and realm-list request.
- `world.py`: mangosd auth, character selection, login verify, idle pings.
- `tunnel.py`: `/tcp/realmd` and `/tcp/world` WebSocket byte tunnels.
- `session.py`, `run.py`, `main.py`: Coworld `/player` orchestration (v1's entrypoint).

## Commands

```bash
uv run pytest vanilla_wow_lab/wowborg/tests -q       # all tests (v1 + v2)
vanilla_wow_lab/tools/build_player.sh                 # build players-wowborg:dev (amd64)
```

The build script sources the base-image digest pin from `../tools/versions.env` and
sanity-checks the built image (king_richard, navmesh data, wow_sdk, our modules, the
`KING_NIMROD_COMMAND` override). To bump the shim when the league redeploys the game, see
the bump notes in `versions.env`.
