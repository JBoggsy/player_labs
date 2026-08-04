# Vanilla WoW working context

**What this is.** The live, high-signal state of *what we're working on right now* in the
Vanilla WoW lab — the minimal cross-session facts to carry into the next session. Read it on
startup to resume; **update it as you learn** (keep it tight). This is *not* a log: the full
game reference lives in [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md); this
file is the one-screen "where are we and why."

> Read order for a newcomer: this file → [`README.md`](README.md) →
> [`docs/vanilla-wow-gameplay.md`](docs/vanilla-wow-gameplay.md) →
> [`docs/vanilla-wow-player-contract.md`](docs/vanilla-wow-player-contract.md). And the
> lab-wide [`../AGENTS.md`](../AGENTS.md) for the operating model.

---

## Status (2026-08-04): COLLISION-DATA ROOT CAUSE FIXED LOCALLY; AWAITING RELEASE

Richard acknowledged the 0.1.146 report on Discord ("spotted this and am investigating",
2026-08-03 20:26 UTC). Six releases later, canonical is **accelerated-wow 0.1.152**
(`cow_1acc54b8-80f9-4965-adb5-9325c0472619`, image `sha256:e479e11a…`). Retested with
**wowborg:v61** (`e3493732-4c72-4204-9e57-4976a1ce18c6`), rebuilt against 0.1.152's SDK.

- **The falling bug IS fixed.** Across all 84 observations z holds at exactly the spawn
  38.718 and never sinks — 0.1.146 fell to 28 / 18.6 and had `FALLING` on 100% of movement
  packets.
- **The character still cannot move.** The replay now contains **zero movement packets** —
  not one `MSG_MOVE_START_FORWARD`, where 0.1.146 at least emitted 175. 32 of 36 movement
  failures are a new gate: *"piloted movement controls settled: movement collision readiness
  timed out"*. Trajectory 0.0 yd, 1 distinct x/y. So the fix appears to have added a
  collision-readiness wait that never becomes satisfied.
- **Root cause found in the owner game.** The `/env` host applies the authenticated
  `/player/assets` URL as the presentation asset base, but unlike the normal player runtime
  it never applies that URL with `setSimulationDataBaseUrl`. Its `simulationDataHttp` build
  therefore cannot resolve the VMap collision data that movement waits for, matching the
  artifact's exact terminal reason: `world collision residency pending`. Local owner-repo
  commit `97f4d36c` (`codex/env-host-simulation-data`) installs the simulation-data base
  before client construction and adds the invariant to the complete environment-host asset
  proof. That proof passes, as do all 38 architecture-gate tests. The fix is local only: no
  branch push, PR, Coworld publication, or policy upload has occurred.
- **A second, separate defect: a startup race.** 1 of 2 hosted episodes failed
  `player_error` with WebSocket 1011 `environment session ended before hello`. Locally the
  same path dies deterministically (2/2) on a game assertion:
  `session.nim(310) httpAssetFetchesActive() == 0` in `finishEnvHostSessionStartup`.
- Hosted `xreq_03d44ab9-1e00-4ec5-9cce-522f17d5a601`: completed
  `ereq_7e785792-9895-4b3b-bb92-f2301ec84abe`, failed
  `ereq_e950ddfa-e04c-45cd-8d47-8577fee2d785`.
- **SDK break in 0.1.152:** `player/sdk/navmesh/__init__.py` stopped re-exporting, so
  `from player.sdk.navmesh import route_navmesh` fails; the import moved to
  `player.sdk.navmesh.client`. Fixed in `wowborg/environment.py`, `tools/build_player.sh`,
  `tools/route_lab.py`. 0.1.152 also adds chat observation fields, so older builds'
  `extra="forbid"` frame model would reject its frames.
- **Version numbering:** upload numbering follows the last *uploaded* version. The 2026-08-03
  local 0.1.146 rebuild was never uploaded and holds no number; `wowborg:v61` is the 0.1.152
  build.

**Next:** publish/review the owner-game fix, build a new accelerated-wow release, then rebuild
wowborg only if its copied SDK contract changes. Run the movement-continuity comparison and
the known + held-out navigation battery on that release. The `httpAssetFetchesActive`
assertion may share the asset-routing cause, but that is not yet proven; retain it as a
separate verification target.

---

## Status (2026-08-03): 0.1.146 DISPATCHES BUT THE CHARACTER CANNOT MOVE — game-side blocker

The accelerated-wow 0.1.146 retest ran. Episodes dispatch and complete (unlike 0.1.127),
but **the character never moves a single yard**, so the movement-continuity question the
retest was built to answer is still unanswered.

