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

## Status (2026-08-08): VANILLA-WOW 0.1.208 REMOVES ENVIRONMENT MOVEMENT CHURN

Canonical **vanilla-wow 0.1.208**
(`cow_2e0459a4-0b66-492c-9799-0cc6ec0e8876`, image
`sha256:f950683bd15014e0fd9be0c4226d70474fe05a0b09fe09b2a55fb0c351dfd3e4`)
contains owner commit `b92f4961c97cc918b7e46e2c39db778f01df2487`. Compatible destination
moves now retain forward input across observation horizons and route turns; collision-avoidance
bearings remain selected until faced instead of collapsing into one-frame turn pulses. The host
also retains typed action and movement lifecycle telemetry in the combined game log.

The unchanged uploaded **wowborg:v88** (`3f955f79-6404-4d51-8efe-c04675d22926`, source
`cbbbee0`) is the control. Owner acceptance request
`xreq_c0649f44-ecca-4f82-bc2a-e1cdf95684b1` completed 5/5 over 17,308.7 trajectory yards
with zero nonterminal stops, stalls, rejections, detached frames, or direct turn reversals.
Its 11 turns lasting at most 100 ms are a 98.5% reduction from the 0.1.207 canary, and none
has the former same-waypoint route-bearing disappearance signature. Three stop/restart pairs
are terminal scoring/logout artifacts after the character is already a ghost, not movement
churn. Wowborg itself was unchanged and remains unsubmitted at v88.

Independent lab request `xreq_cb6f96ae-00d0-40ab-b5a5-d10cb46248e0` reproduced the
acceptance 5/5 with mean score 1,607.572 across 17,352.720 trajectory yards. It has zero
active nonterminal stops, host stalls/rejections/detached frames, stale-frame rejections,
direct reversals, or old bearing-disappearance signatures. Ten turns last at most 100 ms;
the four raw stop/restart pairs split into two death/ghost transitions and two final
scoring/logout artifacts rather than traversal churn.

The lab source dependency and exact environment-image pin now match 0.1.208. Use
`tools/movement_report.py EPISODE_DIR --json` on downloaded experience-request artifacts;
with `game_logs.log` present it reports nonterminal versus terminal stops, host counters,
short turns, direct reversals, and the former bearing-disappearance signature.

Local engineering cleanup is complete. BuildKit's 658.6 MB of disposable cache was reclaimed
without deleting shared images or volumes. `tools/route_lab.sh` again executes the real pinned
0.1.208 navmesh after adopting the current `environment.contract.policy.WorldPoint` import.
Wowborg now suppresses spell 7355 while the authoritative frame lists it on cooldown, emits a
`stuck_skipped` trace, and uses the existing wait fallback instead of submitting another cast.
That behavior is uploaded inert as **wowborg:v89**
(`18b5df77-d270-4f43-a168-2b4a8d389255`, source `a5c9c01`); v78 remains the submitted
Traverse champion.

## Historical status (2026-08-06): V78 SUBMITTED AND QUALIFYING ON THE CORRECTED CLOCK

Inert **wowborg:v75** (`c75e24cc-166f-43df-9d52-d77724cc4b16`, source `aed90c9`)
adds the required Great Lift transition after the lower-dock route.
It selects only visible platform entries 11898/11899 at lower-dock height, turns and walks onto
the platform through bounded `move_vector` ordinary-client input, waits after authoritative
`on_transport`, and walks toward the upper dock only above z=80 before resuming navmesh travel
at the upper road. It does not inject coordinates, bridge the disconnected navmesh, teleport,
or manipulate death. All 39 focused lift/environment/navigation checks pass; hosted proof is
still required.

v75 hosted request `xreq_f658f8de-ab1c-44a9-ae11-f12fb3e48478` completed with **1,764.21
northing** and `reached_goal=false`. It traveled 2,807.5 yards and ended on the normal Tanaris
road chain at `(-7422.79,-3726.72,10.16)`, never reaching the lift. The stateful owned-replay
reducer found one death, but the replay contains only the startup Travel Form cast. The active
v76 source candidate therefore changes only the route's existing safe-resume callback to
reacquire Travel Form after combat or revival; route and lift behavior are unchanged. This is
uploaded inert as **wowborg:v76** (`5a13f3cf-89d0-4f52-a8b8-ea6a7668021f`, source
`d3216d7`) and awaits current-format hosted proof.

