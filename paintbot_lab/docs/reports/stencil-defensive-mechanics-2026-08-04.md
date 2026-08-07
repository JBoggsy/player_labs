# Stencil defensive mechanics — 2026-08-04

> **Historical experiment record.** “Accepted” and “current” below refer to
> this experiment's cutoff. See `../../WORKING_CONTEXT.md` for live state.
> Its GV36 32-slot/five-slot aim claims are correct historical evidence, not the
> current game contract. GV40 restored continuous headings at 5 brads per tick.

## Verdict

`stencil:v21` is the accepted upload and keeps Stencil's strategy fixed. The
accepted mechanics are the live 32-slot/five-slot aim controller, generated
homeward cover posts, defender-only heart-threat gun-target scoring, and
immediate engagement of a visible high-confidence heart carrier; full traces
expose aim, fire-gate, post geometry, and target-score components. It is
uploaded with full artifact tracing and is **not submitted**.

The aim fix is a clear improvement. Forcing posts farther forward is not: the
locked-map A/B sharply reduced shots, hits, kills, and hit rate, so v12 restores
the homeward-ranked selector and retains the forward/heart-distance fields only
as observability. A second, fresh 18-episode-per-arm search rejected five more
mechanics candidates; none improved defender outcomes. v19 kept their added
diagnostics and viewer improvements, then v20's heart-threat target term
improved outcomes in two fresh matched batches. v21's immediate visible-carrier
override then increased defender kills significantly and improved wins in two
more independent matched batches, so it was accepted.

## What changed

| system | accepted behavior | trace evidence |
|---|---|---|
| shooting / aiming | modular controller over 32 aim slots, moving ±5 slots per command | `aim_brads`, `aim_target_brads`, `aim_error_brads`, `aim_grid_error_brads` |
| cover usage | defenders occupy generated firing cells and retain live-threat peek/duck micro | post fire/duck coordinates and navigation-map rays |
| post identification | online, per-map cover candidates scored for sightline, corridor relevance, and duck contrast | `navigation_map` schema v2 |
| post selection | distinct posts ordered outward from the team's home center | `defensive_post*`, route distance to the heart, opponent front, forwardness |
| sightline coverage | defenders sweep toward the opponent front associated with their post | post firing rays, trace-only scored center axis, plus per-tick aim fields |

The fire trace now also records target range, nearest legal-slot angular and
lateral error, fire readiness, ray and teammate blocks, and a normalized gate
reason. The navigation viewer overlays the specific agent's assigned post,
paired duck point, and scored sightline axis.

No objective priority, role split, steal target, heart-return behavior, or
third-party FFA strategy changed.

## Hosted evidence

### Natural-map 4FFA: aim change (`v7` → `v9`)

Eight episodes per arm against the same current top-policy field: daveey
`paintbot-focusfire:v22`, richard `co-gas-paintbot-nim-richard:v4`, and Andre
`alphashot:v359`.

| metric | v7 | v9 | change |
|---|---:|---:|---:|
| wins / draws / losses | 0 / 3 / 5 | 2 / 1 / 5 | +2 wins |
| kills / episode | 4.63 | 11.13 | +140% |
| deaths / episode | 10.13 | 8.50 | -16% |
| replay hit rate | 20.9% | 51.5% | +30.6 pp |
| hearts captured | 0 | 4 | +4 |
| own-heart steals / episode | 1.13 | 1.13 | unchanged |

All nine observed thefts of v9's heart were returned before capture. Requests:
v7 `xreq_4d287287-945f-40f8-89a1-ea85a267b746`; v9
`xreq_c104f2ee-625f-4bbb-a9ee-c245f50e0c86`.

### Locked-map 4FFA: post selector (`v9` → `v11`)

Six paired maps crossed small/standard/large sizes with corners/plus layouts.

| metric | v9 homeward | v11 forced-forward |
|---|---:|---:|
| wins / draws / losses | 0 / 1 / 5 | 0 / 0 / 6 |
| shots | 285 | 205 |
| hits | 156 | 90 |
| kills | 56 | 23 |
| hit rate | 54.7% | 43.9% |
| own-heart steals returned | 7 / 7 | 7 / 7 |

All 12 v11 defender assignments traced as forward, so this is a behavioral
regression rather than an activation failure. The matched 2v2 guard matrix
(small, standard, large, huge sides maps) produced four wins for each arm.

### Final `v12` verification

| locked map | field | outcome |
|---|---|---:|
| small plus, seed 202 | 4FFA vs all three top policies | **win +4** |
| standard sides, seed 808 | 2v2 with richard vs daveey + Andre | **win +2** |

Requests: `xreq_af902ca9-55b0-4168-94c7-b0f77e9a946a` and
`xreq_4eae7ddd-79dd-40c9-b42f-8769730da1cb`.

