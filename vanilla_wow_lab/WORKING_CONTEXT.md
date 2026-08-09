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

## Status (2026-08-08): V106 RESTORES THE LIVE 0.1.209 CONTRACT

Canonical **vanilla-wow 0.1.209**
(`cow_e3f61cb2-fe38-43e9-a10c-cdd12769f797`, image
`sha256:2c06427e2a96ab96f3ba19fedb6049c2eab30e463c167e27fb6781c415f25dfa`)
added `Unit.sub_name` and four quest-reward fields to `Observation`. V105 request
`xreq_9e058bae-fea0-4824-9045-13333b28a992` therefore failed contract validation before
movement and provides no router evidence. The environment pin now matches 0.1.209, and the
unchanged v105 router is uploaded inert as **wowborg:v106**
(`ec727f01-fbe8-45e9-b1c7-b129c3d2c54a`). Request
`xreq_7d385999-abc3-4231-8b78-c5bb21a2bc2f` cleared the measured gates and reached road
node 4, then exposed endpoint-only scoring: a Rabid Blisterpaw avoidance moved south into an
unselected Scorpid Dunestalker at 3.2 yards, and rapid left/right switches made the response
unstable. The source candidate now tracks hostiles to 80 yards, scores player and hostile
movement segments, ends avoidance when the projected forward corridor clears, and switches only
when retained clearance falls below 15 yards. Activation traces include both side scores and all
tracked destinations. V78 remains the submitted Traverse champion.
That candidate is uploaded inert as **wowborg:v107**
(`d7f5fe7d-3d99-4924-88a1-e78865dcc3fd`, source `d33799e`). Request
`xreq_3a8dc2f1-fdae-4bb5-81a8-1936f01ae2d2` survived the earlier cluster and reached
10 guidepoints / 1,684.8 living northing yards. At road node 7, `_steer_road_leg` returned while
avoidance was active for a Starving Blisterpaw 46.9 yards away; the next leg reset the chosen side
and did not react again until the mob was 10.3 yards away. The active source candidate carries
that hazard state across guidepoint boundaries; geometry and thresholds are unchanged.
It is uploaded inert as **wowborg:v108**
(`c2896a36-05a4-4a0c-ba88-83d8ae57c48c`, source `8376f77`). Request
`xreq_b64d45bd-4169-470d-bd03-634192fe700f` proved the cross-node state survives and
reached 1,784.9 living northing yards. It later encountered two Glasshide Basilisks with only
11.9 yards of best candidate clearance, moved anyway, and pulled at 5.6 yards. The active source
candidate treats “both sides below 15 yards” as a wait edge, traces wait start/end, and suspends
the route-stall timer until a moving patrol opens a safe bypass.
It is uploaded inert as **wowborg:v109**
(`6ada5206-cb39-4c3f-8b8b-db9b93fd86d6`, source `dc8fe3d`). Request
`xreq_b05d3806-0a9b-4ef7-b9e2-02dbf97ae61c` proved the wait edge activates and
releases, but a later wait at 14.5 yards let a Glasshide Petrifier cross the stationary player,
pull at close range, and back out to its 29.5-yard casting distance. The active source candidate
records the last observation with a safe edge, retreats to it when both bypasses become unsafe,
and waits only after reaching that holding point. The 15-yard criterion is unchanged.
It is uploaded inert as **wowborg:v110**
(`e33c39e7-3653-4e45-957f-bad88258b67b`, source `e95156e`). Request
`xreq_da39a3f7-4160-4291-b288-753be45a9b48` emitted no retreat activations: its
last-safe observations were commonly one seven-yard pulse behind, but the reused eight-yard
guidepoint radius treated them as already reached. The active source candidate changes only the
safe-holding arrival radius to two yards so retreat can actually activate.
It is uploaded inert as **wowborg:v111**
(`3202f1c4-8a65-4f9b-b05a-f41523e11f3c`, source `3fd1b9c`). Request
`xreq_24ae35ee-7dac-4035-9f65-8792bd5d4f89` produced repeated retreat activations,
but each pulse that temporarily restored 15 yards overwrote the anchor inside the live encounter.
Retreats collapsed into 6–7-yard oscillations until a Scorpid pulled. The active source candidate
freezes the anchor until the projected corridor is fully clear.
It is uploaded inert as **wowborg:v112**
(`9b8831af-2095-4505-98a5-ddf1e814fe54`, source `a20766f`). Request
`xreq_f8931af8-bc85-4073-85da-021d50524465` cleared 11 guidepoints and reached
1,869.4 living northing yards, the best current-contract result. It then pulled one level-45–49
Glasshide Basilisk at road node 8. Direct escape lost 2,098 health over 7.9 seconds while moving
146 yards away from the route target, and the generic eight-second route-progress watchdog
aborted at 595 health. The active source candidate instead fights exactly one known non-elite
attacker when wowborg has at least a ten-level advantage and 80% health; all unsafe cases retain
escape. Fight/escape activation and strength inputs are traced.
It is uploaded inert as **wowborg:v113**
(`ad98cbe0-d091-4f2b-8f73-3de152516a3a`, source `1e8ca0b`), but two hosted requests
failed before connection with empty logs. The upload argv was `python -m wowborg.main`, which
defines but does not invoke `main()`. The identical image is re-uploaded inert as **wowborg:v114**
(`830a0fa0-7d92-416f-8c8a-0eabc9f1015e`) with the correct `python -m wowborg` package
entrypoint. Request `xreq_a4c0fd12-fcf6-49b4-8dc6-fb46bb57b302` proved exact melee
activation but falsified the strength premise: 413 outgoing versus 570 incoming damage in
1.7 seconds against one level-48 Rabid Blisterpaw, followed by death after six guidepoints.
The pre-pull retreat had orbited its six-yard safe anchor because fixed 0.75-second forward-turn
pulses cannot settle within two yards. The active source returns to v112's escape-only combat
baseline and changes only retreat arrival: turn in place, then move with a distance-bounded pulse.
It is uploaded inert as **wowborg:v115**
(`1035e292-5f91-4e18-9398-89161c4bc14a`, source `35d9050`). Request
`xreq_c8dbfd00-8211-4e47-88a7-9e6025b588ca` avoided every pull and death, but cleared
only nine guidepoints before the episode timeout. Its final retreat spent 106 seconds stationary,
alternating fixed 0.25-second turn pulses around the safe-anchor heading. At the documented
pi-radian/second turn rate, each pulse rotates about 45 degrees and overshoots the 0.20-radian
deadband. The active source candidate changes only precise-turn duration to remaining angular
error divided by the turn rate, capped at 0.25 seconds; ordinary steering and hazard geometry are
unchanged. It is uploaded inert as **wowborg:v116**
(`b5ccf41d-92bd-499d-90cc-a6289c987f1a`, source `217902a`). Request
`xreq_21621766-8175-471c-91f9-2b748bfd7c5f` did not repeat the sign-flip loop, but its
first non-quarter-second turn (`0.2188` seconds) timed out at frame 102 without advancing an
observation; it cleared one guidepoint and remained alive with no combat. Owner source confirms
held axis magnitude is reduced to sign. The active candidate therefore keeps the reliable
0.25-second turn quantum and changes only precise arrival's heading acceptance to its matching
45-degree arc; ordinary steering and hazard geometry remain unchanged. It is uploaded inert as
**wowborg:v117** (`6e2b8986-7233-4eca-9412-fcb2f03353ae`, source `13604c1`);
request `xreq_199cfdb3-6a1c-4918-a5ca-adb51b145caf` proved every turn action settles
and six retreats end, but the 45-degree acceptance cone is too coarse. On the fatal retreat it
accepted a 39-degree residual heading, moved forward on the wrong diagonal, passed a Glasshide
Gazer at 3.68 yards, and died after three guidepoints. The active candidate uses the contract's
left/right strafe axis when residual error exceeds 22.5 degrees, reducing precise translation
error to at most 22.5 degrees without changing turn duration, ordinary steering, or hazard
geometry. It is uploaded inert as **wowborg:v118**
(`2e5125da-9fa8-43b7-a8e4-73808d86f8ef`, source `2982c92`). Request
`xreq_e4e7e0ca-8a69-4b96-b84e-c115ef09896b` stayed alive and out of combat, but
failed after one guidepoint because wowborg's thin `select_move_vector` convenience method did
not expose the upstream action contract's existing `strafe` field. The active source adds that
missing pass-through; the diagonal strategy itself is unchanged.
It is uploaded inert as **wowborg:v119**
(`635748f7-56bd-4295-abed-59ddf4e82f98`, source `90b0f91`). Request
`xreq_bee76128-17b5-4bcc-adb5-899a08111294` stayed full-health and out of combat,
reached nine guidepoints / 1,320.1 living northing yards, and mechanically completed every
retreat. It was inefficient: 140 retreats and 139 side switches consumed the episode at road
node 7. Retreats ended whenever projected clearance briefly recovered, even while wowborg was
still 20–45 yards from its frozen safe anchor, then restarted on the next unsafe frame. The active
candidate persists retreat until it actually reaches that anchor.
It is uploaded inert as **wowborg:v120**
(`851c62e2-2a32-4e8d-8501-18067e495a30`, source `0e2a8fb`). Request
`xreq_4bef2465-c2bc-4933-868d-dd048e53a561` reduced churn to seven retreats and four
switches, but persistent retreat exercised a distance-derived 0.5629-second diagonal translation
that timed out at frame 559. It reached three guidepoints and had one escaped pull. The active
candidate uses the proven exact 0.25-second quantum for every precise translation; turn behavior,
state semantics, and geometry are unchanged.
It is uploaded inert as **wowborg:v121**
(`377a2f3e-215e-4425-8f98-06d540db6c47`, source `8b0a2e2`). Request
`xreq_7063f045-2013-4368-a884-1893ca923ad7` had zero action timeouts and completed
13 retreats, but reached only three guidepoints. At the final anchor it waited while a moving
Glasshide Gazer closed from 17.5 to 15.3 yards and acquired wowborg; escape then tripped the
route-progress watchdog. The active candidate replaces stationary unsafe-anchor waiting with
quantized movement away from the active corridor hazards until a safe bypass reopens.
It is uploaded inert as **wowborg:v122**
(`da731748-bd0b-47c6-8b41-8893ba8cb59f`, source `475f58b`). Request
`xreq_5beaa43e-290d-47b3-a3bf-7e5ef8a0a282` activated and completed three mobile
unsafe-anchor evasions with no action timeout, survived at full health, and improved living
northing from v121's 424.1 to 605.5 yards. It then stalled at road node 3: ordinary 0.75-second
forward-turn pulses alternated left/right on every action from frames 592–650 while remaining
65.6 yards from the target. The active source candidate changes ordinary heading correction to
the same proven 0.25-second turn-in-place quantum; straight road translation remains 0.75 seconds.
It is uploaded inert as **wowborg:v123**
(`ec6fe6c8-f7c4-4847-a242-a7aec0d6d8fc`, source `3af9760`). Request
`xreq_46147008-1cf6-43d2-8f2f-37906b15240d` stayed full-health with no combat or
action timeout, but the unchanged 0.20-radian ordinary heading deadband made the 45-degree turn
quantum alternate in place at road node 1. The active candidate uses the complete discrete
actuator: accept heading error through 45 degrees, then add signed strafe beyond 22.5 degrees to
translate along the nearest 45-degree direction. Straight translation duration remains unchanged.
It is uploaded inert as **wowborg:v124**
(`5da21603-0777-48b7-b131-de9420d24ef6`, source `da3459d`). Request
`xreq_1686e46f-4062-43d6-b495-7db0ebd3e82e` cleared the first two road nodes with
no turn loop or action timeout, proving the discrete actuator. At node 3, a fixed 30-yard bypass
with 18.6 yards of projected clearance was accepted under the 15-yard minimum; after one normal
7.3-yard pulse a moving Glasshide Gazer closed to 16.5 yards, acquired, and killed wowborg. The
active candidate raises the route-clearance floor to 25 yards and chooses the shortest 30/45/60
yard lateral bypass that meets it, or the highest-clearance candidate if none do.
It is uploaded inert as **wowborg:v125**
(`87739aaf-702e-47fb-971e-acd5c43a4fb7`, source `c491039`). Request
`xreq_63741569-df7c-4a98-aae3-e374cf35f365` stayed full-health and out of combat,
and selected every configured lateral width, but issued 721 accepted retreat translations without
moving after a 5.9-yard safe anchor became physically blocked. Persistent retreat also suppressed
the general route-stall timer. The active candidate detects three consecutive retreat pulses below
0.5 yards, traces the blocked anchor, and transfers control to mobile hazard evasion so a different
escape vector can be selected.
It is uploaded inert as **wowborg:v126**
(`149ff0eb-750d-4efa-b524-7b7d7302c697`, source `a5d18e3`). Request
`xreq_2794b3ad-a849-4a1f-a733-e4659298a305` fired 68 blocked-anchor transitions,
stayed full-health with no combat or timeout, cleared nine guidepoints, and reached 1,318.5 living
northing yards. It then spent the remaining episode at road node 7 despite already crossing the
node's northing by 23 yards and remaining only 32 yards lateral. The active candidate accepts an
intermediate road guidepoint after crossing its northing within 60 lateral yards; the Great Lift
lower dock retains exact eight-yard arrival.
It is uploaded inert as **wowborg:v127**
(`010103bc-3838-4a7e-89a0-975beeb09c9b`, source `87adcda`). Request
`xreq_dc68b02d-a892-4d7b-b73a-728569f395be` emitted the bounded pass, stayed
full-health with no combat or timeout, and improved to 11 guidepoints / 1,869.8 reported northing
yards, with actual max x another 156.6 yards ahead. It still spent 92 evasions and 66 blocked
retreats under the 25-yard floor. The active candidate lowers the clearance floor to 20 yards:
this still rejects v124's fatal 18.6-yard candidate while recovering five yards of routing freedom.
It is uploaded inert as **wowborg:v128**
(`40be968c-6891-4dc2-8d9d-6c18cdbc3811`, source `cd61076`). Request
`xreq_b8263b3b-87fe-4fa6-a0c4-9539f2ac875a` stayed full-health with no combat or
timeout, reduced avoidance churn roughly in half, and reached 2,027.5 reported northing yards.
At Tanaris road node 9 it then issued accepted ordinary forward inputs for eight seconds without
physical displacement and terminated 222 yards from the guidepoint. The active candidate uses the
existing progress watchdog to try one traced forward-diagonal recovery pulse on each side; if both
remain blocked, the same no-progress failure still terminates the route.
It is uploaded inert as **wowborg:v129**
(`e27cf658-ddef-4d2d-93fe-89b31c4b04dd`, source `29f415a`). The first direct-Coworld
request accidentally selected the default fresh-start variant and is not evidence. Corrected
Traverse request `xreq_37c9ae98-da0f-424c-8176-6025218f4528` showed the first recovery
pulse moved 0.781 yards, then rewedged; the next two moved only 0.323 and 0.463 yards before bounded
exhaustion. It survived at 2,011.7 northing yards after one Scorpid and one Basilisk contact.
Deployed 0.1.209 Detour recon from both observed stuck poses showed the coarse node 8-to-9 chord
omits a required bend through `(-7194,-3733)`, `(-7172,-3754)`, and `(-7097,-3795)`. The active
candidate adds those three exact corridor anchors; they cannot use northing-pass semantics because
hazard displacement can require brief x-backtracking to regain the corridor.
It is uploaded inert as **wowborg:v130**
(`c40c37d1-0396-4307-b850-bac8714e1d67`, source `187b820`). Request
`xreq_786d0482-defb-41da-970c-da0a8858156d` died near road node 2 before reaching
the new terrain anchors. The fatal Scorpid was already tracked at 63.2 yards, outside the old
30-yard projected corridor; when it re-entered as a hazard at 27.8 yards, clearance had collapsed
and reached only 0–2.7 yards before contact. The active candidate widens predictive corridor
entry/exit to 60/70 yards while retaining the existing 80-yard tracked-unit envelope, so crossing
patrols are routed around while safe clearance still exists.
It is uploaded inert as **wowborg:v131**
(`e663e114-f50f-4246-b054-74e2e642474a`, source `811a92e`). Request
`xreq_cc157cd3-3f7a-469b-b954-55962bc1c8c9` survived but activated 55 avoidances
and ended 54, walked 5,942 trajectory yards for 1,842 northing, contacted three mobs, and timed out
at node 8. The widened lookahead exposed a state defect: once a bypass changes the instantaneous
line to the guidepoint, the triggering patrol can fall outside that new corridor while still
nearby, ending avoidance and making wowborg cut back toward it. The active candidate retains each
triggering hostile by GUID until it is actually beyond the 70-yard exit radius; new crossing
hazards can join the active set, and disappearance beyond the 80-yard visible envelope clears it.
It is uploaded inert as **wowborg:v132**
(`1ccd4562-dba9-458e-ac61-53e0afadb02f`, source `751998a`). Request
`xreq_27e8af9f-97b7-44dd-a7eb-285a398ce527` stayed full-health and contact-free,
and reduced avoidance lifecycle churn to three starts and two ends. But the continuously
recomputed target orbited retained patrols: 79 side switches, 142 retreats, only 150 net northing,
and a timeout at road node 1. The active candidate freezes a concrete 140-yard-ahead lateral
waypoint, releasing it on arrival and replanning only when a genuinely new patrol crosses the
active path.
It is uploaded inert as **wowborg:v133**
(`f9fb6c08-632e-46e5-b20f-76278b79371a`, source `f371bd1`). Request
`xreq_9a451cfa-f39f-41e5-ada4-d2573837a55b` replanned 23 times as new patrol
GUIDs entered its displaced path, left the owner road for the surrounding spawn field, and died to
a Glasshide Petrifier after only 142 net northing yards. The active candidate restores the proven
20-yard local sidestep and 30/40-yard immediate horizon. Its separate 60-yard predictor now holds
position for a moving patrol whose path remains at least 20 yards from the holding point; only an
immediate blocker or a patrol projected inside that safety radius triggers lateral avoidance.
It is uploaded inert as **wowborg:v134**
(`2354e2a4-a82c-4e25-a719-375e16dfc6c1`, source `11421a5`). Request
`xreq_f89a11e1-5c2f-4a1e-8518-1dfcc980adb3` stayed full-health with zero combat
and reached nine guidepoints, but spent 3,129 pulses holding and timed out at road node 7 after
1,605 net northing yards. A Roc repeatedly projected across the next guidepoint, so an unbounded
wait cannot clear a resident patrol. The active candidate bounds holding to two wall seconds per
GUID (about 20 simulated seconds), then treats a still-present patrol as a local blocker until it
leaves the 80-yard tracked set; brief trajectory jitter does not reset the timer.
It is uploaded inert as **wowborg:v135**
(`cef2e31f-773e-4045-b341-13cb6d3a7b59`, source `b03cabd`). Request
`xreq_cbb87d77-a2ed-48bb-a30e-205105a13733` escalated the first safe Scorpid
crossing, cascaded into a Glasshide Petrifier contact, and died at node 1 after only 96 net northing
yards. The timer conflated transient crossings with resident blockers. The active candidate instead
holds for genuine cross-traffic but locally avoids a moving patrol whose destination lies within
30 yards of the active guidepoint. In the observed contrast, the safe early Scorpid destination was
about 188 yards from node 1, while v134's blocking Roc repeatedly targeted within about 12 yards of
node 7.
It is uploaded inert as **wowborg:v136**
(`e604b7aa-fc13-4871-a7b5-bc1a084afb48`, source `ab358ec`). Request
`xreq_80a314cf-f183-43c1-bb7f-e818e708651e` was infrastructure-censored by a
30-second action-settlement timeout at node 3 while full-health. Fair repeat
`xreq_50cabc51-a8db-4a56-88b3-dba3884b0bd2` survived and recovered from one Tail
Lasher contact, but timed out at node 7 only about 14 yards from its center and just 5 yards short
of its exact northing threshold. The active candidate permits ordinary guidepoints to pass up to
20 yards before their target x while retaining the existing 60-yard lateral/z corridor. The three
Detour bend anchors and Great Lift remain exact.
It is uploaded inert as **wowborg:v137**
(`de9133dc-8ede-416d-98db-e2713ae88a6d`, source `b7bdcd1`). Request
`xreq_3c31de07-6a4e-40a6-87f0-c46126c03bbe` emitted eight ordinary pass events
through node 6, proving the completion change, but died to two Tail Lasher contacts before node 7.
Pinned 0.1.209 Detour recon found no connected broad north or south bypass around this pass. The
active candidate instead retains a crossing GUID while it remains within 70 yards or intersects
lookahead, holding without displacement. A projected path inside 20 yards of the holding point
still escalates to local avoidance, and guidepoint-resident classification remains active.
It is uploaded inert as **wowborg:v138**
(`cec936af-e9e3-4141-afaa-d693d0a4ccc4`, source `2d61417`). Request
`xreq_d1cd8097-6b68-4ba5-9e28-7c6c945374fe` stayed full-health with zero combat,
but spent 6,339 pulses holding and reached only road node 3. The retention rule exposed a more
basic classification defect: the no-hazard branch held for every moving hostile in lookahead,
whether or not its projected patrol crossed wowborg. The active candidate holds only an isolated
projected crossing; immediate and guidepoint-resident blockers still use local avoidance, and a
held crossing releases as soon as its projected trajectory clears.
It is uploaded inert as **wowborg:v139**
(`e97ab7d9-2c61-4f95-a334-3c3bf8eb78da`, source `bb9871f`). Request
`xreq_2d456355-d5b9-4d8c-936c-d239a369b07d` stayed full-health with zero combat,
reached all three exact Detour anchors and road node 9 in about 2.5 minutes, then failed the
Shimmering Flats south-ramp leg. Pinned 0.1.209 navmesh shows that reachable 265-yard corridor
bends through `(-6884,-3900,54)`, `(-6876,-3912,100)`, and `(-6848,-3925,125)`; direct steering
at the far endpoint repeatedly fell from the escarpment. The active candidate adds those three
real corridor bends as exact anchors without changing the proven Tanaris hazard policy.
It is uploaded inert as **wowborg:v140**
(`191f1a51-9c67-46a1-8e5e-dc4d28efb9a3`, source `3ef7543`). Request
`xreq_7ce2cbdf-f84f-4bc4-ae06-5d6be2189fdd` remained alive, reached the same 15
Tanaris milestones, and had one brief contact costing 56 health, but an unusually dense hazard
draw took 238 seconds to road node 9 and left only 29 seconds for the first ramp anchor. The ramp
geometry is not falsified; the fixed episode horizon makes actuator throughput the binding
constraint. The active candidate doubles open translation from 0.75 to 1.5 seconds while keeping
0.25-second precision for turns, retreat/evasion, and the final 20 yards of every target. Its
roughly 10.5-yard open stride remains inside the existing 30-yard immediate hazard gate.
It is uploaded inert as **wowborg:v141**
(`53afe44e-b6aa-4880-9111-eeffe620e64f`, source `1c051b2`). Request
`xreq_8ab6b8b3-5215-4506-8817-864538ef59a8` reached road node 7 six seconds
faster than v139, but the longer stride closed on a Glasshide Basilisk to 2.7 yards and died before
node 8. The stride is unsafe and its speed gain is small. Trace/code reconciliation found the real
throughput defect: each synchronous vector action already returns its settled next frame, but
Traverse then submitted a redundant 0.25-second wait before every next pulse. The active candidate
restores the proven 0.75-second stride and removes that wait, increasing movement duty cycle from
75% to 100% without increasing one-pulse hazard reaction distance.
It is uploaded inert as **wowborg:v142**
(`663ecd3e-10eb-4ba4-9a73-0cf33d43a33c`, source `c126d76`). First request
`xreq_5a105daa-13a3-4304-be2b-515587f6da89` stayed full-health with zero combat
and reached the Detour bend in 132 seconds, but one action timed out after 30 seconds while the
prior 948 actions all settled (p99 377 ms). Fair repeat
`xreq_c60c6458-3659-4a37-a8ef-63b35a372b60` again stayed full-health, reached all
three exact bend anchors, then hit the same timeout after roughly 985 uninterrupted actions. The
active candidate yields for 0.25 seconds every eight settled pulses: roughly 97% movement duty
cycle versus the original 75%, with a periodic host settlement seam.
It is uploaded inert as **wowborg:v143**
(`0f9033bc-0247-4843-9b77-2af1292a43f8`, source `c40a81b`). Request
`xreq_79ff2e95-2930-444c-8026-3c30c5066a75` executed 165 scheduled yields
without v142's repeated host timeout, stayed full-health/zero-combat through Tanaris, and reached
road node 9 in 164 seconds. The first ramp anchor was still too coarse for discrete steering:
wowborg ran east along the cliff edge and fell before reaching its required southward bend. The
active candidate splits the pinned navmesh approach at `(-6905,-3869,39)` and
`(-6890,-3885,48)` before the existing exact base anchor.
It is uploaded inert as **wowborg:v144**
(`bb21cd9f-2573-4f1c-bfd2-ff5be57842ac`, source `3e2d09c`). Request
`xreq_98016dca-efdf-4bbb-b394-b52d6ebb6433` stayed full-health with zero combat,
but was infrastructure-censored before reaching the new ramp anchors: another 0.75-second action
timed out at about `(-7155,-3769)` on the exact Detour-east leg. Sparse yields improve ordinary
road cadence, but this tight bend needs v139's every-pulse settlement seam. The active candidate
yields after every pulse on exact anchors and every eight pulses on ordinary roads.
It is uploaded inert as **wowborg:v145**
(`dbbc1e08-2f0a-42b8-b79f-9f1e010d72af`, source `9e0c895`). Request
`xreq_07f6e8d6-9bdc-44a6-8102-a18ad3a0c3b5` stayed full-health with zero combat
and removed the action timeout, but exhausted unstick at about `(-7144,-3767)` on Detour-east.
Pinned 0.1.209 navmesh shows the corridor stays shallow to `(-7129,-3767)` before turning
southeast; direct steering forced the diagonal too early. The active candidate adds that real turn
as an exact anchor so crossing no longer depends on v139's lucky left unstick.
It is uploaded inert as **wowborg:v146**
(`8fe6eaee-e885-4117-bc6e-b5b10035d602`, source `41ed1b2`). First request
`xreq_b3f7b4b0-d3ab-447b-a4d2-94505149ad67` was censored by unrelated early
hazard displacement before the changed bend. Fair repeat
`xreq_df6ba150-777d-4417-a4cd-02256116bc59` proved the new exact turn and final
Detour-east anchor at full health with zero combat, but exposed an upstream completion defect:
ordinary node 9 passed at z `-22.7` versus target z `28.9` because its 60-yard pass tolerance
combined y and z. The ramp therefore began below terrain and repeatedly fell/reset. The active
candidate retains 60 yards of horizontal hazard-displacement slack but requires vertical error at
most 10 yards before an ordinary milestone can pass.
It is uploaded inert as **wowborg:v147**
(`9ddebbfa-f068-41be-9ea5-32648a60d8c6`, source `57ed0da`). Request
`xreq_25bda105-0daf-4943-aa2e-e3f0c87ec9a4` enforced vertical alignment on all
11 ordinary pass events (maximum 8.2 yards), reached node 9 within 0.9 vertical yards, and emitted
the first exact ramp-approach arrival. It then fell approaching the ramp turn. The shared 8-yard
exact radius is too loose for the narrow slope; the active candidate tightens only the ramp anchors
to 3 yards while retaining existing tolerances for Detour anchors and the lower-dock goal.
It is uploaded inert as **wowborg:v148**
(`52ad576d-0fc3-4ab4-9570-db29744840f0`, source `205e9e7`). Its first request
`xreq_36342e76-936c-4950-9f14-c6552ae08b6b` was combat-censored before the ramp. Two
full-health zero-combat repeats (`xreq_dc28e85e-d277-4add-8f0c-290e4c6596cf` and
`xreq_c82b3f22-a720-4816-944c-9c9bd5e786de`) both cleared the four exact Detour anchors,
then lost the returned frame on the second ordinary node-9 translation. The latter trace records
the 0.75-second action at `(-7096.53,-3793.63,8.43)` timing out after 30 seconds while the game
host recorded hundreds of WebSocket detach/reattach cycles. The ramp-radius change therefore
remains unexercised. The active candidate reduces exposure to that host churn with a conservative
1.0-second translation only when no road hazard or combat is visible and the target is more than
20 yards away; turns and all hazard/arrival pulses retain their prior cadence. Every longer pulse
emits `traverse_road_open_stride`. It is uploaded inert as **wowborg:v149**
(`b8f24e46-e596-4f20-b154-fb8ed19166a3`, source `4c5e9fc`). Request
`xreq_e218fe41-65f7-414d-a012-066a04b1e7d4` fired 258 longer pulses, stayed at
full health with zero combat, and reached node 9 in about 128 seconds. It then repeatedly reached
the safe ramp lip near `(-6912,-3859,39)`, but generic resident-hazard detours stepped laterally off
the narrow elevated corridor, fell/reset, and consumed the rest of the episode. The active candidate
holds instead of laterally detouring when a resident hazard projects into one of the six tight ramp
anchors; ordinary roads keep their existing dynamic detours. The hold emits reason
`terrain_constrained_resident` and releases when no tracked resident still projects into the
target corridor. It is uploaded inert as **wowborg:v150**
(`a2d455f5-da0b-4e61-8dd2-d0e637c3e998`, source `c71e07d`). Request
`xreq_6b180e18-2154-4427-a3ee-1e26f5cce2ba` reached node 9 at full health, then
activated one terrain-constrained hold for a Basilisk still 60.7 yards away and never released
before the episode deadline. The active candidate holds only an imminent resident inside the
existing 30-yard hazard-entry gate; far projected residents may be crossed before they arrive.
Rank-1 Prowl remains invalid here because its exact detection range is worse than visible level-gap
aggro, and current basic melee remains too weak to promote over the timing solution. It is uploaded
inert as **wowborg:v151** (`6aa3b0e1-c341-446b-8be2-db4b93d7c6bb`, source `b37617e`).
Request `xreq_9e8b2946-9085-49c6-8ad1-14b8d2a7ee5e` reached node 9 at full health,
activated three terrain holds, released twice near 29 yards, then remained blocked at 23.1 yards.
The active candidate suppresses ordinary lateral detours for a resident on the only narrow ramp
edge, crosses straight while its current distance exceeds the existing 20-yard safety floor, and
holds at or inside 20 yards. This retains roughly 13 yards over the measured 5–7-yard visible aggro
radius without reviving uncalibrated melee or inferior rank-1 Prowl. It is uploaded inert as
**wowborg:v152** (`1876851a-0885-433e-be17-055734567913`, source `376d854`).
First request `xreq_0bb6ba02-9257-423e-bed2-54e37ce62f20` died before the changed ramp.
Fair repeat `xreq_5a742ce8-92be-4064-a812-f65bc032db88` stayed at full health, reached
node 9, and exercised 29 terrain holds with 28 releases, but never arrived at the approach. Its
positions repeatedly identify a stable ramp lip at `(-6911.46,-3859.38,39.24)` before direct
steering cuts off the slope. The active candidate inserts that observed lip as a three-yard exact
anchor before the existing approach; v152 hazard timing is unchanged. It is uploaded inert as
**wowborg:v153** (`11b765a4-2eaf-419f-8a1d-8d848baa067a`, source `c838e20`).
First request `xreq_7b7b2089-a15e-4294-9486-882ff7306868` stopped before the changed
anchor. Fair repeat `xreq_fb01b524-ea4d-497b-8fa0-f8a1d4f94966` reached the new lip at
full health as milestone 17, then remained six yards from the broad approach while a Basilisk held
at 16.8 yards. The active candidate separates terrain-constrained hazard handling from three-yard
arrival precision: the approach retains ramp hold semantics but restores its sufficient eight-yard
arrival, while the lip and later narrow bends remain three-yard anchors.

