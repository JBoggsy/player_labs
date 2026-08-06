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

## Status (2026-08-05): TRAVERSE STRATEGY LAYER BUILDS AGAINST THE CERTIFIED WORLD

Wowborg now separates competition objectives from shared navigation/recovery. The image
bakes exactly one objective with `tools/build_player.sh --strategy NAME`; the only current
registry entry is `traverse`, selected by `WOWBORG_STRATEGY=traverse` in that immutable
version. Traverse uses Prowl through its early hostile bypass and Travel Form afterward,
follows an explicit competition route when one is available, and falls back to the safest
untried local northbound frontier. It records
authoritative northing and every route/frontier activation in the trace.

- Canonical target is **traverse-wow 0.1.160**
  (`cow_3eca82b6-2ad7-476b-88af-832d1faa666d`, image `sha256:bc2aec5696…`). Its SDK source
  pin is `b11cbac8a50e9a019848f4001c54f834e22c340b`.
- The 0.1.160 image publishes its Python contract from `/opt/coworld-python`, replacing the
  previous `/app` build path. Wowborg's real amd64 image build and `/env` + `/player` import
  verification pass with that layout.
- The original focused wowborg suite passed (67 tests), but the uploaded inert
  **wowborg:v62** (`b2f6f022-90a9-48b2-a5ac-cd37464046ec`) failed its hosted canary before
  parsing the first frame and must not be submitted.

Hosted request `xreq_9b9bd8b7-45c3-4bf9-af54-d62c0cac6cbb`
(`ereq_0bae0bd3-2fcc-4942-9475-257aa7e30200`) exposed an owner-contract mismatch: the
0.1.160 host emits spell intents `threat` and `threat_reduction`, while the exact packaged
`AgentFrame` has an older closed Literal that rejects them. The adjacent owner client model
and current producer use an open string vocabulary. A local compatibility candidate widens
only `SpellObservation.intent_names` to `list[str]`; 68 tests and the real amd64 build pass.

The compatibility candidate is uploaded as **wowborg:v63**
(`7b3e2eb7-9b3f-47a7-b096-7217fc2daa06`). Hosted canary
`xreq_17763e42-3a8f-4cca-9ea1-d1172ebde234` completed beyond v62's failure boundary,
scoring **1,959.23 northing (12.34%)**. It died twice and spent about 1,574 seconds—59% of
strategy time—recovering corpses; its replay traveled 8,707.5 yards for only 1,959.23 net
northing. Submission `sub_941c5190-13a5-4ca5-93b1-d0bba19d8b19` placed it immediately as
active competing membership `lpm_059413b3-fa38-4c8f-b218-8521406d24a2`, now marked as
James's champion version. Its first
official run, round 142 (`round_d1a45aeb-00d6-4fce-bb53-06f066f2ad56`), scored
**1,776.98 northing**, fifth of seven in the round and sixth on the division leaderboard
after one round; `reached_goal=false`. Round 143
(`round_36c2f641-d101-425b-aa3d-6c2ef7f9db03`) scored **1,308.52**, fifth of eight;
the retained leaderboard score remains 1,776.98 and wowborg is rank 7 after two rounds.
Round 144 (`round_6061ea14-fdb6-4ab5-bec2-36085a7f8b6a`) scored **1,357.49**,
sixth of seven scored entrants; the retained best and rank remain unchanged after three rounds.
No round-143 or round-144 entrant reached the goal.

Round 145 (`round_97932121-2e61-47b0-8aaa-0eeb27d5774b`) improved v63's retained best to
**1,834.47**, sixth of nine, but `reached_goal=false`. Round 146
(`round_5c914794-356e-4433-81f1-31958799a10d`) scored **1,624.98**, sixth in the round.
Round 149 raised v63's retained best to **2,169.13**, fourth in that round. Rounds 150-152
scored 1,700.15, 1,789.51, and 1,752.34; none reached the goal. The division leaderboard
ranks wowborg 8 with 2,169.13 after ten scored rounds, and round 153 is running. Round 148
failed before play because a Kubernetes pod remained `PodInitializing`; it was an infra round
failure, not a policy disqualification.

