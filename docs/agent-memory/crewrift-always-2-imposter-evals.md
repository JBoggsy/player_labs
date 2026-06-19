---
name: crewrift-always-2-imposter-evals
description: "For Crewrift imposter evals always pin a 2-imposter config, never 1-imposter"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f70c9801-7ee7-499b-97f9-4fd0848a6b8e
---

In the Crewrift lab, **always run 2-imposter evals when pinning roles for imposter
work — never 1-imposter.** Use crewborg slot 0 = imposter plus one partner-imposter
slot, the rest crew (matches real 8-player league games with 2 imposters).

**Why:** 1-imposter games remove the partner dynamics that much of crewborg's imposter
strategy actually targets — e.g. a partner killing in an obvious spot, getting reported,
and the report **resetting every imposter's kill cooldown**. I ran a v22-vs-v24 "kill
sooner" A/B in a 1-imposter config and it couldn't test the very hypothesis the changes
were built for (there was no partner), which James flagged. The clean-solo-kill appeal of
1-imp doesn't outweigh that it can't validate partner-aware behaviour.

**How to apply:** In the experience-request `game_config_overrides.slots`, set two slots
to `imposter` and the remaining six to `crew`, and **pin crewborg's roster participant to
one of the imposter slots** (since metta #15572 the body is a single `roster` list —
`{"player": {"policy_ref": "crewborg:vN"}, "slot": 0}`; roles attach to seats, so the pin
is what fixes its role). Measure crewborg's own kills/ejection via `results.json` by
`policy_version_id` (attribution stays clean even with a partner).
See [[crewrift-living-docs-discipline]].