### Previous 0.1.208 movement baseline

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

For that baseline, the lab source dependency and exact environment-image pin matched 0.1.208. Use
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

The active Great-Lift-arrival candidate replaces the static Tanaris detour with the exact
deployed owner road chain: 23 connected ordinary-navmesh legs and 6,560.2 route yards through
Tanaris, the Shimmering Flats, and Thousand Needles. It ends at the lower dock and deliberately
does not board the lift. It is uploaded inert as **wowborg:v90**
(`6593c92d-2c1a-46f8-abe5-658300d5a7eb`, source `fb09adc`). First five-episode hosted
request `xreq_0e577780-d491-4ac5-9a4f-256258d15c7a` failed 5/5 before combat: its first
302-yard semantic move advanced one 4.94-yard corridor horizon and then hit the environment's
action deadline, leaving all five characters alive at spawn with zero guidepoints. The next
candidate kept the exact road but drove its legs with bounded ordinary steering. It is uploaded
inert as **wowborg:v91** (`b2cc42e5-822d-4459-89eb-6c16195a7e3c`, source `0b21234`). Request
`xreq_ba3e0d47-539f-4e3d-8f89-44c776e050fb` showed that even its first 0.249-second turn-only
`move_vector` timed out without advancing frame 2. The active candidate therefore uses short
semantic micro-targets sized to settle within the five-second environment action horizon;
v90's telemetry proves that semantic movement can advance 4.94 yards inside that horizon. That
candidate is uploaded inert as **wowborg:v92**
(`e05dc2ad-be49-4e9f-b9c2-a971ca6a7c31`, source `c5881ed`), but request
`xreq_3f2afccb-a366-446e-a201-a431bd5ff07f` still timed out without advancing frame 2.
v93 advanced an explicit wait from frame 2 to frame 3, then wedged on movement there, ruling
out a Travel Form race. Fresh control `xreq_d53a387d-906d-4dfd-9372-abfc3018f1ed` confirmed
that unchanged v88 still drives movement against today's 0.1.208 game,
although its old southwest route died and spent 84.2% of the episode as a ghost. v94 combined
the published 0.1.188 game contract with the failed micro-target experiment and again did not
move. v95 restored the long semantic movement shape, but again the host advanced 4.94 yards
eastbound while the policy never received frame 3. The fresh v88 control's southwest opening did
return successive frames. The active candidate therefore adds one short southwest movement
bootstrap, safely before v88's lethal old endpoint, then turns onto v90's canonical road on the
following frame. v96 proved that bootstrap across frames 2 through 10, then stalled on the first
eastbound semantic action. The active candidate keeps the successful bootstrap and uses bounded
ordinary keyboard steering for the canonical road, testing vector control only after movement is
already established.
v97 proved the first post-bootstrap turn advances to frame 11, but a second consecutive
turn-only action wedges without displacement. The active candidate holds forward while turning,
so every bounded steering action produces physical route progress.
v98's first forward-turn arc displaced 6.4 yards and returned frame 11, but a second consecutive
vector action wedged. The active candidate inserts one contract-native wait between vector pulses
to break the failing continuation chain; activation emits `traverse_road_pulse_settled`.
v99 advanced that wait to frame 12 but its following 0.431-second vector still wedged. Across all
four vector probes, 0.75-second actions settle and every shorter action times out. The active
candidate fixes every steering pulse at the proven 0.75-second duration.
v100 proved that mechanism continuously through frame 400: it reached four guidepoints, gained
872.08 living northing yards, and had no movement failures or damage before the first real route
hazard. A Glasshide Gazer at roughly `(-8331,-3277)` pulled wowborg at
`(-8314.9,-3269.0)`, then dealt 2,808 damage over 108.7 seconds while the stopped policy dealt
none. The active candidate inserts one pinned-navmesh-verified northern bypass at
`(-8350,-3180,14.1)`, over 40 yards clear of that observed patrol, and rejoins the unchanged
owner road at node 4. It is uploaded inert as **wowborg:v101**
(`22efcbf3-9091-4299-8023-c848981f0362`, source `5c56fff`). Request
`xreq_18d73da8-12b7-4a42-a8f2-83224fb9367e` falsified that one-point bypass: a
Dunemaul Brute at `(-8396.0,-3178.9)` pulled from 4.1 yards and killed wowborg at
`(-8395.8,-3175.2)` after 2,825 damage over 83.8 seconds. The active candidate stays on v100's
proven center road through `(-8401.8,-3220.7)`, then crosses due east at `y=-3220`, 42 yards
south of the observed Brute and 57 yards north of the observed Gazer, before rejoining node 4.
It is uploaded inert as **wowborg:v102**
(`775f286c-aa9d-4834-86e1-75730cfb3762`, source `48db44c`). Request
`xreq_f0744efc-7573-4b44-b978-0934c83cc599` cleared both measured hazards at full
health and reached road node 5. At `(-7989.2,-3488.8)` it took one 62-damage hit, then stopped
and disconnected because the road-leg loop treats any combat as terminal. It still had 2,692 of
2,754 health. The active candidate retains the measured route but continues steering along it
during incidental combat, tracing attacker identity and escape start/end instead of freezing.
It is uploaded inert as **wowborg:v103**
(`a7b0bc17-80b6-4e7c-b909-dbefe9486428`, source `928cb29`). Request
`xreq_46900459-a4be-465a-8a34-d54006fa5746` proved the fallback activated and kept
moving, but a seed-dependent Glasshide Gazer pulled earlier at 7.9 yards and followed for roughly
100 route yards until death. The active candidate adds pre-aggro dynamic steering: a hostile
within 30 yards ahead bends pulses toward the higher-clearance side of the road, holds that side
until 40 yards clear, and traces avoidance activation/end with exact unit evidence. It is uploaded
inert as **wowborg:v104** (`6472b8dc-0499-4a05-b28d-070c029b950d`, source `1d44515`);
request `xreq_f77ed886-9df8-4b54-98ff-7a88222840ff` activated avoidance nine times but
still died. The trace explains why: any nearby unit triggered a turn while only the triggering
unit influenced side choice, so avoiding a Rabid Blisterpaw exposed a Glasshide Gazer and the
stale side persisted. The active candidate triggers only on an 18-yard forward-corridor
intersection, scores both sides against every nearby hostile, switches only for five yards more
clearance, and flees directly away from attackers if a pull still occurs. It is uploaded inert as
**wowborg:v105** (`af1d041f-61d2-45a5-bb44-6051762f2934`, source `d763b81`); hosted
request `xreq_9e058bae-fea0-4824-9045-13333b28a992` was invalidated before movement by the
0.1.209 observation expansion. V106 carries the same router on the matching live contract.

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

