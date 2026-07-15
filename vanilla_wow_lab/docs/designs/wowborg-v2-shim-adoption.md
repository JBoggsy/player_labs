# Design: wowborg v2 — adopt the Nim shim, wrap it swappably

**Date:** 2026-07-15
**Status:** approved direction (human: "we just gotta use the shim… wrap it nicely so we can
swap out/update the shim easily"); this doc fixes the architecture before implementation.
**Supersedes:** the from-scratch Python-client path implied by
[`wowborg-player-design.md`](wowborg-player-design.md) (v1 stays as a debugging asset).
**Companion:** [`wowborg-observation-action-spaces.html`](wowborg-observation-action-spaces.html)
— the typed spaces; v2 implements a thin T0 slice of them over the shim.

## Decision

Build wowborg v2 **on top of the deployed reference player image**, driving the bundled Nim
client (King Richard in `nim-control` mode, autonomous planner off) through its documented
file bridge (`state.json` / `action.json` / `action-results.jsonl`). Do not reimplement the
WoW protocol in Python.

Evidence for this call (build-vs-reuse recon, 2026-07-15, repo @ `312d1d0c7`):

- A faithful Python client is a ~20–45k-line port of protocol machinery encoding years of
  correctness (the reference's *slim* raw walker is still 12.4k Nim lines importing shared
  typed parsers).
- The hosted reference image's **default path already is our target architecture**:
  `vanilla_wow_coworld.player` (WS wrapper) → `$KING_NIMROD_COMMAND` →
  `hosted_general_grinder.py` → `king_richard --scenario=nim-control` +
  `KING_RICHARD_AUTONOMOUS=0` + a **Python policy loop** over the file bridge
  (`player/Dockerfile:65`, `hosted_general_grinder.py:28-38,146-162`).
- The bridge is a versioned, documented seam: `vanilla_wow.llm_sdk_state.v1` /
  `vanilla_wow.bot_action.v1` (`wow_sdk/protocol.py:10-27`; `wow-sdk/README.md` §Python API).
- king_richard hard-requires navmesh data (`king_richard.nim:32-42`); the deployed image
  ships the helper + Valley-of-Trials tiles. From scratch we'd have neither.

## The swap seam (the "wrap it nicely" requirement)

Three layers, one rule: **everything that knows it's King Richard lives in one module.**

```
┌─ policy (wowborg/policies/…) ────────────────────────────────┐
│ sees ONLY wowborg.bridge types (Observation, intents,        │
│ ActionOutcome) — never wow_sdk models, files, or processes   │
├─ bridge (wowborg/bridge.py) ─────────────────────────────────┤
│ our typed seam: adapts the shim's TelemetrySnapshot +        │
│ ActionExecutionResult into the design doc's observation/     │
│ action shapes (T0 slice now). Imports wow_sdk (present in    │
│ the base image) — the only module that does.                 │
├─ shim runtime (wowborg/shim.py) ─────────────────────────────┤
│ the ONLY King-Richard-aware code: env mapping, process       │
│ spawn (king_richard --scenario=nim-control, AUTONOMOUS=0),   │
│ startup wait, deadline/exit handling. Modeled line-for-line  │
│ on the proven hosted_general_grinder.py.                     │
└──────────────────────────────────────────────────────────────┘
```

Swapping/updating the shim then means:

- **Routine update** (new game release): bump `WOWBORG_BASE_IMAGE` in
  `vanilla_wow_lab/tools/versions.env`, rebuild. No code change unless the
  file-bridge protocol version moved (pydantic validation fails loudly if it did).
- **Different shim** (e.g. a future first-party SDK runtime, or our own client maturing):
  reimplement `shim.py` + the `bridge.py` adapter half; policies untouched.

## Image: layer on the deployed artifact, don't rebuild it

The deployed player image is pullable via `coworld download vanilla_wow` (today:
`vanilla_wow 0.1.19`, player image digest `sha256:665adff0…`, verified locally to contain
`/usr/local/bin/king_richard`, `/usr/local/bin/vmangos-navmesh-helper`,
`/opt/coworld-player/mmaps` (Valley of Trials), installed `wow_sdk` +
`vanilla_wow_coworld`). So:

```dockerfile
ARG WOWBORG_BASE_IMAGE          # pinned digest from tools/versions.env
FROM ${WOWBORG_BASE_IMAGE}
COPY wowborg /opt/wowborg/wowborg
ENV PYTHONPATH=/opt/wowborg:… \
    KING_NIMROD_COMMAND="python3 -m wowborg.shim"
# CMD inherited: python3 -m vanilla_wow_coworld.player  (the WS wrapper stays theirs)
```

Why this beats rebuilding their Dockerfile from the repo:

1. **Exact-version parity** — we run the *same bytes* the league runs (game repo `main`
   runs ahead of deployment; the crewrift lab learned this the hard way — see the
   `CREWRIFT_REF` pin rationale in `crewrift_lab/tools/versions.env`).
2. **No Nim toolchain, no vmangos build contexts** — the two heaviest reproduction costs
   (nimby.lock toolchain; `vmangos_base`/`vmangos_data` compose contexts) disappear.
3. **The shim-update path is the pin bump** — which is exactly the swap seam we want.

Trade-off accepted: we inherit their image's Python env (3.12) and must keep our additions
dependency-light (stdlib + what's already installed: pydantic via wow_sdk). If we ever need
our own deps, `pip install` in our layer.

**Pin discipline (`tools/versions.env`):** `WOWBORG_BASE_IMAGE` records the *digest* (not a
tag) plus the vanilla_wow package version it came from and the date. Bump when the deployed
game bumps (signal: new `vanilla_wow` version in `coworld list` / the live manifest fetch).

## Process model in the container (all inherited-proven)

1. `vanilla_wow_coworld.player` (CMD, theirs) — consumes `wow_session`, starts local
   WS→TCP proxies when tunneling, exports `KING_NIMROD_{REALM_HOST,REALM_PORT,USERNAME,
   PASSWORD,CHARACTER_NAME}`, spawns `$KING_NIMROD_COMMAND`, sends `done` when it exits.
2. `wowborg.shim` (ours) — maps `KING_NIMROD_*` → `KING_RICHARD_*`, sets
   `WOW_SDK_NIM_RUNTIME_DIR`, `KING_RICHARD_AUTONOMOUS=0`,
   `PYTHONPATH+=/opt/coworld-player`; spawns `king_richard --scenario=nim-control`; waits
   for `state.json` (startup timeout); runs the policy loop in-process; on completion/
   deadline stops the child and exits 0.
3. `king_richard` (theirs) — logs into the realm, writes `state.json` (~0.5 s cadence),
   executes `action.json`, appends `action-results.jsonl`.

Differences from `hosted_general_grinder.py` (deliberate, small):
- The policy loop runs **in-process** in the shim (no third process) — one fewer failure
  seam; the pilot-style subprocess split exists for their CLI reuse, which we don't need.
- Duration: `WOWBORG_DURATION_SECONDS` (default 120 s, the grinder's proven hosted budget)
  — bounded by design; the 27.8 h lesson stays structurally impossible.
- Policy selection: `WOWBORG_POLICY` env (default `random_walk`) → registry in
  `wowborg/policies/__init__.py`.

## The file-bridge contract (verified shapes)

- **`state.json`** — one `TelemetrySnapshot` (`wow_sdk.protocol`, `extra="forbid"`),
  atomically replaced; read via `wow_sdk.runtime.EmbeddedClientRuntimeClient.read_snapshot()`.
- **`action.json`** — flat envelope `{sequence ≥1, request_id, kind, …allowlisted args}`
  (`runtime.py:244-255`; movement keys `runtime.py:15-48`), atomic write, consumed once by
  sequence.
- **`action-results.jsonl`** — one `ActionExecutionResult` per line (typed
  `movement_settlement` / `navmesh_traversal` / `client_state`), offset-cursor reads.

## T0 scope (this iteration): random-nearby-point navigation

- `bridge.py` exposes: `observe() → Observation` (self pose/vitals/death flags, movement
  progress, seq/age — the T0 slice of the design doc's §3) and
  `move_to(dest, arrival_radius) / wait() → ActionOutcome` (typed settlement, §4.9 slice).
- `policies/random_walk.py`: on settle → pick a random point 10–20 yd away (uniform angle,
  current z, `target_z_known=False` so the executor's Detour projection fixes z) → emit
  `move` → wait for settlement → repeat until duration elapses. Log every leg + settlement
  kind; count `reached` vs other kinds as the smoke metric.
- Unit tests: bridge adaptation (snapshot→Observation, result→ActionOutcome) against
  fixture JSON captured from the real contract models; shim env-mapping; policy step logic
  with a fake bridge. No network, no Nim in tests.
- Hosted validation: build → upload → `orc-fresh-start` experience request; success =
  nonzero displacement across snapshots + ≥1 `reached_target` settlement in our logs
  (retention caveat from session 3 noted — logs may again be unretained; the replay is the
  fallback evidence).

## Layout

```
vanilla_wow_lab/wowborg/
  main.py, run.py, …            v1 raw client (kept: debugging asset; unused by v2 image)
  shim.py                       King-Richard-aware supervisor (the swap point)
  bridge.py                     typed seam over the file bridge (imports wow_sdk)
  policies/__init__.py          policy registry (WOWBORG_POLICY)
  policies/random_walk.py       T0 policy
  Dockerfile                    v2: FROM pinned base + our layer (replaces v1 Dockerfile)
  tests/…                       + test_shim.py, test_bridge.py, test_random_walk.py
vanilla_wow_lab/tools/
  versions.env                  WOWBORG_BASE_IMAGE pin (+ provenance comment)
  build_player.sh               build with --platform=linux/amd64, sourcing versions.env
```

## Risks

1. **Base image opacity** — we depend on env/entrypoint conventions of an image we don't
   build. Mitigation: the pin records provenance; `build_player.sh` sanity-checks the base
   (king_richard present, wow_sdk importable) at build time.
2. **Protocol drift on pin bump** — snapshot/result schemas move with the game. Mitigation:
   pydantic `extra="forbid"` fails loudly; bridge tests re-run against the new image's
   models on every bump.
3. **Movement settlement semantics** — our first hosted run is the real test that
   `nim-control` + `AUTONOMOUS=0` behaves for a pure `move` diet (the grinder always mixes
   combat). Watch for planner-off idle behaviors (auto-eat? stuck recovery?) in results.
4. **amd64 emulation** — base is linux/amd64; local smoke runs under emulation on Apple
   Silicon (slow but workable; hosted is the real target).
