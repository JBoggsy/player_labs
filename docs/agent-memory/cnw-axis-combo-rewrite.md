---
name: cnw-axis-combo-rewrite
description: Cue N Woo switched to axis_combo concepts (4 of 15 axes); mentalist being rewritten as v4 on the Player SDK with a per-axis classifier
metadata: 
  node_type: memory
  type: project
  originSessionId: 974bff52-7d92-49d3-b571-eddaad9f40a1
---

**The game changed (2026-06-15).** Cue N Woo's hidden concept switched from
`concept_type=list` (one of 61 named writing styles) to **`axis_combo`**: the
judge is FLAS-steered toward **4 randomly-chosen of 15 axes**, one value each,
joined with "; " (e.g. `technical; evidence-first; frontier town; sterile`).
15 axes / 326 atomic values live in the game repo `v2/coworld/data/concept_axes/`
(register, syntax, rhetoric, cognition, epistemology, morality, social, persona,
emotion, genre, domain, sensory, time, object, place). ~287M combinations, but
FACTORED — the tractable problem is per-axis value inference, not whole-concept.
Other deltas: round_timeout 300->600s, worker URL is now
`cue-n-woo-fleet.softmax-research.net` (was `-worker`), `reveal_concept_to_clients=false`
(concept hidden from live state but present in the replay's `hidden_concept`).
Scoring logic UNCHANGED. Full writeup: `cue_n_woo_lab/docs/axis-combo-system.md`.

**Why mentalist loses (rank 3/3):** the 61-style classifier has no valid target
(returns ~uniform noise), AND the new judge rewards concrete terse nouns
("A brass key" p=0.95) over mentalist's florid in-style prose (authored-question
p=0.00-0.17). Both load-bearing components are mis-aimed.

**The rewrite (mentalist v4).** Full rewrite on the Player SDK. Design doc:
`cue_n_woo_lab/docs/designs/mentalist-v4-sdk-rewrite.html` (HTML, open in browser).
Key decisions: adopt the SDK's game-agnostic helpers — `run_message_bridge` (P2,
bakes in the exit-0-on-abrupt-close rule), `player_sdk.llm` (P3, client/model/usage
selection; but it's text/JSON not tool-forced, so keep our own tool path),
`TraceConfig` (P5), `TraceEvent.step` (P4), telemetry namespace (P1) — but NOT the
tick-based AgentRuntime (built for gridworlds; crewborg+suspectra both bypass it).
These P1-P5 SDK generalizations are MERGED to players main (#67-#71, tip fdf2987)
and locked into the lab (uv.lock). New classifier = per-axis inference over the 15
axes. **Open gate:** axis separability from 3 judge answers is being measured by
`probe/probe_axis_recovery.py` against the fleet worker (results -> docs/probe-findings.md).
Related: [[cue-n-woo-lab]], [[cnw-bedrock-now-working]].
