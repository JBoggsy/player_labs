---
name: cue-n-woo-lab
description: cue_n_woo_lab — a second player_labs game lab (text theory-of-mind game); status and locked build direction
metadata: 
  node_type: memory
  type: project
  originSessionId: b952ba45-d32f-4ce0-a227-c691de8c588f
---

`cue_n_woo_lab/` is a second game lab in player_labs, started 2026-06-12. **Cue-n-Woo
is NOT a gridworld** — despite shipping in the `cogames` image family, it's a
two-player, text-only theory-of-mind game: players interview a hidden-persona judge
(Gemma-2-9b-it FLAS-steered toward one of 61 known writing styles), then write/answer
challenge questions; the steered judge scores which answer it prefers. Full reference:
`cue_n_woo_lab/docs/cue-n-woo-gameplay.md`. No live league yet as of 2026-06-12.

Key operational fact (not obvious): the judge worker
`https://cue-n-woo-worker.softmax-research.net` is **live and serves unsigned requests**
(no auth/VPN), so you can develop and self-evaluate against the real scorer from a
laptop with no local GPU. Probe harness + findings: `cue_n_woo_lab/probe/` and
`cue_n_woo_lab/docs/probe-findings.md`.

**SUPERSEDED build direction** (orig from probes): cheap local 61-**style classifier** →
Bedrock Claude writes a short on-topic in-style answer. This is now WRONG: as of
2026-06-15 the game switched `concept_type` from `list` (61 named styles) to
**`axis_combo`** — the judge is steered to 4 randomly-chosen of **15 axes** (~287M combos,
326 atomic values; data/concept_axes/). The 61-style classifier returns near-uniform noise.
See [[cnw-axis-combo-rewrite]] for the new system + the mentalist v4 SDK rewrite. Bedrock
confirmed working in tournament pods 2026-06-15 ([[cnw-bedrock-now-working]]).
See [[crewrift-living-docs-discipline]].