Three independent optimization reads agree on the first attributable change: maintain Druid
Travel Form (spell 783) during navigation. The owner reference policy activates it, and rank-1
`wow-walker:v24` casts 783 at startup and again after losing it while moving at roughly
9.8-9.9 yd/s. The local candidate adds only a traced pre-frontier activation/reacquisition;
69 tests pass.

The Travel Form candidate is uploaded inert as **wowborg:v64**
(`b7a35d49-d39c-4cd8-aa06-d6562d0f4037`). Matched request
`xreq_422da653-5c3f-45dc-a5e5-804ad77757a0` (`ereq_6b3a8f57-bcd1-4187-89cb-12b4f3dcd184`)
completed against the exact v63 world/variant with **1,740.77 northing (10.97%)**, below
v63's 1,959.23 hosted baseline. Replay confirms spell 783 casts at 8.0s and 1,293.7s, but the
faster policy reached the lethal greedy corridor sooner: deaths at 239.0s, 1,339.9s, and
2,508.3s. It traveled 11,098 yards yet finished at `world_x=-7446.23`.

The owner repository is current at `a7e26edce`; that commit replaces its own failed greedy
Traverse frontier with shared semantic world travel. **wowborg:v66**
(`415de479-47fe-4bd0-877a-1238a29ebd96`) ports only its 23-edge smooth
Tanaris/Thousand Needles prefix through the Great Lift lower dock, retaining the existing
adaptive fallback. It was built from `b2e58e4`, uploaded inert, and is not submitted; 72 tests
pass. v65 contained the same image but incorrectly overrode its working `python3 -m wowborg`
image command with `python -m wowborg.main`; that module defines but does not invoke `main()`,
so two hosted jobs never connected. Request `xreq_32a6f4d3-3ba0-48d1-a64d-b460fd6ed3e2`
was cancelled, and v66 restores the image default command. Exact 0.1.160 Detour measurements
show a complete route can cover about 19,431 ground yards excluding the lift, or 33:03 at
Travel Form speed, leaving almost 12 minutes for lift/control/combat.

v66 request `xreq_288ca227-6bcc-44a9-8a5d-92ca4cb60ca6` completed with **1,806.38
northing (11.38%)** and `reached_goal=false`. Its trace attempted eight guidepoints, arrived
at seven, and recorded no typed route failure, but two deaths after aggro by Scorpid
Dunestalker near `(-9025,-2690)` and Glasshide Gazer near `(-8170,-3326)` consumed 1,568
seconds. A third hostile contact near guidepoint 8 left it alive but damaged at timeout. The next isolated
candidate replaces all 23 populated-road guidepoints with the exact-0.1.160-Detour-proven
east bypass `(-8033.689,-2283.733,23.1)` → `(-6960.3,-3739.2,46.1)` → Great Lift lower
dock. It stays 164 and 716 yards from the two death sites; hosted evaluation must establish
whether it avoids other mobs. v62, v64, v65, and v66 remain unsubmitted.

The east-bypass candidate is uploaded inert as **wowborg:v67**
(`a59a5117-1678-4c80-894d-c44a180c4052`) from source `cee622a`. Matched hosted request
`xreq_3293f9ba-ad00-4fdd-aefa-f71617e590a7` completed with **1,300.82 northing
(8.19%)** and `reached_goal=false`, regressing 505.56 from v66. It reached only the first
guidepoint, then failed the Tanaris-entry leg with `no_progress`; two deaths consumed 1,741
seconds (65.3% of the episode). The Great Lift was never attempted. The apparent replay
maximum near `world_x=-7191` was a ghost cemetery position; authoritative final and maximum
living x were both `-7886.18`.

