# stencil version log

Read this before assuming what a version contains. Format mirrors
`ctf_lab/ctf/beacon/VERSION_LOG.md`: one entry per uploaded version — what
changed, why, and what the evidence said.

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