- Canonical target `accelerated-wow:0.1.146` = `cow_ff82f1c4-d1f5-4291-810e-039e67ac8173`,
  game image `sha256:ab5f989c…` (now pinned in `tools/versions.env`).
- **v59 was not runnable** and the plan to reuse it was not executable: its copied 0.1.124
  contract is `extra="forbid"`, and 0.1.146 adds a required top-level
  `queued_melee_spell_id` plus nested `units[].class_id` / new `spell_facts` fields, so every
  frame would be rejected exactly as on 0.1.127. **v60's `AgentFrame` JSON schema is
  byte-identical to 0.1.146's**, and v60 is documented behavior-identical to v59 — so v60 is
  the controlled comparison, and it is what ran.
- Hosted `xreq_45fa56c4-1b49-4f4c-9a08-f819cd9be62a` (wowborg:v60, `custom-fresh-start-10x`,
  2 episodes) — both **completed, score 1.0, replay retained, no errors**. Score 1.0 is
  `level_progress` for a level-1 character with 0 XP; it is NOT a success signal here.
- **Both episodes recorded exactly ONE distinct x/y position** for the whole session.
  Trajectory 0.0 yd vs the baseline's 1,315.8 yd. The character spawns at
  (-618.518, -4251.670, 38.718), falls to z≈28 (down to 18.6), and lands where the navmesh
  refuses it: *"no physically admissible source triangle was found near the client pose"*
  (33/34 of all movement failures). wowborg then casts the unstick spell 7355, the server
  returns it to spawn z, and it falls again — the z trace oscillates 38.7 → 28 → 38.7 for
  720 s. Movement failures rose 13 → 44/47 versus baseline.
- **ROOT CAUSE: the character never lands — it is permanently in the falling state.**
  `FALLING` (0x2000) is set on **175/175 and 157/157 = 100.0%** of both episodes' movement
  packets (many also `FALLINGFAR`), against **3.8%** in the v59 baseline. A falling character
  ignores forward input horizontally, which is exactly why x/y never changes while
  `MSG_MOVE_START_FORWARD` is still being sent. The chain: spawn pose is valid → never
  grounded → z drifts below the terrain → the navmesh refuses the pose → wowborg unsticks with
  7355 → server returns it to spawn z → it resumes falling. For 720 s.
- **The navmesh and the world data are innocent, both verified directly:**
  - `maps` / `vmaps` / `mmaps` tiles covering the spawn (map 1, grid 33/39-40) are
    **byte-identical** between 0.1.124 and 0.1.146 (same md5s, same sizes).
  - Querying 0.1.146's own `vmangos-navmesh-helper` at the spawn pose z=38.718 **plans a
    48-yard route with waypoints**; the identical query at z=27.988 and z=18.558 returns
    `no_path` / "no physically admissible source triangle". The mesh is right — the
    character's z is wrong.
- **This is game-side, not our SDK pin.** wowborg was rebuilt against 0.1.146's exact image
  (the unnumbered 2026-08-03 build — never uploaded, so it holds no `vN`; `wowborg:v61` is the
  later 0.1.152 build) and run as a full local exact-image episode: same spawn, same fall, **1 distinct x/y,
  0.0 trajectory yards**. Three episodes, two builds, hosted and local — one signature.
- Note the 0.1.146 image set is now **three images**: the Python adapter
  (`sha256:ab5f989c…`, packages under `/app`, no world data) and the VMaNGOS runtime
  (`sha256:38880c23…`) that carries `/vmangos-data` and `vmangos-navmesh-helper`. 0.1.124 was
  a single all-in-one. `tools/route_lab.sh` assumes the pinned image carries `/vmangos-data`,
  so it needs the runtime image, not the `versions.env` pin, on 0.1.146+.
- Build-contract change found while rebuilding: the game image now serves its Python
  packages from **`/app`**, not `/usr/local/lib/python3.11/dist-packages`. The Dockerfile
  COPY paths are updated; without that the build fails outright.
- New instrument: [`tools/movement_report.py`](tools/movement_report.py) scores movement
  continuity from a replay plus the policy's own trace. Validated against the v59 baseline —
  it reproduces every independently recorded figure (4,097 packets / 239 forward starts /
  243 stops / 326 turn starts / 356 turn stops / 2,907 heartbeats).

**Next:** this needs a game-side fix at the `custom-fresh-start-10x` spawn (character falls
below the walkable surface on 0.1.146). Report upstream with the three episode IDs; re-run the
movement-continuity comparison once a release lands where the character can walk. That 0.1.146
build was validated locally but **never uploaded** — rebuild against whatever release carries
the fix. (Superseded by the 2026-08-04 status above: 0.1.152 fixed this fall.)

