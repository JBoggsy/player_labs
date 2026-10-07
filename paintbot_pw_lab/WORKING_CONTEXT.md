# Paintbot PW working context

## Current objective and boundary

**V29 is champion and parent**, submitted by the orchestrator as
`sub_08157a74-7eb8-4d98-8f1e-ca6f3d508cf2`. I35 xolod+0.019978
[+0.011562,+0.028393], Richard+0.030296[-0.023487,+0.084079], zero episode failures.
The orchestrator explicitly overrode the +0.02 point threshold as rounding;
the frozen automated decision remains a fail. REPORT-35 records both distinctly.

Champion: `jb-pw-opt:v29`, UUID `cf05fa48-71e3-408c-96cf-ed1ce74409ea`,
build `e42b7834-1`, source `e42b7834`. V10 is the historical fallback behavior.
Current task: VERDICT-39 analysis-only plateau review complete in
`tmp/collab/optimizer/REPORT-40.md`. No new hosted cohorts until verified balance>=14000
or an orchestrator-confirmed field/engine change. No auto-resume at11000. Explicit follow-up exception: build i41 refuse-and-counter on guarded v29 and run
ONE cohort400Richard+100xolod perarm; all other cohorts remain held until>=14000. V29 remains champion; all future builds retain
the map guard. No optimizer submission; account hard floor10000.

Player James Botts: `ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce`.
League: `league_ae677105-0ab8-4561-81ec-c9cf6735821c`.

Current source: i41 refuse-and-counter on guarded v29, source593d9c1a/build593d9c1a-1.
Uploaded v34 UUIDd0757ce1-9af2-441e-bef4-b87ab4ba8248; all compiler gates passed.
Two capture cogs and six separated staging posts, public distant-capture transition
releases bounded counterattack;40s deadline returns to baseline. Phase/trigger tracing
is present. Exact map-guard unit unchanged. Local recording188activations/16seats,
3634valid telemetry lines,0failures; counter release not yet seen in short recording.
ONE authorized cohort400Richard+100xolod perarm versus fresh v29,1000games/~500credits.
I39/v33 is rejected: Richard+0.016600[-0.038049,+0.071249],
xolod+0.004696[-0.007212,+0.016603]; its terrain planner is not inherited.
Guard-only child build `1fe285df-1` passed and uploaded as v30; not submitted. **Do not submit v30 alone.**
Standing orchestrator rule: retain the geometry guard in v31/v32 and every future
candidate, and ship it only with the next real gameplay improvement. The current
league uses one map; the orchestrator estimates a submission sigma reset costs
about6MMR, so this guard alone does not justify replacement. The orchestrator owns
fieldwatch and will fast-track a response if the map/variant changes. Existing
v31/v32 classifier units were verified to include the same exact geometry guard.
Its26/26state-hash checks through800ticks match v29 on Heartwick and v10 on all12
shipped alternate maps, both sides; compiler28-seed Heartwick play is identical.
Dodge rebase i37 build `757ec5d2-1` passed and uploaded as v31, UUID
`f56b16e7-c204-4335-ab29-487755205821`. Its fresh400Richard+200xolod per arm
comparison vs v29 is complete and rejected: Richard-.037619[-.093054,+.017817],
xolod+.007471[-.004326,+.019268],0episode failures. Do not inherit it.
The submitted v29 artifact is immutable and retains its original heart-count-only guard.
V28 dodge remains recoverable at `4f0e5d4e-1`; do not substitute its v10 parent.

## Final robust-bundle result

I31 tested v10 + v22 frontier pairs/direct capture + v25 glory collection, excluding
v24 pursuit. All 1,200 games scored, zero episode failures; 600 creation-preview credits.
Fresh controls, balanced sides, one game per observation, nominal normal 95% intervals.

| Opponent | Games per arm | v26 minus v10 score | 95% CI |
| --- | ---: | ---: | --- |
| xolod:v14 | 300 | +0.000372 | [-0.005255, +0.006000] |
| finist:v2 | 100 | +0.003725 | [-0.002304, +0.009754] |
| Richard:v1 | 200 | +0.019763 | [-0.051979, +0.091504] |

Both gate conditions failed: xolod lower bound is below -0.005, and neither secondary
opponent has a positive lower bound. This does not establish equivalence or universal
harm; it establishes no supported replacement under the fixed design. Candidate health
was checked in 16/600 episodes with zero bad seats; 584 optional status artifacts are
unknown. Do not equate zero episode failures with complete seat verification.

Full evidence: `tmp/collab/optimizer/REPORT-31.md`, `i31-hosted-results.json`,
`i31-submission-decision.json`, and `episode_data/optimizer-i31/requests/manifest.json`.
These local evidence directories remain ignored by git; the final findings above are durable.

## Supported champion lineage

All deltas below use fresh hosted controls at margin scale 600. Different cohorts cannot
be added into a cumulative causal estimate. See [TENTATIVE_LESSONS.md](TENTATIVE_LESSONS.md)
for dead levers, limits and follow-up criteria.