Exact 0.1.160 Detour planning proves a direct spawn-to-lower-dock route in 13 continuation
chunks and 5,673.4 yards. It is 1,031.1 yards shorter than v67 and crosses 15 static hostile
detection ranges instead of 49 (69% fewer), though nine Centipaar Wasps remain a real risk.
The next candidate changes the prefix to this one semantic target only.

The direct-dock candidate is uploaded inert as **wowborg:v68**
(`bb7f59cc-a684-4ab4-b485-7071170502d1`) from source `fa083a6`. Matched hosted request
`xreq_3864dc6e-0e6f-45bd-8bae-fc9f3529da5a` was cancelled before gameplay after the
expanded hazard audit found the direct polyline passes 2.3 yards from an active Centipaar
Wasp and 11.6 yards from v67's fatal Wasp onset. It produced zero completed episodes and no
performance evidence. A named-coordinate bypass was also rejected after the full spawn
snapshot exposed six different Wasps and two Workers, including one Wasp 0.34 yards away.

The next candidate uses four exact bypass guidepoints before the dock. Its 5,995.5-yard,
17-chunk exact Detour proof clears both v67 Silithid coordinates by at least 41 yards and
crosses zero static or conservative-wander encounters across all 112 active Centipaar
Wasp/Worker spawns. Eight other static hostile exposures remain, down from direct's 15.

The full Centipaar-bypass candidate is uploaded inert as **wowborg:v69**
(`69885bb8-34f4-4e7c-9d90-56e6d91edd71`) from source `61a8e84`. Matched hosted request
`xreq_e1288518-2403-460e-8a5a-12a43c02bfee` completed with **662.68 northing (4.17%)**
and `reached_goal=false`. It attempted only the first guidepoint, arrived at none, and failed
`no_progress`; two deaths consumed 2,193 seconds (82.3% of the episode). Rabid Blisterpaw
plus Glasshide Petrifier caused the first death, and another Rabid Blisterpaw caused the
second. The Great Lift was never attempted. Route-only avoidance is not enough: remaining
early hostiles kill wowborg before it reaches the protected corridor.

**Next:** add one attributable survival capability for the unavoidable early hostile band;
the leading owner-supported option is Druid Cat Form plus Prowl. Re-evaluate the v69 route
before any Great Lift work.

The stealth candidate is uploaded inert as **wowborg:v70**
(`c330d793-586b-4cc6-a7ec-0c15a1109ab2`) from source `d072d11`. It enters Cat Form and
Prowl through the four early bypass guidepoints, then restores Travel Form for the dock leg.
Matched hosted request `xreq_36167fe8-b19a-4989-b634-c332c5d908bf` completed valid with a
reported **1,751.51 score (11.03%)** and `reached_goal=false`, but that score includes a
graveyard teleport and ghost movement: maximum living x was only `-8423.30` (763.70 yards,
4.81%). Cat Form and Prowl rank 1 both settled successfully at startup. Prowl was lost at the
first hostile detection and never reacquired because the first `navigate_to` call occupied the
rest of the episode. It reached zero guidepoints; three deaths consumed 2,220 seconds (83.3%).

The safe-resume candidate is uploaded inert as **wowborg:v71**
(`d5960580-8056-4026-b2a8-f79f3799f896`) from source `fe11437`. It adds a game-agnostic
callback at `RouteNavigator`'s verified living, out-of-combat resume seams and uses it to
reacquire the existing traced Prowl after combat ends or corpse recovery completes during the
first four guidepoints. Matched request `xreq_2604d7d8-8d51-489f-b310-d9017b83bd42` is
complete with **1,139.61 northing (7.18%)** and `reached_goal=false`. The prediction passed:
Prowl activated successfully after both corpse recoveries (three successful activations total),
deaths fell from three to two, dead/ghost time fell from 2,219.6 to 2,003.6 seconds, and maximum
living x improved from `-8423.30` to `-8047.39`. It reached the first bypass guidepoint for the
first time, but only after 2,570.5 seconds; the two avoidable deaths and roughly 1,000-second
corpse runs still consumed most of the episode. The first fight began with Prowl already active.
The next isolated survival capability is therefore exact-attacker melee engagement during the
existing combat pause, retaining flee/wait when the typed frame cannot identify the attacker.