Independent stateful replay inspection corrected the causal read: v75 retained Travel Form at
9.8 yd/s until a Scorpid Dunestalker killed it near `(-9050,-2508)`, then never revived; its
headline score was ghost/graveyard-derived. The still-pending v76 request
`xreq_5d974b37-303d-4175-b218-9c59d9b0d329` was cancelled before dispatch because its
safe-resume callback would not execute. A proposed owner-authored
`tanaris-north-road-1` leg was rejected before commit/upload: it clears the fatal Scorpid but
the full pinned-spawn audit increases conservative hostile-envelope intersections from 17 to
18 and introduces 11 contacts, several within 3.7-6.8 yards. The next route change must use a
multi-point ordinary-Detour corridor proven against the full pinned spawn set.

The prior candidate is uploaded inert as **wowborg:v77**
(`e9cfde9d-5ac5-41a2-ac56-0977de5401b5`, source `4217916`) and awaits current-format hosted
proof. v63 remains the only submitted league version.

v77 request `xreq_227bf53a-a8f3-42a0-bc00-1a367d5b9457` falsified its 48-spawn audit. It died before
GP1 completed at maximum living `x=-9056.248`; the 1,752.34 headline was ghost-derived. A
Rabid Blisterpaw (entry 5427, GUID 22586) had been omitted because the prior 48-row audit was
route-local, not regional. The correct region contains 136 pinned hostile rows, and v77's exact
route crosses seven conservative envelopes.

**wowborg:v78** (`36f3f0bf-2261-42ec-9d8a-4a084e145b81`, source `3e95dcb`)
replaces only that opening with eight ordinary-navmesh guidepoints,
then rejoins the existing first Centipaar bypass. Its exact chained Detour route is 2,122.1609
yards and crosses zero conservative envelopes across all 136 regional hostile rows; the
tightest margin is +0.226 yards. Combat, recovery, the later route, and normal lift boarding
remain unchanged.

The canonical league Coworld is now **traverse-wow 0.1.174**
(`cow_dc024af2-7f05-4ee1-bd33-99103175cde0`), with the corrected 10x gameplay clock.
Hosted canary `xreq_e984c401-f498-449d-8aa6-77cad0e1912b` completed 1/1 with no policy or
infrastructure failure, scoring **1,304.14 northing**. Its ordinary-access replay records
1,114 client movement packets, 3,746.6 yards of trajectory, zero falling packets, and a normal
Travel Form cast. No policy-log artifact was exposed at ordinary permissions, so lifecycle
timing is unavailable; the authoritative northing and replay nevertheless prove genuine
world movement rather than a connect-only completion.

With the human's explicit gate, submission `sub_6c5e6403-d23f-4296-8ee9-3f4dee8b2477`
placed v78 as membership `lpm_67027432-7d93-40ba-9f3c-8ed632f83735`. It subsequently
qualified and is now the active champion; v63 is benched.

Behavior-neutral **wowborg:v80** (`db6faec7-451a-483f-b65d-db2b3f80fded`, source
`917e83a`) is uploaded inert against the exact active 0.1.174 environment contract; v79 failed
at startup on a stale navmesh import and was superseded. v80's trace records frame
receipt-to-action latency, `/env` step round-trip, submitted/returned frame IDs, raw status,
stale refresh, and locally skipped actions. In hosted request
`xreq_75c86237-6b7a-4a3a-abe3-cb4b9fd65687`, all five runs completed and Wowborg eventually
submitted on every one of 2,561 unique offered frames. Normal response is extremely prompt
(0.548 ms median, 0.810 ms p95), but each run has exactly three synchronous nav operations over
the default five-second deadline: initial planning, frontier replanning after opening no-progress, and
ghost recovery planning. The 15 pauses span 7.63-17.23 seconds and are followed by all 15
stale-frame rejections. They are real policy-caused silence windows that satisfy the documented
stall trigger, but are not the primary cause of
the pervasive choppiness: the five replays contain 717 forward stops and 707 boundary-only
stops, while only 38 raw stops occur in the coarse wall-clock windows of those slow responses.
At that time, the host's exact `action_stall` count and continuation retain/release reason were
owner-only and required environment telemetry rather than policy inference. v80 is not submitted; v78 remains
the active champion.

