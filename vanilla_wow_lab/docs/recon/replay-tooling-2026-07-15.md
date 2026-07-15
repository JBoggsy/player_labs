# Recon: replay & episode-evidence tooling for Vanilla WoW

**Date:** 2026-07-15. **Consumer:** building this lab's reporting stack — what exists to
view, decode, inspect, analyze, and understand `.cwreplay` artifacts (and per-episode
evidence generally), what we must build, and in what order. Citations into
`~/coding/coworlds/coworld-vanilla-wow` (@ `312d1d0c7`) and this repo.

## Mission

After a hosted episode we get artifacts back. Session 3 proved the pain: **no results, no
policy logs — replay only**, in a custom binary format. This recon inventories every replay
tool (game repo + platform + sibling labs) and ends with a build plan. Wowborg-side tracing
(the other evidence half) shipped alongside this recon — see "Our evidence channels" below.

## The format in one paragraph

`.cwreplay` = 8-byte magic `CWREPLAY` · u16 format version 1 · game/version strings · u64
start-ms · length-prefixed **JSON header** (`vanilla_wow.replay.v4`: scenario identity,
sanitized config, lifecycle events, results when scored) · typed records
(`docs/protocol/cwreplay.md:21-41`; codec `src/vanilla_wow_coworld/replay_format.py:55-227`).
Record `0x02` (mandatory) holds **CWPARTY4**: per party member, an intact **VMaNGOS PKT
2.1 packet capture** — every world packet, both directions, decrypted, timestamped
(`party_wire.py:121-155, 321-393`). Record `0x01` (RFC only) is a zlib-JSONL godview
camera/boundary sidecar. **The replay is not an event log — it is the full decrypted wire
traffic of all five characters.** Everything observable in our designed observation space
is in there; the tooling question is decode-and-reduce.

## What exists and runs today

### Viewers (human)

| Tool | What it shows | Launch |
|---|---|---|
| `global_viewer` (native Nim) | Full 3-D playback of one POV — world, combat, chat (`/say` visible!), XP/loot; POV switching, speed/seek, RFC fly-cam | `nim r -d:release player/global_viewer.nim -- --replay=<path-or-url>` (`docs/global-viewer.md:184-192`); needs client data + nimby deps |
| Hosted WASM viewer | Same engine in-browser; the platform serves it per episode | `uv run coworld replay-open <episode> --hosted`, or download + `coworld replay <coworld_id> ./replay` (`docs/coworld-readiness.md:483-506`) |
| `bot_visual_replay.py` | MP4 reels rendered from a replay under Xvfb | `python3 player/tools/bot_visual_replay.py render <profile> <replay>` |
| `vanilla-wow replay` CLI | Text/JSON summary of the header (scenario, events, results) | `vanilla-wow replay --uri file://<path> [--json]` (`replay.py:367-390`) |

The hosted viewer route was fixed after our session-2 docs were written (commit
`bd7dc9eff` "Launch hosted replays in the WASM viewer") — `coworld replay-open --hosted`
is the low-friction human path for our smokes.

### Decoders (agent) — and the two-tier knowability boundary

The complete Python decode stack ships **inside the game package we already install**:

```
decode_coworld_replay (replay_format.py:142)     → envelope + header + records
  └ decode_party_wire (party_wire.py:353)        → per-member PKT streams
      └ read_vmangos_pkt (party_wire.py:121)     → [(direction, time, opcode, body), …]
```

**Be precise about what each tier can know** (this boundary shapes the whole roadmap):

- **Tier 1 — stateless decode** (stdlib Python, no client): packet framing + any fact a
  single packet body self-describes. That includes chat text, login verify, XP-gain
  events, cast results, and — because 1.12 movement is client-authoritative — **each
  member's own trajectory** (every outbound `MSG_MOVE_*` body carries plaintext
  flags/time/x/y/z/o, captured pre-encryption). Opcode-body decoding grows via
  `docs/vanilla-wow-protocol.md` + `wowborg/opcodes.py`.
- **Tier 2 — stateful reduction** (requires a client reducer): facts that accumulate
  across packets — other units' positions/health over time, `SMSG_UPDATE_OBJECT`
  field values (update-mask walk + field table + object store), aura/death transitions,
  loot/vendor window contents. The supported recipe is the game repo's
  `player/tools/inspect_party_wire_replay.nim`: `readReplayWireBundle` → classifier →
  `mirror.applyViewerEvent` — the full **replay → PlayerStateMirror** pipeline, headless,
  no renderer/realm/client-data. Extending it to dump TelemetrySnapshot JSONL per POV is
  a modest Nim tool (and an upstream-shaped contribution), not an architectural change.

Also runnable today: `vanilla-wow rfc-episode-audit --replay … --results …` (full
structural verification, `rfc_episode_audit.py:516-525`).

### Platform analysis roles (read results, not replays)

Reporter (Rust/Wasm, `reporters/rfc/`) consumes only `results.json` → recap/events/stats;
grader/diagnoser likewise (`rfc_grader.py:37-50`). So platform-side analysis gives us
nothing packet-level; the replay is ours to mine.

### Lab-side machinery (proven by sibling labs)

Three tiers, all present in crewrift/ctf and partially in heartleaf
(scout report, this repo):

1. **Fetch** — the shared `coworld-episode-artifacts` skill: per episode `episode.json`,
   `results.json`, replay bytes, `logs/policy_agent_N.log`, and
   `artifacts/policy_artifact_N.zip`; `--watch` streams while the batch runs.
2. **Fast survey** — `results.json` + `episode.json` only → self-contained HTML report
   (crewrift-survey is the template).