That candidate is uploaded inert as **wowborg:v72**
(`c6e67ab5-cbe3-4e1e-8970-8be5e27d2638`) from source `c0cc241`. Traverse now resolves only a
typed active attacker (current auto-attack, visible recent damage source, or a live visible unit
targeting wowborg), faces and starts melee within five yards, and holds the swing. The old flee/wait
path remains unchanged when no exact adjacent attacker is available. Activation traces record the
target GUID, face/attack settlement, and cumulative outgoing damage. Canonical 10x request
`xreq_90ef6893-552c-4f08-8360-1c1c299203ca` is streaming on `traverse-wow 0.1.164` with the
resolved v72 UUID. A combat-free run leaves the mechanism unevaluated. Mechanism success requires
actual outgoing damage; behavioral success requires zero deaths before guidepoint one, arrival
there before 600 seconds, and maximum living x beyond v71's `-8047.39`.

---

## Status (2026-08-04): LOCAL NAVIGATION BATTERIES PASS; OWNER FIX LANDED

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
- **Root cause found and fixed locally in the owner game.** The `/env` host applies the authenticated
  `/player/assets` URL as the presentation asset base, but unlike the normal player runtime
  it never applies that URL with `setSimulationDataBaseUrl`. Its `simulationDataHttp` build
  therefore cannot resolve the VMap collision data that movement waits for, matching the
  artifact's exact terminal reason: `world collision residency pending`. Local owner-repo
  commit `1608da7a` installs the simulation-data base
  before client construction and adds the invariant to the complete environment-host asset
  proof. That proof passes, as do all 38 architecture-gate tests. The same patch removes the
  startup assertion that required the shared HTTP fetch pool to be empty: once collision
  routing works, world entry legitimately leaves two authenticated collision requests in
  flight. The host already reports that count in hello, while movement readiness gates the
  collision data it actually needs. Richard Higgins merged owner-repo
  [PR #7809](https://github.com/Metta-AI/coworld-vanilla-wow/pull/7809) after both CI checks
  passed; the landed squash has the same stable patch ID as the simplified topic commit. No
  Coworld publication has occurred.
- **Exact local end-to-end proof passes.** A disposable derivative of the 0.1.152 runtime,
  containing only the patched environment host, completed with the owner HEAD SDK. Unchanged
  wowborg:v61 held spawn height, emitted movement, traversed 115.2 yards with zero falls, and
  exited cleanly in a deliberately short 180-second episode.
- **Known + held-out navigation batteries pass locally.** A focused wowborg candidate no
  longer treats already-pushed frames with no observed action result as movement stalls.
  The known course reached 2/2 reachable targets and rejected 1/1 impossible target with
  zero replans; its replay shows 165.3 yards and exactly one uninterrupted forward span per
  journey. A data-only coordinate absent from the repository (`-500,-4300,46`) was reached
  in one 121.8-yard forward span, while the matching high-air target was rejected; again,
  zero replans and zero falls. The candidate is local only and not uploaded.
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

**Next:** build a new accelerated-wow release from landed owner-game PR #7809, then rebuild
and upload the candidate against that release's exact SDK. Run the known + held-out battery
hosted and finish the pending long movement-continuity comparison against the v59 baseline.

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

1. **Release the landed owner-game fix.** Commit `1608da7a` routes authenticated
   simulation data and removes the invalid zero-active-fetch startup assertion. Focused Nim,
   architecture, scope, and exact local episode proofs pass. Richard Higgins merged owner-repo
   PR #7809 with both CI checks green; it still needs a released accelerated-wow build before
   hosted wowborg can move.
2. **Then finish the hosted movement-continuity retest** that has been pending since 0.1.127:
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
