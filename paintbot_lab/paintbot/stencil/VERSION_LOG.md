# stencil version log

Read this before assuming what a version contains. Format mirrors
`ctf_lab/ctf/beacon/VERSION_LOG.md`: one entry per uploaded version — what
changed, why, and what the evidence said.

## (unreleased) — v1 bootstrap, 2026-08-03

Forked from ctf_lab beacon (post-v67 lineage) and adapted for Paintbot:

- **NEW `worldmap.py`**: episode-scoped world model built online from the
  walkability sprite + `game teams` + `endzone` markers + planted-heart
  sightings. Eroded 8px nav grid (SAT-based footprint erosion), cover cells,
  lazy per-goal Dijkstra flow/route fields, derived tactical anchors
  (choke/rally/spawn-aim/inside-base). Replaces `nav.npz` + `bake_map.py` +
  `poi.py` + `plan.py` + `posts.py` wholesale.
- **Multi-team**: 2-or-4 colors from the wire, slot-mod-teams dealing with
  self-sprite color lock, per-color hearts + retirement tracking, steal target
  = nearest live enemy heart, convert trigger generalized to the weakest enemy
  team, roster-aware roles/squads (4 or 8 seats/team inferred from teams + map
  size).
- **Perception**: + walkability pixel decode (cramjam raw snappy), wire-marker
  parsers, all-color players/hearts/shouts/score-chips.
- **Items**: spawn table discovered from sightings (generator placements are
  per-map); seat-keyed fixed assignments removed.
- Ported ~intact: aim/lead/fire-gate/FF-guard, peek-fire-duck, firefight
  scoring + focus claims, hearing, chat protocol (grid dims from the map),
  danger field (Voronoi-ish home-half init), tracing, tunables registry
  (env prefix `STENCIL_*`; FIREFIGHT/FOCUS_CLAIMS default ON).
- Cut from v1 (deliberate): posts, battle plans, POIs, anti-turtle, squad
  command layer (stays OFF as in beacon v29+).
- Tests: 20 passing (`paintbot/stencil/tests/`) including an end-to-end
  synthetic-frame pipeline smoke test.

Never uploaded; no hosted evidence yet.