1. **Evaluate the canonical Tanaris road before generalizing hazard-aware routing.**
   [The 2026-08-08 recon](docs/recon/traverse-hazard-routing-2026-08-08.md) finds that the owner
   route begins at the exact league spawn while the current static-envelope detour crosses the
   hosted death cells. Use road/navmesh routing as the baseline, then add live-unit avoidance and
   only later a calibrated fight-cost selector. The fixture's Prowl rank 1 is not a viable
   fallback: its 100 stealth value gives these level-45–49 mobs roughly 22–25 yards of frontal
   detection (13–16 from behind), versus only 5–7 yards of ordinary level-adjusted aggro, while
   also slowing movement by 40%. The next attributable change is the opening road prefix alone.
   The current inert candidate is **wowborg:v154**
   (`4b12b163-c947-4fee-969f-cd6b7110e01f`, source `e030d61`): it has already
   reached the observed Shimmering Flats ramp lip at full health in its v153 predecessor and now
   restores the broad ramp approach's eight-yard arrival tolerance while preserving three-yard
   precision at the lip and later bends. It has not been submitted; v78 remains champion.
   Its request `xreq_2a2d6324-4fb2-470a-8aad-14dc08e7091f` reached the lip and broad
   approach at full health with zero combat, then exhausted 86 seconds holding at the ramp-turn
   frontier. The next source candidate changes only the constrained-ramp resident floor from 20
   to 8 yards, retaining margin over the measured 5–7-yard visible aggro radius.
   That candidate is uploaded inert as **wowborg:v155**
   (`1345f357-a3eb-414d-9942-7fe54be5e726`, source `e7fc2c4`).
   Its request `xreq_801ccdf9-44a7-4f37-8b2e-e5a294999fd1` reached ramp-turn
   milestone 19, pulled the Scorpid at 4.9 yards, and died after generic lateral evasion had left
   the supported ramp. Pinned-navmesh recon found no connected bypass: complete paths converge
   within about 4.5 yards, while 9–10-yard-clearance offsets terminate on disconnected ledges.
   The next source candidate holds for every sub-eight-yard constrained-ramp hazard and suppresses
   lateral evasion there, establishing a supported frontier before adding any combat behavior.
   That candidate is uploaded inert as **wowborg:v156**
   (`35d3023e-a376-4d35-9207-c9424582c2d2`, source `be61bff`).
   Request `xreq_6ba1066e-b154-4a7b-bc5e-83bdc2054c06` reached milestones 17–18
   and held 25 seconds on supported terrain: pre-combat z stayed within 34.6–39.2 with zero
   constrained-ramp avoidance/evasion. The Scorpid eventually wandered into aggro at 6.7 yards;
   escape pulled a Basilisk and died. The next source candidate commits only against this single,
   non-elite level-40/41 Scorpid with the maintained Cat/Rake/Claw/Rip feral ordering.
   That candidate is uploaded inert as **wowborg:v157**
   (`e8629df4-2707-4729-9514-a9dcb14d512d`, source `c456c34`). It changes no route
   geometry or behavior against any other contact.
   Its one-run request `xreq_d2a1e397-b199-4cd0-be8e-43b5cffa1eb7` and three-run
   request `xreq_3ac8997c-c6bf-451e-8292-46ee09323961` produced zero fight
   activations: three runs exhausted on the variable road prefix, and the one ramp arrival held
   healthy for 82 seconds without a pull. The next source candidate proactively closes on the exact
   qualifying sub-eight-yard resident rather than waiting for it to wander into aggro.
   That candidate is uploaded inert as **wowborg:v158**
   (`6d531041-bc99-4755-a0c8-9a4d10457391`, source `4d0a8af`).
   Six-run request `xreq_903ae02b-bfc0-4f52-9150-8164d764711e` produced two exact
   proactive activations, but both repeatedly tried Cat Form while still in Travel Form; host
   telemetry reported "You are in shapeshift form" until deadline. The next source candidate first
   invokes the observed active-form binding to leave Travel Form, matching maintained real-playerbot,
   then enters Cat on the next frame.
   That candidate is uploaded inert as **wowborg:v159**
   (`083b6d20-c164-485d-b828-672a6a05e9ae`, source `d737576`).
   Six-run request `xreq_b7d21eda-82b8-46ec-9206-4e5906fff375` produced two exact
   proactive activations, but direct invocation of the observed current-form spell still did not
   toggle Travel Form. The environment's current action catalog exposes a typed `cancel_aura`
   action for active beneficial auras; the next source candidate uses it for spell 783 before Cat.
   That candidate is uploaded inert as **wowborg:v160**
   (`84f82e8c-f928-4e29-851e-5a2a8b2e0736`, source `b5f3e95`).
   Six-run request `xreq_a732a990-eb51-4157-bb7c-c025c48eac9b` produced one ramp
   kill: form exit and Cat entry succeeded; the level-41 Scorpid died in 34.0 seconds after 1,956
   dealt / 110 taken, with wowborg alive at full health. Rake and Claw lacked their required target,
   so host telemetry reported `select target` / `cancelled` and repeated auto-attacks did the work.
   The next source candidate passes the exact Scorpid GUID to every offensive feral spell.
   That candidate is uploaded inert as **wowborg:v161**
   (`922c2942-06d8-4b55-8ac1-bedf7bb41522`, source `f83906a`).
   Six-run request `xreq_dd819d01-f854-4b36-b482-128fb24fc8a6` produced one ramp
   fight. The exact target reached the spell command, but Rake was `Out of range`; auto-attacks
   killed the mob in 34.3 seconds (1,946 dealt / 367 taken). Wowborg survived and reached ramp-base
   milestone 20, the first post-kill advance. The next source candidate closes to two reported yards
   before attacking so the ramp's vertical separation cannot leave melee abilities outside range.
   That candidate is uploaded inert as **wowborg:v162**
   (`b1dfbc40-2631-4b5d-8581-83ec6e6a935f`, source `8057d2e`).
   Six-run request `xreq_c726b42a-4b82-4961-814c-2b16afd16ee1` produced three safe
   ramp kills. One landed Rake and two Claws, but all still took 33-36 seconds. The best run reached
   ramp-base milestone 20 before the 270-second horizon. It spent 266 seconds inside 1,452 action
   round trips, including 395 one-second hazard-free strides. The next source candidate changes
   only those clear-road strides to four seconds; the 80-yard hazard horizon and all constrained
   actions are unchanged.
   That candidate is uploaded inert as **wowborg:v163**
   (`c111df42-03f8-42c4-bc67-40e7603270c3`, source `99d2555`).
   Request `xreq_9523234d-13d1-40e6-b099-47a4df0b76e7` failed identically at the
   first clear stride in all six episodes: canonical `move_vector.duration` is capped at 1.5
   seconds, so the four-second action failed local validation before host submission. The next
   source candidate uses the contract maximum of 1.5 seconds.
   That candidate is uploaded inert as **wowborg:v164**
   (`a14b004c-0efa-481b-8cf9-d88263ce521d`, source `8ada40f`).
   Six-run request `xreq_414ce1c9-2d56-40f0-b372-6d44a5458d60` improved a representative
   ramp arrival only from about 202 to 190 seconds, while producing up to three earlier pulls in one
   episode and one ramp death. The next source candidate restores the proven one-second clear stride
   before changing hazard-path efficiency.
   With the safe stride restored, the active source candidate changes only local bypass geometry:
   40 yards forward rather than 20, with the same adaptive 30/45/60-yard lateral choices and
   mandatory 20-yard segment clearance. This remains inside the 60-yard lookahead and 80-yard
   tracking horizons while reducing lateral path waste.
   That candidate is uploaded inert as **wowborg:v165**
   (`3b4b7594-a711-456c-8d36-8cf282d241cc`, source `1086b45`).
   Six-run request `xreq_e02535ab-4616-4c12-a8c0-b242294471dd` survived without a
   death but reached only milestones 15, 18, 18, 18, 20, and 20. The best ramp approach improved
   to 166.7 seconds, but arrivals ranged through 210.1 seconds and every run still incurred 40-51
   avoidance starts plus 31-49 retreats. The longer tangent did not consistently reduce churn, so
   source restores the proven 20-yard forward component. The next isolated speed lever is the
   unavoidable ramp fight: current safe kills take 29-36 seconds and spend combo points on Rip
   before the fixture can use its maintained Ferocious Bite finisher.
   The active source candidate adds only the maintained five-combo-point Ferocious Bite finisher
   once the Scorpid is at or below 40% health. Existing Rake, Rip, and Claw ordering is unchanged;
   spell traces now include pre-cast combo points and active power so the hosted result can explain
   both activation and non-activation.
   That candidate is uploaded inert as **wowborg:v166**
   (`327685d0-0d64-4bd5-a606-322610bff48f`, source `937f6ec`). v78 remains the
   submitted champion.
   Six-run request `xreq_21b0b6d6-53dc-4b28-a60d-28661ec36868` produced zero Bite
   activations. Four runs stopped before the ramp; the two ramp-bearing runs admitted two Scorpids
   each and reached only two/four combo points. One recorded two 33.6-33.9-second fight windows and
   32 failed spells after combo points reset to zero. Current owner policy consistently treats
   observed `health <= 1` as terminal even if `is_dead` lags. The active source removes the
   inactive Bite branch and applies that terminal convention to Traverse hazards and attackers,
   preserving the resource trace fields for the next hosted proof.
   That candidate is uploaded inert as **wowborg:v167**
   (`31e355b8-384d-490b-a274-5f2669eb2c06`, source `7dc278e`).
   Six-run request `xreq_4b1d6b73-d335-466a-923b-4af9562cd3e4` kept every run alive.
   Its three ramp fights ended in 4.3, 5.3, and 15.6 seconds instead of 29-36 seconds, and all three
   reached ramp-base. From there, ramp-rise's 48-yard 3D distance selected one-second clear-road
   translations; traces show repeated falls from z about 52 to as low as -22 followed by correction
   snaps and `no_progress`. The active source changes only terrain-constrained anchors to retain
   quarter-second translation for their full leg.
   That candidate is uploaded inert as **wowborg:v168**
   (`29b5673e-b414-43c4-ad3a-64d1ff0d5089`, source `54c7b0c`).
   Six-run request `xreq_0810a791-b80a-4316-ab58-b427e8f8e231` kept all six runs
   alive. Three reached ramp-base after 4.4-6.3-second fights but still failed ramp-rise; the other
   three ended earlier on missing observation frames. The smaller pulses proved cadence was not
   the root cause: each ramp run moved diagonally off the edge and fell from z about 52 to below
   zero. A read-only route query over the canonical 0.1.209 VMaNGOS mmaps returned a complete
   17-point smooth path. It holds x near -6884 for the first three climbing points before bending
   east, unlike the invalid direct line. The active source replaces only that ascent leg with the
   canonical Detour points; combat, hazard routing, and ordinary-road cadence are unchanged.
   That candidate is uploaded inert as **wowborg:v169**
   (`ca5d030f-316e-4644-99d7-6dccb979bb48`, source `b7f1b50`).
   Six-run request `xreq_5d280a5e-dc35-48ce-927b-ca4f0e86ad4a` reached the first
   ascent point in two runs, then both walked off the edge and failed the second. Two runs died
   earlier in Tanaris, one stalled at the Detour bend, and one lost its observation frame. The
   route polygons are marked `NAV_STEEP_SLOPES`; this is the real mountain pass, but it requires
   jumps. Python's public local-step wire intentionally omits the internal jump hint, while the
   maintained host `move_to` follower infers jump-at-start edges from Detour polygon keys. The
   active source removes the manual ascent points and delegates only ramp-base-to-crest to that
   native follower. Hazard-aware steering remains unchanged before and after the pass.
   That candidate is uploaded inert as **wowborg:v170**
   (`8085e4e1-e211-4958-9477-a15a148490b9`, source `2c32d05`).
   Six-run request `xreq_b07f6d6c-b7a5-4c0e-95b1-fa668c05d442` produced one
   ramp-base run. The native 94-yard pass action was accepted, but after 30 seconds it returned the
   unchanged frame with `action_status=timeout`; the synchronous action is too long to consume the
   whole pass. Two runs died earlier in Tanaris and three stopped earlier on route progress/frame
   failures. The active source retains native jump inference but restores the 17 canonical points
   as action boundaries, so each `move_to` executes and settles one steep edge at a time.
   That candidate is uploaded inert as **wowborg:v171**
   (`2b445ece-e7f8-43a5-83cc-f773df84c0d0`, source `3818f5d`).
   Six-run request `xreq_24966ee6-6f57-4ebe-bad2-ce3a5946f9cf` produced one
   ramp-base run. Its first edge-bounded native action also returned the unchanged frame after 30
   seconds, proving native `move_to` cannot execute this steep component. Four runs stopped earlier
   on route progress/frame failures and one died at ramp-turn. The active source keeps the
   canonical edge bearings but uses the public action contract's explicit one-shot `jump` bit on
   their forward vectors. All non-steep movement and hazard decisions are unchanged.
   That candidate is uploaded inert as **wowborg:v172**
   (`be0167b1-0275-4c39-aabf-a50fc8f0be19`, source `772672c`).
   Six-run request `xreq_38156220-9ef8-4f8d-8d85-4454b8347805` kept every run
   alive. One reached ramp-base at 180.9 seconds, then climbed through ascent point 08 (above z111)
   before the 270-second deadline—the first verified steep-pass progress. It still incurred 49
   avoidance starts, 13 side switches, and 33 retreats; three other runs stalled near Tanaris
   waypoint 3. **wowborg:v173** (`1fdac500-2bbf-4024-87f7-a9fd9be76a22`, source
   `54459a9`) is uploaded inert to time-align observed player and patrol motion for segment
   clearance. It retains the 20-yard safety threshold and conservative swept fallback whenever
   timing is absent; only false crossings that occur at different times become clear. Six-run
   request `xreq_80c311ec-8cbf-4e9e-b817-a52772c8bc3d` kept every run alive,
   but none reached ramp-base: three stalled at `tanaris-north-road-9`, two stopped at road point 3,
   and one stopped at road point 2. The timing branch is dropped from the active source. Navmesh
   recon shows that the final road-9 approach rises from z13 to z34 at up to 1.21 slope, and all
   three road-9 runs stopped at the same foot of that climb. **wowborg:v174**
   (`73f5f8cb-d6e9-41f4-ab30-e43e73208496`, source `fcb8d78`) is uploaded inert with that measured
   climb-base anchor and explicit jumps on the missing edge. Six-run request
   `xreq_b10b0b04-3bc4-4d63-8264-19353a0b3e5c` kept every run alive. Four
   reached the climb base and crossed the formerly impassable climb; one continued through
   mountain-pass ascent point 15, the best frontier yet. Three overshot road point 9 vertically at
   z48–71 instead of z29. **wowborg:v175** (`069a5fea-de02-4969-afd2-62c6b83f585b`, source
   `63413c5`) is uploaded inert with that path split at the navmesh's measured z34 crest, ending
   explicit jumps there before walking downhill to road point 9. Six-run request
   `xreq_ea688a49-44e2-4e64-b96f-71301d0e958b` produced three correct
   crest/downhill crossings that reached mountain ascent points 14, 6, and 6. One climb run still
   overshot the 40-yard jump edge; one stopped earlier; and one died near road point 3 after a
   Glasshide Gazer closed to 4.05 yards. **wowborg:v176**
   (`adb98318-5ce8-40a3-856e-0e8b9feaccc7`, source `25a2666`) is uploaded inert with the long climb
   jump replaced by six measured navmesh sub-edges. Six-run request
   `xreq_28f32e93-23b2-4a5e-97a4-6a3251e93513` falsified that design: no run
   cleared the climb, two repeated the first short jump to z78–95, and one reached its first sub-edge
   before falling into combat and dying. The active source restores v175's one crest edge and allows
   that crest alone to use the existing northing-pass envelope; v175's failed climb was already
   inside its 20-yard northing, 60-yard lateral, and 10-yard vertical limits. That candidate is
   uploaded inert as **wowborg:v177** (`829c6ecb-de49-4441-bd04-a163c58a4e94`, source `4a704fd`);
   six-run request `xreq_588c79bb-5b5b-429a-a168-6ffb5e21d05f` kept every run
   alive. All four climb runs acquired the crest in 1–2 seconds; three reached main mountain ascent
   points 14, 12, and 5, and one completed the mountain crest at 252.2 seconds and reached the
   Shimmering Flats south ramp—the first verified Tanaris exit. The batch still emitted 14–30 false
   retreat-blocked events per run because turn-only retreat controls counted as failed translations.
   **wowborg:v178** (`6c29b6e2-131f-44c7-8c8b-44219b11622a`, source `69fff04`) is uploaded inert and
   counts only actual retreat translations toward the three-pulse blocked limit. Six-run request
   `xreq_86a8c77f-c292-4e22-b87a-509d1e2fab52` reduced blocked retreats to zero
   in five runs, but caused 58–107 completed retreats in four full runs. Only one reached the road
   crest, at 264.3 seconds, and one run died. The active source reverts this branch to v177 retreat
   behavior. It changes only steep-edge settling: v177's successful 94-yard mountain ascent took
   90.45 seconds with 509 control pulses and 509 extra waits, so steep edges now use the existing
   every-eighth-pulse settle cadence. This is uploaded inert as **wowborg:v179**
   (`f2e48def-d816-4ce0-bb60-8e95ce4e8f85`, source `27a277f`). Six-run request
   `xreq_18b0176a-d269-42bf-9e0a-554a1fb71d55` shortened the successful
   mountain ascent from 90.45 to 62.03 seconds. The best run reached the crest at 222.5 seconds,
   south ramp at 227.5, and south road at 234.6, but three runs died. Two deaths expose combat
   policy failures: a proactive Scorpid chase admitted a Glasshide Basilisk at 2.55 yards, while
   another looped at 2.177 yards above the 2.0 attack gate. The active source requires the Scorpid
   to be the only hostile within 30 yards and attacks from 2.5 reported combat yards. The third
   death was explicit falling after south road and remains the next route-safety task. The combat
   candidate is uploaded inert as **wowborg:v180**
   (`2e1e0cdb-d12b-46dd-87f3-761fb55fa023`, source `836f8dd`). Hosted request
   `xreq_15b75738-8083-42fc-b01a-d23834eedeb8` kept all six runs alive; neither prior ramp-combat
   death recurred, and its only recorded Scorpid fight cleared in about 3.4 seconds at full health.
   The batch did not re-reach the south road: four runs stalled earlier, one timed out at road-9,
   and one held a mixed ramp hazard for about 123 seconds. The active source now makes the existing
   south-ramp to south-road leg terrain-constrained, replacing V179's fatal one-second open strides
   with the existing 0.25-second precise cadence. That candidate is uploaded inert as
   **wowborg:v181** (`a7e551aa-538f-4b83-9476-9d8a8baf4cd9`, source `9efa623`); its hosted
   request `xreq_f8160381-9848-4f7b-a1a9-e20c6d5799b2` kept all six runs alive but did not reach the
   south-ramp frontier. Two runs held at the ramp turn for about 111 and 130 seconds because a
   qualifying Scorpid was not literally the only hostile within 30 yards. The active source now
   admits the same single sub-eight-yard level-40/41 non-elite Scorpid when every other nearby
   hostile's projected patrol segment remains at least 12 yards from the player. That preserves
   roughly twice the observed 5-7-yard ordinary aggro range while allowing a calibrated fast kill.
   The candidate is uploaded inert as **wowborg:v182**
   (`a536822a-16cd-4170-b9cc-8ff869198e16`, source `e3e05e3`). Hosted request
   `xreq_ecff12e4-6234-466d-950f-8d4171c8d4f8` kept all six runs alive; two proactive fights cleared
   safely in 5.7 and 6.2 seconds with no extra pull. One run reached ascent 16 with only about 10
   seconds left in the fixed 270-second horizon. The full route is 6,662 yards, and the current
   20-yard predicted-clearance floor drives repeated 30/45/60-yard detours despite the pinned
   5-7-yard ordinary aggro radius. The active source lowers that floor to 12 yards, preserving an
   approximately 2x margin while reducing avoidable route churn. The candidate is uploaded inert
   as **wowborg:v183** (`b3bfe4a6-940a-4677-8e43-1dfe4dc07bed`, source `e49641a`). Hosted request
   `xreq_aeff773d-fffe-4815-b84f-2c2cc18e92c7` kept five of six runs alive. One reached south road
   at 241.4 seconds but accumulated fall damage throughout the quarter-second descent and died when
   the final damage landed 1.34 seconds after movement stopped. The active source now exits Travel
   Form, enters Cat Form for that one descent, and makes south road an exact three-yard anchor;
   Travel Form resumes on the flats. The candidate is uploaded inert as **wowborg:v184**
   (`1cfe5fa3-18ec-43f6-9c8a-50d151f19d2f`, source `e85a02a`). Hosted request
   `xreq_bb91cc02-83a0-4c16-a291-4e0b341a2f04` did not reach the descent, so Cat Form remains
   unexercised. Five runs survived; one pulled a Glasshide Gazer at 8.75 yards under the 12-yard
   global clearance floor, collected additional attackers while escaping, and died. The active
   source restores ordinary road clearance to 20 yards while retaining the local 12-yard
   projected-add gate for the calibrated Scorpid fight. The candidate is uploaded inert as
   **wowborg:v185** (`639852fd-e3b7-4d49-bffa-efcf58f77165`, source `2295773`); its hosted
   request `xreq_d0b5f50f-2c79-496f-8ee9-7caab588597d` kept 10 of 12 runs alive but did not reach
   the south-road descent, so Cat Form remains unexercised. The two deaths each began as one
   ordinary attacker: a Glasshide Basilisk at 22.4 yards with 2,633/2,754 health and a Scorpid
   Dunestalker. Eight other runs entered the existing ramp feral routine without dying. The active
   source now uses that maintained rotation reactively against exactly one visible, ordinary,
   non-elite level-49-or-lower attacker on any route leg. Multi-attacker combat still escapes;
   proactive acquisition remains limited to the constrained ramp's safely isolated Scorpid. This
   is uploaded inert as **wowborg:v186** (`1c5e7a88-5b41-42e2-b0ba-fb10ee28c898`, source
   `e303664`). Hosted request `xreq_20f622df-e5c0-42bf-9758-5c36137fd859` kept 11 of 12 runs
   alive. Reactive level-42-49 kills generally completed in 3.5-4.8 seconds, validating combat as
   a fast fallback. The sole death was a proactive level-41 Scorpid that settled at 2.652 reported
   combat yards; the 2.5-yard gate then waited without attacking until death. No run reached the
   Cat descent. The active source raises only that melee-engagement gate to three yards. It is
   uploaded inert as **wowborg:v187** (`9ef2d2d6-0b4a-4e27-961f-06faf57eb0b9`, source `13c001b`).
   Hosted request `xreq_a8fcb3ec-48c5-42c6-a8ce-69686fc3f655` again kept 11 of 12 runs alive. Its
   sole death attacked a Glasshide Basilisk from 3.05 yards but dealt zero damage, then retried a
   failing Rake every 1.5 seconds until death. The active source restores the proven 2.5-yard gate
   and uses existing precise steering to close on the exact attacker while already in combat,
   rather than waiting for it to step closer. This is uploaded inert as **wowborg:v188**
   (`f2e341fe-45cb-4d16-b5a4-89080938294c`, source `e1e9298`); hosted evaluation is pending.

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