The canonical owner replay reducer now makes the retained replay a complete causal diagnostic
surface for movement/stalls, damage and death locations, life-state time, recovery controls,
combat, spell outcomes, and form/aura evidence. `tools/wow_batch_profiler.py` aggregates those
facts without duplicating packet-state reduction. Across rounds 323-325 (two v63, one v78), all
three runs ended ghosted after one death, spent 4,852.6 seconds total in ghost form (68.9%),
dealt zero damage with zero attack packets, and recorded five clustered stuck episodes from 15
Stuck invocations. The damage sources were one Scorpid Dunestalker, one Rabid Blisterpaw, and
one Glasshide Petrifier. Recovery, not route geometry alone, is the shared primary failure.

The full historical profile now covers 129 unique playable replays (one exact duplicate
removed), including 113 current Tanaris Traverse runs from v63–v78. In that current family,
121 deaths and 88.6% of all incoming damage concentrate in four adjacent opening cells along
y≈-2500; 107/113 runs ended ghosted and ghost time is 60.9%. All six v78 replays died and
ended ghosted, five near x≈-9100 and one near x≈-9308, with Glasshide Petrifier as the final
damage source. See
[`docs/wowborg-history-profile-2026-08-06.md`](docs/wowborg-history-profile-2026-08-06.md).

A preregistered six-replay v78 smoothness audit localizes the visible choppiness below waypoint
strategy. The authoritative outbound wire has 591 effective stop-to-restart intervals: 478
without an intervening turn (156 lasting at least 0.5 simulation seconds), 109 with explicit
turn controls (median 4.0 seconds; 81 at least 3 seconds), and four with other controls. `/env`'s
pilot explicitly stops forward for heading errors above 45 degrees, matching the stationary
avatar/rotating-terrain presentation; the viewer interpolates the recorded wire and therefore
exposes rather than invents it. See
[`docs/smooth-movement-root-cause-preregistration-2026-08-06.md`](docs/smooth-movement-root-cause-preregistration-2026-08-06.md).

Speed-first **wowborg:v74** (`621ee466-2caf-4325-881d-0ba483dc1bfd`, source `d421042`)
completed current-format request `xreq_3bad8628-4872-4422-a805-41f74ac3c256` on
`traverse-wow 0.1.166` with **1,797.73 northing** and `reached_goal=false`. It failed the
preregistered 2,000-yard floor and did not reach the lift. Ordinary-permission artifact fetch
returned the replay but no owned trace/results/log artifact. v63 remains the only submitted
league version; v74 and the lift candidate are inert.

## Earlier status: TRAVERSE STRATEGY LAYER BUILDS AGAINST THE CERTIFIED WORLD

Wowborg now separates competition objectives from shared navigation/recovery. The image
bakes exactly one objective with `tools/build_player.sh --strategy NAME`; the only current
registry entry is `traverse`, selected by `WOWBORG_STRATEGY=traverse` in that immutable
version. Traverse uses Prowl through its early hostile bypass and Travel Form afterward,
follows an explicit competition route when one is available, and falls back to the safest
untried local northbound frontier. It records
authoritative northing and every route/frontier activation in the trace.

