# Stencil defensive mechanics — 2026-08-04

## Verdict

`stencil:v12` is the accepted upload. It keeps Stencil's strategy fixed and
improves the mechanics underneath it: the aim controller now matches the live
32-slot/five-slot rotation contract, defenders use generated homeward cover
posts, and full traces expose both aim error and post geometry. It is uploaded
with full artifact tracing and is **not submitted**.

The aim fix is a clear improvement. Forcing posts farther forward is not: the
locked-map A/B sharply reduced shots, hits, kills, and hit rate, so v12 restores
the homeward-ranked selector and retains the forward/heart-distance fields only
as observability.

## What changed

| system | accepted behavior | trace evidence |
|---|---|---|
| shooting / aiming | modular controller over 32 aim slots, moving ±5 slots per command | `aim_brads`, `aim_target_brads`, `aim_error_brads`, `aim_grid_error_brads` |
| cover usage | defenders occupy generated firing cells with reachable duck cells | post fire/duck coordinates and navigation-map rays |
| post identification | online, per-map cover candidates scored for sightline, corridor relevance, and duck contrast | `navigation_map` schema v2 |
| post selection | distinct posts ordered outward from the team's home center | `defensive_post*`, route distance to the heart, opponent front, forwardness |
| sightline coverage | defenders sweep toward the opponent front associated with their post | post firing rays plus per-tick aim fields |

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

## Remaining limit

The desired all-map draw-or-win outcome is not yet demonstrated. In the locked
4FFA matrix, Stencil recovered every theft of its own heart but still lost when
one opponent captured another opponent's heart. A policy posted defensively at
its own heart cannot directly prevent that terminal event. Closing that gap
requires revisiting third-party FFA strategy; doing so was explicitly out of
scope for this mechanics-only iteration.

## Reproducibility note

Paintbot terrain is locked with `mapSeed`, `mapSize`, and `mapLayout`. The
generic experience-request `seed` field did not reproduce map geometry and is
not valid for paired terrain comparisons.