---

## Status (2026-07-30): WOWBORG WORKS ON 0.1.124; NAV + LIVE PROGRESS PROVED

The current accelerated-wow release now ships the convenient Gymnasium interface the
lab previously expected to own. `wowborg` has been rewritten against that canonical
surface:

- `VanillaWowEnv.reset()` yields `AgentFrame`; policies submit canonical
  `AgentAction` values with synchronous `step()`.
- The game owns the WoW client, projection, action admission/execution, settlement,
  reconnects, and transport. Wowborg contains no client binary, mask adapter, or
  compatibility path.
- The deployed accelerated-wow 0.1.124 image
  (`sha256:ed11e79d...d173a`) and its source/image-set commit
  (`bda33bf9c321fa9a6f01398423c36c513b3db622`) are pinned in
  `tools/versions.env` and the root lockfile.
- Navigation uses the owner SDK's authenticated `/player/navigation` query while the
  policy loop uses `/env`. A read-only `/player` observer reports the canonical
  frames as live level/XP/displacement progress without owning gameplay actions,
  changing the policy's own time budget, or affecting station selection. The
  observer reserves the owner-standard 35-second teardown margin before the
  handed-off session deadline.
  The full wowborg test suite is the current focused gate; real-navmesh catalog and
  held-out course results belong in `wowborg/VERSION_LOG.md`.
- Hosted certification is complete for canonical Coworld
  `cow_4dedf501-86de-4457-b303-c552975501d9`. Versions through 0.1.123 had a
  game-side asset-base startup defect that closed `/env` before the first frame;
  0.1.124 fixes it and surfaces typed pre-session failures.
- V47 (`57583ca8-476e-430a-ad3b-bc7c33ce40d0`) completed two hosted 0.1.124
  episodes (`xreq_49d36c6a-b479-4246-bce3-acf975d2490f`) with replay and score
  1.0, proving `/env` startup. Both characters remained at spawn: 90/92 of 120
  outcomes were stale-frame rejections and reachability was 0/3 per episode.
- Current hypothesis: route planning crosses the game-wide action deadline; the SDK
  returns the rejected old frame, so wowborg resubmits stale IDs. The candidate
  consumes the host's next pushed frame on stale/deadline rejection, traces
  `frame_refresh`, and otherwise leaves navigation unchanged. V48 proved that
  `VanillaWowEnv.reset()` is not a reattachment API: both candidate episodes ended
  as player errors when reset opened a new lifecycle against the retained session.
  V50 proved the in-connection mechanism: both episodes completed, every refresh
  advanced the frame, the maximum stale run fell to one, and position diversity
  rose from one to 264/337. Its first station still failed because four replans
  expired during a repeatable ~20-second startup movement stall just as movement
  began. V52 reached the known `valley-gate`; the other episode activated the
  one-time retry on Sarkoth. V53 exposed multiple queued typed request errors
  before the current frame. V54 drained them and completed 2/2 hosted held-out
  episodes with score 1.0 and replay: both independently reached the never-before-used
  `novel-east-rise` coordinate (332.9s / 341.8s) and correctly failed the deliberately
  impossible `novel-high-air` target as unreachable. No version was submitted to a
  league. V55 (`94c46921-5c5d-4486-b780-1d1d31f43591`) is the pre-observer
  default-catalog artifact from the same proven source.
- V59 (`fc660a1d-2ec2-45d2-bf9a-e7725d8be246`) adds behavior-neutral `/player`
  participation: `/env` keeps the original policy budget and sole action ownership,
  while the observer reports live progress and sends `done` 35 seconds before its
  handoff deadline. Hosted request `xreq_50048077-8098-4ece-a725-460866e70ed4`
  completed 2/2 with score 1.0 and replay; both reported about 1,310 yards and
  retained about 4,100 movement packets. No version was submitted to a league.
- V60 (`99a2c257-bbad-4bb2-9eb5-1eefa8920f06`) is the same behavior rebuilt against
  accelerated-wow 0.1.127's strict `AgentFrame` SDK. A complete exact-image local episode passed
  with score 1.0, replay, 312 observations / 311 intents, and 1,391.080 trajectory yards. Versus
  the hosted v59 baseline, movement packets fell 4,097 -> 1,376 and forward start/stop pairs fell
  239/243 -> 22/25, proving PR #7391's continuation locally. Hosted request
  `xreq_d2255259-ee1b-4647-bc71-2ea93133ab54` never dispatched because 0.1.127 certification
  failed its 3,600-second smoke episode; packet-count validation waits for a corrected release.