3. **Deep dig** — replay → events → DuckDB/Parquet warehouse (crewrift/ctf). Crucial
   difference in our favor: crewrift must *re-simulate* replays with a version-matched
   Nim binary (hash-fails on drift); **our replay decodes with pure Python** — no
   version-matched build step, no re-simulation. The deep tier is cheaper here.

## What our first smoke actually left on disk

`vanilla_wow_lab/episode_data/` (xreq_23feebad, 4 episodes): `episode.json` (4.7 KB, has
job_id/scores/participants/variant/config) + `replay.json` (240–331 KB, **actually a
CWREPLAY binary** despite the name; served uncompressed) per episode. No results.json, no
logs, no policy artifacts — all 4 episodes exhausted their fetch retries. Two gaps, two
different fixes:

- **results.json/logs retention** — platform-side; still the open question from session 3
  (the game's README badge is gated on exactly this retained-artifact proof).
- **Our own evidence** — now solved wowborg-side (below): we stop depending on stdout
  retention entirely.

## Our evidence channels (shipped with this recon)

wowborg v2 now emits on **three redundant channels**, ordered by retention confidence:

1. **Policy-artifact bundle** (`wowborg/artifact.py`) — at session end the shim zips
   `trace.jsonl` + `action-results.jsonl` + final `state.json`/`heartbeat.json` and PUTs
   to `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` (the same contract the players SDK's
   `jsonl@artifact` uses; fetchable via `GET /jobs/{job}/policy-artifact/{idx}`,
   policy-scoped, no log cap). This is the ctf/crewrift-proven answer to the log-retention
   gap.
2. **`trace.jsonl` + `WOWBORG-TRACE` stdout** (`wowborg/trace.py`) — every observation
   tick, intent, outcome (typed settlement fields), say, session start/end/error, as
   structured JSONL, mirrored to stdout in case logs *are* retained.
3. **`/say` breadcrumbs** (`ShimBridge.say`, rate-limited 5 s) — chat packets are real
   wire traffic, so they land **inside the CWREPLAY** and render in the viewer. When
   channels 1–2 are dropped, the replay itself still carries our leg-by-leg narrative.
   (CWREPLAY v4 stores no bot-policy record; `/say` is the documented visibility channel —
   `cwreplay.md:159-164`.)

## Build plan — a growing stack for the whole optimization loop

This tooling is **not a one-off walk-checker**: it is the lab's observability layer, and
each wowborg capability tier pulls the corresponding analysis capability with it. The
crewrift lab's history is the precedent — survey → warehouse → diagnose → A/B all sit on
the same artifact plumbing. Planned growth, keyed to policy tiers:

**Now (T0 — navigation):**
1. ✅ **`tools/cwreplay.py`** — stateless decoder: `summary` / `packets` JSONL /
   `trajectory` (own-position stream + cumulative travelled yards from outbound
   MovementInfo) / `members` / `header`. Validated against the 4 smoke replays
   (retroactively confirmed v1's login ×5 members ×4 episodes).
2. **Trace ↔ replay cross-check** — join wowborg's `trace.jsonl` intents against the
   replay's observed movement packets and settlements: the automated
   "sent is not accepted" audit. First real use: the v2 hosted smoke.

**Next (with the first real batches):**
3. **`wow-survey` skill** — crewrift-survey shape: `episode.json` + `results.json` when
   retained + `cwreplay.py` summaries always; per-slot travelled distance, `/say`
   breadcrumbs, login/duration health; flagged-episodes shortlist with Observatory
   links; Ink & Print HTML. The loop's standing "report" instrument.

**As wowborg gains combat/quests (T1):**
4. **Tier-2 decode — replay → TelemetrySnapshot JSONL** (Nim, upstream-shaped): extend
   `inspect_party_wire_replay.nim`'s recipe to dump per-POV mirror snapshots. This is
   what unlocks combat analysis (who hit whom, health curves, aura uptime, death
   causes) — the facts stateless decode cannot know. Build when the first combat
   policy needs debugging, not before.
5. **Event warehouse** — DuckDB/Parquet over exported packet/snapshot JSONL, re-keyed
   slot→policy-version (the crewrift/ctf pattern): cross-episode SQL for optimization
   questions ("where do deaths cluster", "XP/hour by route", "which pulls go wrong").
6. **`wow-ab` adapter** — a `compare.py` metric adapter over the shared `coworld-ab`
   engine (legs-reached → XP/hour → boss-clear metrics as the policy matures).

The tier-1/tier-2 boundary above dictates this order: everything in 1–3 is stateless
decode; 4 is the one new build that unlocks the stateful facts; 5–6 are consumers.

## Unresolved

- Why results.json/policy logs weren't retained for vanilla_wow episodes (platform gap vs.
  game-package gap) — carried over from session 3; the policy-artifact channel makes us
  robust to it either way, but the survey tier is richer if it's fixed.
- Whether the hosted runner injects `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` for this game's
  player containers (the SDK contract suggests yes; the first v2 smoke will confirm —
  the shim logs `evidence bundle: …` either way).
- Local `global_viewer` requires WoW client data (`VANILLA_WOW_CLIENT_DATA_DIR`) we
  haven't provisioned; `coworld replay-open --hosted` avoids that entirely.

## Files read

Game repo: `docs/protocol/cwreplay.md`, `replay_format.py`, `party_wire.py`, `replay.py`,
`rfc_episode_audit.py`, `global_viewer.nim` (launch/params), `bot_visual_replay.py`,
`reporters/rfc/`, `inspect_party_wire_replay.nim` (via scout). This repo: the
`coworld-episode-artifacts` skill + endpoint map, crewrift/ctf/heartleaf tooling +
skills, `episode_data/` contents, players SDK `trace_outputs.py` (artifact-upload
contract).
