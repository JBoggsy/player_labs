# stencil version log

Read this before assuming what a version contains. Format mirrors
`ctf_lab/ctf/beacon/VERSION_LOG.md`: one entry per uploaded version — what
changed, why, and what the evidence said.

## v7 — distinct homeward-ranked defensive posts, uploaded 2026-08-04

Immutable policy-version UUID: `91cd9b6d-df02-4887-8ed0-24cc8379030b`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Deduplicates the generated post union and ranks it by distance from the
  team's heart, then assigns defender seat N to rank N. This fixes v6's
  duplicate assignment while keeping the behavior explicitly defensive.
- Defenders travel to and hold their assigned post, sweeping toward the
  associated opponent front. Heart-theft interception remains higher priority;
  attackers are unchanged; generic choke cover is the no-post fallback.
- `STENCIL_DEFENSIVE_POSTS=0` disables the behavior. Traces expose assignment,
  duck cell, opponent, score, travel/hold ticks, and fallback count.

Four paired hosted `2v2` episodes used the same standard-sides map (seed 707),
with v7 and v5 each playing both colors. All completed without failures. Across
12 v7 defender-episode assignments, every defender emitted `to_post`, 10 reached
`hold_post`, all assigned positions were distinct within a team, and fallbacks
were zero; all 20 attacker-episode assignments remained unposted. The result
split 2-2 and is too small for a win-rate conclusion.

Requests: red v7 `xreq_688bd557-c881-479d-995e-988e12911cef`; blue v7
`xreq_0e1f7106-58ca-4263-9f7e-4cbea6a97a94`.

## v6 — initial defensive-post assignment, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `794f3db1-f552-43d5-b1a8-f9b7f9ec1a2e`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Each defender attempted to snap its hold target to the generated post nearest
  its old seat-spread lane. If a map produces no usable post,
  that defender falls back to the old geometry-derived choke cover.
- Posted defenders sweep toward the opponent front used to generate their
  position. Heart-carrier return and heart-thief interception remain above the
  posting rung in the objective ladder.
- `STENCIL_DEFENSIVE_POSTS=0` disables the behavior for controlled comparisons.
  Full traces expose the assigned position, duck cell, opponent, post score,
  travel ticks, hold ticks, and fallback count.

Hosted tracing found two problems. `1v1` never reaches the defender rung because
its three enemy lives immediately activate the higher-priority convert hunt, so
its 7-4-1 result against v5 is not post-defense evidence. In paired `2v2`, post
behavior did activate but defender seats 0 and 1 sometimes chose the same point.
v6 was rejected and never submitted. The standard-corners four-team probe did
confirm activation across all eight defenders with zero fallbacks.

Requests: `xreq_4aa4eb07-39a5-4488-8b7f-df9f055be511`,
`xreq_31745e93-1855-4931-b952-b1347a243130`,
`xreq_59840e62-4ca5-40ec-99a5-e876be8d9c7c`, and
`xreq_36ed443a-de7b-41fa-b6e5-c745c505ee4e`.

## v5 — generated own-team post knowledge, uploaded 2026-08-04

Immutable policy-version UUID: `6f571639-7a5b-42b7-bf2e-113be8377602`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Generates post knowledge online from the episode `WorldMap`; no fixed map
  coordinates or authored POIs return.
- For each opponent front belonging to the agent's own team, finds cover near
  the opponent→home shortest-route corridor, distributes candidates across 12
  route-progress buckets, scores nine forward firing rays, pairs the firing
  cell with a nearby reachable duck cell, and retains up to six posts with
  120px spatial separation.
- `navigation_map` schema v2 traces each candidate's combined, sightline,
  corridor, and duck-contrast scores plus selected firing rays and duck cells.
  `tools/render_nav.py` adds a front selector, candidate heat, post labels,
  firing rays, duck links, and hover score inspection.
- Diagnostic only: no gameplay behavior consumes posts in v5.

Five pinned-seed hosted probes on canonical Paintbot 0.7.183 all completed
with zero failed episodes:

| map | XP request | grid | fronts / posts | post pass |
|---|---|---:|---:|---:|
| small sides, seed 101 | `xreq_4c5e4d79-b248-4cbc-8f95-bc7ee428f283` | 131x70 | 1 / 3 | 20.3 ms |
| large sides, seed 202 | `xreq_381f0f56-5fa7-4a81-b9f9-ba7e6ea25a13` | 200x107 | 1 / 4 | 109.0 ms |
| standard corners, seed 303 | `xreq_79e63a93-e2d2-4770-93b8-0023740c5a14` | 120x120 | 3 / 10 | 164.0 ms |
| huge plus, seed 404 | `xreq_e600af70-768a-4d63-948f-379bc9fb5442` | 216x216 | 3 / 15 | 1,157.9 ms |
| giant corners, seed 505 | `xreq_8d02bb4b-29fe-45aa-acf1-911fe083c676` | 312x312 | 3 / 17 | 2,775.6 ms |

The artifact downloader exhausted each otherwise-complete episode because the
separate results artifact and policy-log listing were unavailable, but the
requested navigation ZIPs were present for 2/2, 2/2, 16/16, 16/16, and 15/16
seats respectively; representative traces rendered successfully.