- At that point the canonical target was **traverse-wow 0.1.160**
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
`xreq_90ef6893-552c-4f08-8360-1c1c299203ca` completed on `traverse-wow 0.1.164` in about
4.5 wall-clock minutes with **1,860.96 northing** and `reached_goal=false`, but the score was
ghost-derived rather than an improvement. The only living advance reached `x=-8905.77`; wowborg
died at 154.8 simulation seconds before reaching any guidepoint, then spent the remaining 80.3
wall-clock seconds as a ghost. The mechanism resolved the exact attacker and started auto-attack,
but its face action failed while the authoritative frame reported movement unavailable. Across 335
hold observations it dealt zero outgoing damage, so the pre-registered mechanism and behavioral
criteria both failed. The next isolated correction is to start the valid exact-target attack while
movement is unavailable and defer facing until the frame reports movement authority restored.
Replay inspection refined the root cause: a Glasshide Petrifier landed Petrify while the local
mover was still applying its generic run-through/stall policy, including an unnecessary Stuck
attempt, so the first face came too late. **wowborg:v73**
(`45f04501-7e76-4511-a9b7-892b421cc607`) is uploaded inert from `351126e`. Only Traverse's
existing `engage_attackers` flag now makes the local mover surface the first combat frame before
stall handling; other strategies retain healthy run-through behavior. If control is already
blocked, it attacks the exact target and retries face when movement authority returns. Canonical
10x request `xreq_0be069a7-204b-47a9-a39d-be483e820180` completed with **408.57 northing** and
`reached_goal=false`. That score is
not comparable to normal Traverse because the scaled episode clock outran ordinary locomotion,
but the targeted capability passed: the first hostile frame surfaced before any Stuck action,
three exact attackers were faced and attacked successfully, wowborg dealt 7,695 damage, killed all
three, and had zero deaths. Full-duration matched request
`xreq_c317e459-ee91-4bab-a0fb-b789f2709bed` was cancelled after live league inspection proved
0.1.160's 45-wall-minute format is obsolete. The league now runs the same 270-wall-second 10x
format as the v73 mechanism request, so a long-fixture result would not guide the current goal.

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

The then-current accelerated-wow 0.1.124 release shipped the convenient Gymnasium interface the
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
- **Wowborg is a synchronous Python semantic player.** It consumes the game's typed
  `Observation`, submits one `Action` over the injected `/player` session, and consumes the
  next authoritative frame. The game owns the Nim packet client, projection, admission,
  execution, settlement, and reconnects. **Submission is not success**; use typed outcomes and
  observed state, never a second client or synthetic state.
- **Only 7 of 9 classes are seedable** (Horde-only seeding; **paladin** Alliance-unreachable,
  **druid** unseeded). Class rotations exist for those same 7 (`player/bots/rotations.nim`).
- **No `-100` failure sentinel** (that's Crewrift). Detect player failure via episode status;
  read a low completed-episode score as a gameplay signal.

## Open threads (next steps)

1. **Return to the death cells with a reusable navigation model, not another exact script.**
   Movement continuity is closed: unchanged v88 has zero active nonterminal stops on two
   independent five-run 0.1.208 batches. The current-family replay profile localizes 106/121
   deaths and 88.6% of incoming damage to four adjacent opening cells. The next human-led
   choice is the capability model for travel between waypoints—hazard-aware routing around,
   deliberate combat through, or stealth/travel-form passage—so the same intelligence applies
   to later danger rather than encoding this one corridor.

## Reference

- Game repo (reference only): `~/coding/coworlds/coworld-vanilla-wow` — Python adapter,
  semantic environment, owner replay reducer, Nim runtime/client, dungeons, and manifests.
  **Read-only for us; fetch/pull before relying on it.** Current verified movement source:
  `b92f4961c97cc918b7e46e2c39db778f01df2487`.
- Design doc for this lab's creation: `../docs/superpowers/specs/2026-07-13-vanilla-wow-lab-design.md`.

## Discipline (from [`../AGENTS.md`](../AGENTS.md))

Human sets strategic direction; you build observability, measure, hold the correctness gate.
**Propose-and-pause.** Change one component per iteration. Uploading is routine/ungated;
**league submission is the human's gate** (public, champion-making, hard to roll back).
Wowborg v78 remains the submitted champion; v88 is an inert evaluation control.