The older status sections below are historical context. In particular, the 2026-07-27
decision to fork/re-open a Gym seam has been superseded by the owner's shipped `/env`.

---

## Older status (2026-07-13 - 2026-07-27): archived

Sessions 2 through 5j — lab creation, the v1-v45 waypoint/nav ladder, the 0.1.31 contract
migration, and the 2026-07-27 upstream contract rewrite — are in
[`docs/status-archive.md`](docs/status-archive.md). All stale; consult only for history.

## Key facts (the hard-won ones — full detail in the docs)

- **Two game shapes** (docs/vanilla-wow-gameplay.md "Two game shapes"): a **persistent realm**
  (ranked by an account's highest-XP character, `highest_character_total_xp`) and **isolated
  scored episodes** (disposable servers from a signed `CWROSTER` 5-character snapshot; nothing
  writes back). Keep them distinct.
- **The scored benchmark is `rfc-five-player-clear`**: one policy fills **all five slots**
  (`self_play=True`), a level-30 Horde party (warrior tank / priest healer / shaman / rogue /
  mage) clears Ragefire Chasm (map 389), four bosses (Oggleflint 11517, Taragaman 11520,
  Jergosh 11518, Bazzalan 11519).
- **Round score = clear-then-speed:** full clear → `max(1.0, 1_000_000 − clear_seconds)`;
  partial → `bosses_defeated / bosses_total` (< 1.0). Every clear beats every partial; among
  clears, fastest wins. **Cross the full-clear threshold before optimizing time.**
- **7200 is NOT the episode deadline** — it's `DUNGEON_LAB_RESPAWN_SECONDS`, the boss-respawn
  timer that keeps a killed boss readable as dead. The episode budget is `max_ticks/tick_rate`
  (RFC: 10000/0.1). Be precise when writing about time.
- **The player is Nim, packet-level** (King Nimrod, headless `-d:noGui`), connects via a
  WebSocket→TCP bridge (`wsproxy`), and must obey **"sent is not accepted"** (confirm every
  action from `action-results.jsonl` / typed state transition; no teleport / injection /
  synthetic state / DB repair after login).
- **Only 7 of 9 classes are seedable** (Horde-only seeding; **paladin** Alliance-unreachable,
  **druid** unseeded). Class rotations exist for those same 7 (`player/bots/rotations.nim`).
- **No `-100` failure sentinel** (that's Crewrift). Detect player failure via episode status;
  read a low completed-episode score as a gameplay signal.

## Open threads (next steps)

1. **Blocked on the game, not on us.** wowborg cannot move on `accelerated-wow` 0.1.152.
   Two defects to report to Richard Higgins (Discord `relh.net` — see the memory note; the
   `discord.send-message` skill lives in the metta checkout, not this repo):
   - *"piloted movement controls settled: movement collision readiness timed out"* — 32/36
     movement failures, zero movement packets emitted.
   - `session.nim(310) httpAssetFetchesActive() == 0` in `finishEnvHostSessionStartup` —
     killed 1 of 2 hosted episodes; reproduces deterministically locally (2/2).
2. **Then finish the movement-continuity retest** that has been pending since 0.1.127:
   compare a fresh episode against baseline `ereq_422085f1-9ec7-4554-b2ba-9942947e5dc2`
   with `tools/movement_report.py --baseline`. Baseline figures: 4,097 movement packets,
   239 forward starts, 243 stops, 326 turn starts, 356 turn stops, 2,907 heartbeats,
   1,315.8 replay yd. The open question is whether the environment-owned forward
   continuation (game PR #7391) holds hosted, as it did locally on 0.1.127.
3. **`tools/route_lab.sh` is stale for 0.1.146+.** It assumes the `versions.env` image
   carries `/vmangos-data`, but the release now splits into a Python adapter image (no world
   data) and a separate VMaNGOS runtime image. Point it at the runtime image before relying
   on it.
4. **Spell 7355 cooldown spam** remains an unaddressed wowborg issue, separate from all of
   the above.

## Reference

- Game repo (reference only): `~/coding/coworlds/coworld-vanilla-wow` — Python adapter
  `src/vanilla_wow_coworld/`, Nim player `player/`, dungeons `dungeons/`, manifest
  `coworld_manifest_template.json`. **Read-only for us; pull before relying on it.**
- Design doc for this lab's creation: `../docs/superpowers/specs/2026-07-13-vanilla-wow-lab-design.md`.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back) — and
here, doubly gated behind the game even being live.