| Retained version | Change and measured benefit | Evidence |
| --- | --- | --- |
| v3, build `2a539036-1` | Persistent grenade charge; block disarmed starts and preserve safe release. Versus v2, field score +0.026192 [-0.015124, +0.067509], 72/72 vs 69/72 wins. Retained under the then-authorized operational/point-estimate rule, not proven statistical superiority. | REPORT-2 |
| v6, build `21b9c416-1` | Update committed grenade aim and required charge with eligible live targets; keep last safe point otherwise. Richard +0.197569 [+0.072426, +0.322713], 56/96 vs 36/96 wins. | REPORT-6 |
| v8, build `5cee1447-1` | Finish cover-cog captures instead of leaving for an outside post when own capture starts. Richard +0.133064 [+0.009925, +0.256203], 65/96 vs 50/96 wins. | REPORT-10 |
| v10, build `7faadaa4-1` | Use physical squared distance, not HP-weighted target ranking cost, for both spray range gates. Independent Richard confirmation +0.098137 [+0.017251, +0.179024], 152/200 vs 130/200 wins. Xolod -0.006267 [-0.022531, +0.009997]. | REPORT-14 discovery; REPORT-18 confirmation |

Reports are under `tmp/collab/optimizer/`. V8 is a research-lineage parent; v10 inherits
these retained changes, not every intervening upload. The tiny i18 zhar result (4/arm,
all wins) was explicitly judged noise by the orchestrator; no universal guard-gain claim.

## Pairings and rating

Canonical source-verified mechanics: [mechanics.md §1](docs/mechanics.md#1-the-one-thing-to-get-right-winning-glory-and-rank).
Recorded league settings: OpenSkill, `margin_scale: 600`, `round_scoring_rule: mean`,
`team_n` / `elo_softmax` matchmaking, temperature 100. MMR is player `mu - 3*sigma`;
soft outcome is `clamp(0.5 + glory_margin/1200, 0, 1)`. Champion replacement widens sigma
to at least 6; immediate ordinal cost is `3*max(0, 6-old_sigma)`, not a fixed five points.
An experiment upload does not cause this submission penalty.

Pairing frequency changes with ratings. Rounds 849–852 had four of our games, all vs
Richard; rounds 871–876 had seven, five xolod and two finist (all wins). These are observed
samples, not permanent opponent weights. A 520–0 win rates about 0.933, not 1.0.
Xolod is near an observed margin ceiling for tested levers, not a proven mathematical
ceiling. Faster wins alone do not guarantee more rated margin: awards and clamping matter.

V22 is a conditional reserve: Richard +0.059869 [+0.009132, +0.110606] at 400/arm,
but xolod -0.013229 [-0.026098, -0.000361] at 48/arm (REPORT-27). Reconsider only against
a changed pairing mix with fresh controls, never submit solely from the old Richard result.

Latest six-round check (888–893, all completed): **Richard 4/7 (57.1%), xolod 3/7
(42.9%), no other opponents**; exact own v10 identity verified in all seven games. All four
Richard games were in rounds 891–893, so the sample already shows a recent shift. This is
above the orchestrator's one-third trigger. Recommend a fresh v22 vs v10 A/B, Richard-focused
with a substantial xolod guard, before any submission. The seven-game mix is uncertain and
the old effects may not replicate; this triggered i32, whose final result was inconclusive; VERDICT-32 then opened the new Richard campaign. Evidence:
`tmp/collab/optimizer/standby-six-rounds.json` and `standby-pairing-mix.json`.

## Environment and operational handoff

Tools and native library target `coworld-v0.3.124` / `7a29ed7a`, rules 49. The change
from 0.3.123 is training-map infrastructure, with no hosted rules/BASIC/seat-view change.
On this handoff, deployed-ref --write confirmed the existing pin; tools and native library
were rebuilt. Quick v10 check: seed 7, both sides vs pinned upstream, two complete games,
zero bad-seat matches, native/headless hashes match on both sides. This is runtime evidence
only; no competitive requalification was needed. Evidence: `tmp/collab/optimizer/standby-*`.
Coworld 0.1.57 and softmax-cli 0.26.38 were release-checked during i31; refresh before
future CLI diagnosis. Broader neural/oracle references retain `PW_DOCS_SHA=118e1619`.
M3 comms remains inactive and unqualified on current Bassy; see [comms.md](strategy/comms.md).

I32–i35 are complete; their workers exited. I37/i38 complete and fail their gates. I39 is complete/rejected; its workers exited. I41 is the only authorized active cohort. Admission/results workers exit on terminal work;
field_watch.py is stopped by explicit handoff. Dashboard 8810 stays off. Do not poll
terminal requests for optional artifacts. Future authorized polling/retries: at least
120 seconds, bounded artifacts, finite exit. No hosted self-play. Local games establish
runtime/activation/mechanisms, never competitive superiority. No optimizer league
submission, public writes or git push without authorization.

Credits: VERDICT-39 holds all new cohorts until verified balance>=14000 or an
orchestrator-confirmed field/engine change. `tmp/collab/optimizer/hosted-hold.json` blocks
the local admission helper except for the explicitly whitelisted i41 cohort.
All other cohorts require balance>=14000 under the latest orchestrator instruction.
After release, one hosted cohort at a time. Future cohorts use400Richard+100xolod games
per arm (1000total, approximately500 preview credits). I39/v33 is grandfathered at
400Richard+200xolod per arm; finish its frozen1200-game design unchanged.
After the VERDICT-39 hold is released, pause NEW cohorts below11000 until next refill;
refill is approximately1429/day at00:00UTC. Preserve the10000 hard floor throughout.
The orchestrator reported12337 when setting this rule; re-read actual balance before
admission. Local diagnosis/build preparation may continue while hosted admission is
paused. Finite workers only, no faster than120s polling. Requests/previews remain in
frozen manifests; account observations in `tmp/collab/optimizer/credit-observations.jsonl`.
Net account movement includes other spending and is not attributable cohort cost.
