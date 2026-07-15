# Vanilla WoW tentative lessons — session buffer

**Session started:** 2026-07-14 17:07. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`vanilla_wow_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (Vanilla-WoW-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### The typed obs/action protocols in our docs are NOT the hosted-policy interface — they live inside the Nim player's container

Evidence: Recon of `src/vanilla_wow_coworld/` (2026-07-14, HEAD `312d1d0c7`) showed the
`/player` WS carries only lifecycle (`wow_session`/`pong`/`final`, `session.py:99-175`) and
`/tcp/*` are unfiltered byte pipes (`tcp_proxy.py:66-78`). `TelemetrySnapshot`, `BotAction`,
`movement_settlement.v1` are the file bridge between the Nim client and its bot brain
(`wow_sdk/nim_client.py:2404`) — wowborg gets none of them. Our protocol doc reads as if
they're the game's player API; easy to mis-plan against.
Status: recon report `docs/recon/navigation-obs-actions-2026-07-14.md` is the corrective.

### WoW 1.12 movement is client-authoritative — "move" = self-reporting integrated positions, not requesting motion

Evidence: `MSG_MOVE_*` packets carry the client's own MovementInfo (flags, time, x/y/z/o);
the reference bots integrate `pos += speed·Δt·(cos o, sin o)` at 200 ms and send
`MSG_MOVE_HEARTBEAT` (`king_richard/world/movement_and_observation.nim:999-1094`). There is
no click-to-move API. Consequence: our own pose between authoritative packets is dead
reckoning, and "arrived" is self-asserted unless the server corrects us.

### No terrain is observable over the wire — geometry comes only from extracted client-side data files

Evidence: no packet carries geometry; the Nim client loads maps/vmaps/Detour mmaps from
`local_data/vmangos-5875-data` (`simulation/terrain.nim:105`, `navmesh_collision.nim:457`)
and shells to a Detour helper (`navmeshes.nim:571-610`). wowborg has none of this → z-drift
on slopes is the expected first failure mode; start in flat areas (orc valley) and consider
bundling extracted mmaps later.

### Server force packets (speed/root/knockback/teleport) each demand a counter-echo ACK or the session desyncs

Evidence: `SMSG_FORCE_*_SPEED_CHANGE` / `MSG_MOVE_TELEPORT_ACK` / knockback all require the
echoed counter + MovementInfo (`viewers/movement_emitters.nim:154-290`). A movement-capable
wowborg can't keep v1's drain-and-ignore loop — ACK handling is a prerequisite, not an
enhancement.

### The reference TelemetrySnapshot hides all interaction windows (loot/gossip/vendor/trainer/quest-frame) from its Python policy — a real design fork for wowborg

Evidence: obs/action-space design recon (2026-07-15): the Nim runtime's `state.json` never
exports window contents; its composite Nim actions (loot-all, sell_junk, train-all) consume
them internally, and its Python policies parse load-bearing *result message strings*
(`"move into melee before auto attack"`, `spell_traits.py:125-135`) to compensate. Our design
(docs/designs/wowborg-observation-action-spaces.html §3.8, §4.9) exposes windows as typed
observations + typed result reasons instead. If wowborg policies feel starved of menu-level
choice or start grepping result text, revisit this lesson.

### 1.12 wire truth has sharp knowability edges worth memorizing before designing observations

Evidence: same recon. No threat packets (derive from per-unit target_guid); no aura durations
or cast progress for OTHER units (booleans/spell ids only); no geometry; zone id is
client-derived, not server-sent; spell metadata (name/cost/range) needs static DBC tables;
but item/creature/GO/quest metadata is all servable via query opcodes (88/97/93). Designs
that assume any of these are observable will silently fabricate state.

### The hosted reference player already IS a "bring your own Python policy" harness — swap `KING_NIMROD_COMMAND`, run `king_richard --scenario=nim-control` with `KING_RICHARD_AUTONOMOUS=0`

Evidence: build-vs-reuse recon (2026-07-15). The shipped hosted image's own path is
`vanilla_wow_coworld.player` (WS session wrapper) → spawns `$KING_NIMROD_COMMAND` →
`hosted_general_grinder.py` → spawns the Nim client (nim-control mode, planner off) + a
Python policy loop over the `state.json`/`action.json` file bridge (`Dockerfile:65`,
`hosted_general_grinder.py:28-38,146-162`). The file contract is versioned and documented
(`vanilla_wow.llm_sdk_state.v1`, `wow-sdk/README.md`); `runtime.py`+`protocol.py` vendor
cleanly (stdlib+pydantic only). Building our own policy this way is the proven template.

### king_richard HARD-FAILS at startup without navmesh helper + mmap tiles; the reference player image ships ONLY Valley of Trials tiles

Evidence: `king_richard.nim:32-42` (`requireKingRichardNavmesh` quits before login);
`player/Dockerfile:59-63` copies `vmangos-navmesh-helper` + a 001.mmap Valley-of-Trials
subset only. Any wowborg-on-shim image roaming further (RFC = map 389!) must bundle the
right mmap tiles from the vmangos_data build context. This is the biggest hidden cost of
the reuse path — and also proof the from-scratch path is worse (no navmesh at all).

### Session-3's "no policy logs retained" was probably just a 403 — policy-logs routes need `--elevated` for softmax team members

Evidence: v2 smoke (2026-07-15): `GET /jobs/{job}/policy-logs` → 403 "User is not a
softmax team member" on OUR OWN policy's episode. The artifact skill documents
`--elevated` (X-Use-Elevated-Privileges) for exactly this. Session 3 recorded "logs not
retained" as a platform mystery; the mundane explanation is the watcher hit 403s and
recorded nothing. Always retry artifact fetches with `--elevated` before concluding
retention gaps. (`policy-artifact` 404'd too — whether the runner injects
COWORLD_PLAYER_ARTIFACT_UPLOAD_URL for this game is still open; read the shim's
"evidence bundle:" log line via elevated logs.)

### The xreq DETAIL endpoint intermittently 500s while the LIST endpoint stays healthy — wrap --watch in a retry loop

Evidence: v2 smoke: `GET /v2/experience-requests/{id}` 500'd repeatedly (~30+ attempts),
killing fetch_artifacts --watch each time, while `coworld xp-request list --mine`
kept working and episodes kept completing/downloading between crashes. Workaround: a
5-line bash retry wrapper around the watch command; it resumes from disk. Report
upstream if it persists.

### The Nim shim narrates our queued actions as its own /say lines ("Policy action: <kind>") — a free-but-noisy extra replay channel

Evidence: v2 replay: alongside our own breadcrumbs, each queued action produced a
"Policy action: move/chat_say" say from the client layer. Useful corroboration;
also means breadcrumb extraction should filter for our `wowborg ` prefix.

### CWREPLAY decoding has TWO tiers: self-describing packets decode statelessly; derived world state needs the client reducer

Evidence: replay recon + `tools/cwreplay.py` (2026-07-15; boundary sharpened by James).
Record 0x02 holds per-member VMaNGOS PKT 2.1 streams (every packet, both directions,
decrypted). Tier 1 (stateless, stdlib Python): framing, chat, login verify, XP events,
and — because 1.12 movement is client-authoritative — each member's OWN trajectory from
outbound MovementInfo bodies. This tier retroactively CONFIRMED v1's login (×5 members
×4 episodes). Tier 2 (stateful): other units' positions/health, update-field values,
aura/death transitions — these REQUIRE running packets through a client reducer;
the supported recipe is the game repo's `inspect_party_wire_replay.nim`
(replay → PlayerStateMirror), a modest Nim tool, not an architectural change. Don't
promise tier-2 facts from tier-1 tooling. Still cheaper than crewrift's version-matched
re-simulation for tier 1.

### Hosted evidence must be multi-channel: policy-artifact zip > stdout logs > /say breadcrumbs in the replay

Evidence: session 3 lost ALL policy stdout (retention gap, cause still unknown) and
results.json. The proven answer (ctf/crewrift `jsonl@artifact` pattern): PUT an evidence
zip to `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` (policy-scoped `policy-artifact` job routes,
no log cap). And since CWREPLAY v4 records real chat packets, rate-limited `/say`
breadcrumbs make the replay itself carry the policy narrative — the only channel that
provably survives. wowborg v2 now emits all three.

### `coworld download <game>` is the clean way to pin a shim base image — it pulls the DEPLOYED images and writes their digests to coworld_images.json

Evidence: v2 build (2026-07-15). `uv run coworld download vanilla_wow` fetched package
0.1.19 with the player image digest (`sha256:665adff0…`), which became the
`WOWBORG_BASE_IMAGE` pin in `tools/versions.env`. This sidesteps the crewrift-era problem
of guessing which game-repo commit matches the deployed league — the digest IS the
deployed artifact. Bump signal: new version in `coworld list`.

### Repo was moved on disk (~/coding/personal_labs/personal_labs_wow); stale .venv shebangs broke `uv run pytest` silently-ish

Evidence: `uv run pytest` failed with "Failed to spawn: pytest" then "bad interpreter:
/Users/jamesboggs/coding/personal_labs_wow/.venv/bin/python" — the venv pre-dated the
repo move. Fix: `rm -rf .venv && uv sync`. If a spawn failure mentions a path that no
longer exists, rebuild the venv before debugging anything else.

### Reference-client constants worth hardcoding: run 7.0 yd/s, walk 2.5, turn π rad/s, arrival 3.0 yd, bot cadence 200 ms, jumpZ 7.95797334

Evidence: `viewers.nim:216-221`, `locomotion.nim:9-13`, `protocol.py:39`
(`MOVE_ARRIVAL_DISTANCE`), `packets.nim:192-193` (`FollowStepSeconds 0.20`). The reference
client itself skips the six speeds in the update-object create block (`protocol.nim:499`)
and trusts defaults + force packets — we can do the same.