### Follow-up mechanics search (`v13` → `v18`)

Each candidate used the same six locked 4FFA maps (small/standard/large crossed
with corners/plus), three episodes per map, against the same top-policy roster.
The fresh v13 baseline was 3 wins / 15 losses.

| version | isolated candidate | W / D / L | defender kills / ep | defender deaths / ep | defender hit rate | verdict |
|---|---|---:|---:|---:|---:|---|
| v13 | behavior-neutral fire diagnostics | 3 / 0 / 15 | 6.44 | 5.11 | 51.1% | baseline |
| v14 | strafe to a cover cell with a hittable legal aim slot | 1 / 0 / 17 | 5.06 | 5.11 | 52.1% | reject |
| v15 | exact 14 px centered-body hit corridor | 3 / 0 / 15 | 5.44 | 4.61 | 52.1% | reject |
| v16 | use the generated paired duck point on cooldown | 4 / 0 / 14 | 4.67 | 4.67 | 45.1% | reject |
| v17 | score posts within 64 px home-distance bands | 4 / 0 / 14 | 6.22 | 5.17 | 54.5% | reject |
| v18 | sweep along the generated sightline center ray | 2 / 0 / 16 | 4.72 | 4.89 | 55.2% | reject |

The small outcome changes were not statistically distinguishable from noise,
and every candidate was flat or worse on defender kills. v14 is the important
guard against trusting a small screen: it first looked better over six episodes
(one win and five draws versus one win, four draws, one loss), then reversed in
the 18-per-arm replication. v19 therefore restores v13 behavior exactly.

Two final v19 trace/viewer probes completed without infrastructure failure on
standard-corners seed 303 (`xreq_6606c47a-731e-4bcc-8153-acaf2127b589`) and
large-plus seed 606 (`xreq_4af94dbe-e965-410b-a0d9-a4b7194b336a`). Both were
losses to richard; they validate the behavior-neutral trace and rendering
contract, not an outcome improvement.

Replicated request provenance (small-corners, small-plus, standard-corners,
standard-plus, large-corners, large-plus respectively):

- v13: `xreq_df4778e3-93e0-4487-a091-285cd5eaa6bb`,
  `xreq_1df861a6-105b-4f3f-9824-a71fbbabbaf0`,
  `xreq_59ee75f7-e98c-4b75-9e8e-6f3305471e5e`,
  `xreq_687d49cf-1d13-404b-9324-c02521fd39ec`,
  `xreq_1b243e00-1dd8-4c0c-bb47-ea6fedf33574`,
  `xreq_167ba3c3-b6e7-41ca-a6b6-72eb337d029a`.
- v14: `xreq_059f8793-8226-4397-95ea-c757da6a6cdc`,
  `xreq_37fc2431-ad1b-4716-9283-559d85fd4643`,
  `xreq_8e5f767f-9286-4e5e-a8b1-5ffc36b3216f`,
  `xreq_38216b14-e5b5-4f55-8eb5-f5d188dee703`,
  `xreq_bee27442-8c33-4862-8430-db758f2b7caa`,
  `xreq_870728e9-9a48-4366-aea2-2d2b065ff68a`.
- v15: `xreq_fa9024bc-5d0b-4aba-9214-b42d50afa5a4`,
  `xreq_cb011822-8a11-4ed3-b39e-aa7e8cfddf9a`,
  `xreq_86277e8a-708a-4d0d-afe4-92aac92d4321`,
  `xreq_98c86483-44af-4123-b979-c3849f23c785`,
  `xreq_08d8313d-08c2-4db7-9128-2621723f212a`,
  `xreq_acdb7396-156e-478f-af9a-35d58a0c64c6`.
- v16: `xreq_830603b5-ecb6-4b19-91f4-2f7d6608dd77`,
  `xreq_3dea85b2-bcce-48af-929f-9d43b4cfe035`,
  `xreq_880e23ac-a119-41af-af2c-675be1d8c946`,
  `xreq_0c891564-874c-4178-9479-b9e47d1220c0`,
  `xreq_47091fce-b78d-4301-868d-1df070ab1738`,
  `xreq_a4423258-1317-4ccf-a547-0d222555b49b`.
- v17: `xreq_c6d4ea59-fb01-4c3a-81c0-2e4ddc2d6673`,
  `xreq_46fd6aa0-72b6-4fa2-9448-1ec662c3326e`,
  `xreq_77cbb517-015c-471d-a2b6-5d8aa239919e`,
  `xreq_76740921-7575-49ce-94af-57d39e3749ae`,
  `xreq_7b5a4b53-dbb5-456f-9ce5-678adff86b5a`,
  `xreq_d7dba8db-5fb1-4a0f-a009-4a7160532885`.