## v4 — bounded duck-ray probe, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `88ccf5d1-45e0-4e59-b257-19b3fa41167f`.
Reduced duck contrast from all nine rays to left/center/right threat rays and
24 shortlisted candidates. Hosted post time improved to 43 ms small, 220 ms
large, 687 ms standard, 4.87 s huge, and 14.0 s giant. Rejected because every
agent still computed all 12 four-team fronts. Never submitted.

## v3 — route-progress candidate bound, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `69d03cb3-cfe2-4a7f-a35b-f88b4e59c75d`.
Bucketed corridor cover by route progress before exact firing-ray evaluation.
This fixed two-team maps but left exact duck testing combinatorial: hosted post
time was 129 ms small, 357 ms large, 1.46 s standard, 18.7 s huge, and 23.9 s
giant. Never submitted.

## v2 — unbounded post-metric probe, uploaded then rejected 2026-08-04

Immutable policy-version UUID: `1ab24204-1582-4cc9-9fdd-26a61432c3f8`.
First complete implementation of the agreed firing/duck metric and viewer.
Hosted tracing exposed the scaling failure: every corridor cover cell was
ray-scored before shortlisting, costing 818 ms standard, 3.72 s huge, and
29.6 s giant. Kept only as diagnostic evidence; never submitted.

## v1 — bootstrap + navigation diagnostics, uploaded 2026-08-04

Immutable policy-version UUID: `8af80cb6-022a-4d1b-b1eb-dfb08374b826`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

Forked from ctf_lab beacon (post-v67 lineage), adapted for Paintbot, then
ported exactly to native Nim:

- **NEW `worldmap.nim`**: episode-scoped world model built online from the
  walkability sprite + `game teams` + `endzone` markers + planted-heart
  sightings. Eroded 8px nav grid (SAT-based footprint erosion), cover cells,
  lazy per-goal Dijkstra flow/route fields, derived tactical anchors
  (choke/rally/spawn-aim/inside-base). Replaces `nav.npz` + `bake_map.py` +
  `poi.py` + `plan.py` + `posts.py` wholesale.
- **Multi-team**: 2-or-4 colors from the wire, slot-mod-teams dealing with
  self-sprite color lock, per-color hearts + retirement tracking, steal target
  = nearest live enemy heart, convert trigger generalized to the weakest enemy
  team. Roster-aware roles/squads start from the minimum muster consistent with
  the seat and grow only from observed identity badges; campaign map size is
  explicitly not used as a muster proxy.
- **Perception**: direct walkability pixel decode (supersnappy raw block),
  wire-marker parsers, all-color players/hearts/shouts/score-chips.
- **Items**: spawn table discovered from sightings (generator placements are
  per-map); seat-keyed fixed assignments removed.
- Ported intact: aim/lead/fire-gate/FF-guard, peek-fire-duck, firefight scoring
  + focus claims, hearing, chat protocol (grid dims from the map), danger field,
  tracing, and all 91 `STENCIL_*` environment variables.
- Cut from v1 (deliberate): posts, battle plans, POIs, anti-turtle; squad
  command remains off by default as in beacon v29+.
- Local-only fast-ready transport is available behind `STENCIL_FAST_READY=1`;
  the native self-play harness enables it to remove the 24 Hz pacing sleep.
- Opt-in `STENCIL_TRACE_NAVIGATION=1` telemetry records the exact eroded nav
  grid, cover, tactical anchors, and every lazily cached Dijkstra distance/hop
  field. `tools/render_nav.py` turns a JSONL trace or hosted artifact ZIP into
  a standalone interactive viewer; `self_play.py --visualize-nav` captures the
  local trace without enlarging routine telemetry.
- Synced against canonical Paintbot 0.7.182 (`3151a47`): the two changes since
  the 0.7.180 parity corpus were replay-viewer hashing and campaign docs, with
  no simulation/wire delta. The audit corrected production facts that do not
  follow engine defaults: deployed gun range is 1300px, campaign cell size can
  override `4ffa8`'s giant default, and absence-based item tracking uses the
  narrowest deployed vision cone (45 degrees).
- v1 release build updated to canonical Paintbot 0.7.183 (`95bb768`), whose
  server optimization retains object placements per viewer and emits only
  changed placements after initialization. Stencil already consumes Sprite-v1
  as retained state; the first hosted XP batch is the runtime contract check.
- Differential replay across six representative configurations matched
  169,235 controller/chat decisions exactly. The legacy Python oracle used for
  that proof is preserved in Git commit `1129931` and was removed from `main`
  after the port was accepted.

Hosted startup proof on canonical Paintbot 0.7.183 (`95bb768`): one bounded,
40-gameplay-tick XP episode each for `default`, `2v2`, `4ffa`, and `4ffa8`.
All four requests completed with zero failed episodes; every Stencil seat
uploaded telemetry, and representative artifacts contained the navigation map,
3/3/6/7 lazy flow fields respectively, plus a snapshot on every observed
policy tick. These deliberate timeout draws validate the upload/runtime,
retained Sprite-v1 stream, map construction, full trace, and artifact-rendering
boundaries—not competitive strength.