- v18: `xreq_db3ed84b-d252-4b28-ac7a-4d557eafb6f0`,
  `xreq_97c22e4b-8e7b-4e9d-ada4-090b49622061`,
  `xreq_84bbf9ce-40aa-4398-9bcd-887081cebdcb`,
  `xreq_abf95204-40b9-4047-9ccc-1bbb92314edb`,
  `xreq_1adc243f-81ad-499c-b468-537aa0cce542`,
  `xreq_3a74dcaa-28bd-4e20-b23a-408f73b495cb`.

## v20 accepted — heart-threat target selection

Warehouse mining found that defenders saw multiple enemies on 2,164 of 4,402
alive ticks in the 120 ticks before red-heart steals, while the existing target
score had no defended-heart input. v20 adds a defender-only threat term: route
progress toward the home heart before a theft, then proximity to the observed
thief after one. It does not change roles, movement, objectives, post
generation/assignment, aim, or the fire gate.

Two independent fresh matched batches used v19 and v20 on the same six locked
4FFA maps, three episodes per map and arm. Combined result:

| metric | v19 | v20 |
|---|---:|---:|
| W / D / L | 2 / 1 / 33 | 8 / 2 / 26 |
| non-loss | 8.3% | 27.8% |
| team kills / episode | 8.92 | 11.00 |
| defender kills / episode | 5.11 | 6.42 |
| defender deaths / episode | 4.36 | 4.97 |
| defender replay hit rate | 61.0% | 51.0% |
| red-heart steals | 43 | 40 |

The non-loss Fisher p-value is 0.063 and defender-kill Welch p-value is 0.098.
Those are not conventional 0.05 significance, but the outcome and kill
direction repeated independently, and the mechanism activated narrowly: it
changed the generic top target on 1,771 of 26,150 multi-target defender ticks
(6.8%). The lower precision is an accepted tradeoff because increased firing
volume produced more hits, kills, wins, and non-losses in both batches.

The CTF-derived warehouse's `episodes.winner` field is red/blue-only and
mislabels green/yellow wins as draws. All W/D/L figures in this section were
therefore computed from the complete four-team `results.json` win vectors.

Of v20's 26 losses, Stencil recovered its own heart in 21 and never lost it in
four; only one loss ended with red's heart unrecovered. Thus 25 of 26 remaining
losses terminated when blue or green completed a capture elsewhere after red's
local defense had succeeded.

## v21 accepted — immediate visible-carrier engagement

Trace review showed a remaining mechanical delay after theft: v20 could keep a
generic target latched for eight ticks even when a high-confidence carrier was
already visible and shootable. v21 lets that carrier override both the generic
weighted score and target dwell. The change is limited to defender target
selection; roles, movement, objectives, post generation and assignment, aim,
and firing remain unchanged.

Two independent fresh matched batches used v20 and v21 on the same six locked
4FFA maps, three episodes per map and arm. Combined result:

| metric | v20 | v21 |
|---|---:|---:|
| W / D / L | 8 / 0 / 28 | 10 / 0 / 26 |
| team kills / episode | 9.67 | 10.44 |
| defender kills / episode | 4.78 | 6.67 |
| defender deaths / episode | 5.06 | 4.86 |
| defender replay hit rate | 47.8% | 52.5% |
| red-heart steals | 51 | 45 |

Each batch independently moved from 4 wins to 5. The combined outcome change
is not significant (Fisher p=0.786), while the defender-kill increase is
significant (Welch p=0.024). The trace confirms a narrow causal mechanism: 77
weighted-score overrides and 174 immediate carrier switches across 28,168
multi-target defender ticks.

All 26 v21 losses occurred after Stencil had recovered its own heart or had
never lost it: 24 followed a recovery and two had no red-heart steal. This
removes the final observed local-defense failure from the matched matrix while
leaving third-party FFA captures as the terminal loss mode.

Full immutable request provenance is recorded in
`paintbot/stencil_nim/VERSION_LOG.md`; all 72 episodes completed and all
artifact bundles were fetched.

## Remaining limit

The desired all-map draw-or-win outcome is not yet demonstrated. In the locked
v21 matrix, all 26 losses happened after Stencil had recovered or never lost
its own heart, then one opponent captured another opponent's heart. A policy
posted defensively at its own heart cannot directly prevent that terminal
event. Closing that gap requires revisiting third-party FFA strategy; doing so
was explicitly out of scope for this mechanics-only iteration.

## Reproducibility note

Paintbot terrain is locked with `mapSeed`, `mapSize`, and `mapLayout`. The
generic experience-request `seed` field did not reproduce map geometry and is
not valid for paired terrain comparisons.
