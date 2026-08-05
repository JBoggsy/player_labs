# Stencil exact-aim accuracy A/B — 2026-08-04

## Verdict

`stencil:v22` met every acceptance condition against the fresh matched v21
control: **74.3% gun accuracy**, more shots, fewer deaths, and more kills. The
change was accepted, then submitted on 2026-08-05; it qualified and became the
James Botts champion as membership
`lpm_f0764d92-c162-4a1d-be5e-fb4cf0e9833b`.

| metric | v21 control | v22 exact aim | change |
|---|---:|---:|---:|
| replay gun accuracy | 488 / 916 (53.3%) | 847 / 1,140 (74.3%) | +21.0 pp |
| released shots | 916 | 1,140 | +224 (+24.5%) |
| kills | 177 | 299 | +122 (+68.9%) |
| combat deaths | 203 | 195 | -8 (-3.9%) |
| wins | 3 / 18 | 7 / 18 | +4 |
| cumulative aim resyncs | 85,885 | 196 | -99.8% |

All 36 episodes completed without an episode failure. Kills and deaths are the
authoritative GameVersion 36 replay events; accuracy is `hit / shot` over gun
events for Stencil's four seats. Combat deaths exclude capture-elimination
folds.

The accuracy difference is decisive (Fisher exact p=3.73e-23, odds ratio 2.54).
Per-episode shot volume increased under both Welch's t-test (p=0.0155) and
Mann-Whitney (p=0.0236), as did kills (p=0.000473 and p=0.00103). Deaths moved
downward but the eight-death reduction is noise at this sample size (p=0.298
and p=0.285); the acceptance condition was non-increase, not proof of a death
reduction.

## Recon and root cause

The deployed target was Paintbot 0.7.186, source
`61f504c1463ee18dd1a3c1bf07fb15bea98311f1`, GameVersion 36. The live shooting
contract is:

- the gun has 32 aim slots, 8 brads apart; the manifest's `aimTurnRate=5`
  advances five slots per held tick;
- trigger pull locks the angle, release occurs five ticks later from the
  shooter's then-current position, and cooldown is 12 ticks;
- the released hitscan ray receives calibrated Gaussian jitter, stops at walls
  or the first hittable body, and tests only visible silhouette samples;
- the player stream exposes exact own aim as `own aim <brads>`; the soldier art
  itself has only 16 rotations.

Stencil parsed its own angle from the 16-rotation soldier sprite and ignored
the exact marker. The server still occupied odd 8-brad slots, but Stencil folded
them onto even 16-brad angles and then chose subsequent turn/fire inputs from
false state. One recovered v21 episode logged roughly 1,450 resyncs; across the
fresh control arm the total was 85,885.

v22 reads the exact marker and leaves the sprite-derived value only as a
compatibility fallback. No strategy, movement, target selection, lead, or fire
gate changed. v22's traces use odd gun slots and reduced resyncs by 99.8%, which
directly verifies activation rather than inferring it from the score.

## Locked-map results

Each arm played three episodes on each map against the same pinned opponent
teams: daveey `paintbot-focusfire:v22`, richard
`co-gas-paintbot-nim-richard:v4`, and Andre `alphashot:v359`.

| locked map | v21 shots / hits | v21 accuracy | v22 shots / hits | v22 accuracy | v21 to v22 kills | v21 to v22 deaths |
|---|---:|---:|---:|---:|---:|---:|
| small corners, seed 101 | 143 / 76 | 53.1% | 141 / 112 | 79.4% | 17 to 33 | 36 to 34 |
| small plus, seed 202 | 191 / 95 | 49.7% | 191 / 137 | 71.7% | 38 to 53 | 33 to 31 |
| standard corners, seed 303 | 165 / 95 | 57.6% | 182 / 136 | 74.7% | 24 to 58 | 36 to 34 |
| standard plus, seed 404 | 146 / 79 | 54.1% | 196 / 139 | 70.9% | 46 to 49 | 31 to 33 |
| large corners, seed 505 | 160 / 83 | 51.9% | 231 / 162 | 70.1% | 37 to 49 | 34 to 35 |
| large plus, seed 606 | 111 / 60 | 54.1% | 199 / 161 | 80.9% | 15 to 57 | 33 to 28 |

Every map reached at least 70% accuracy. Five of six maps held or increased shot
volume; the aggregate rose by 224 shots. Four maps reduced deaths, large corners
rose by one, and standard plus rose by two; aggregate deaths nevertheless fell
by eight while kills increased on every map.

## Request provenance

Requests are listed in small-corners, small-plus, standard-corners,
standard-plus, large-corners, large-plus order:

- v21: `xreq_2479eff3-a2ce-48e0-9c98-8e92c7ece424`,
  `xreq_a5d87427-3d17-4870-bb9a-0ddd8c8b4b98`,
  `xreq_fa1406f4-1550-491b-a55c-1674a0edb230`,
  `xreq_e36fbedd-1e39-4008-8dba-3a1de3bbc1c5`,
  `xreq_922e008a-ae02-4cf7-a498-108bd8ccd792`,
  `xreq_4ecec622-bbaa-4243-8261-a251c02ef16d`.
- v22: `xreq_3d506be2-cff3-4a12-ba55-2ba2795d3563`,
  `xreq_cbf8d509-5a1e-4feb-87d9-5a3354b057eb`,
  `xreq_ecada834-afb2-4ade-839d-59c7403d9fb7`,
  `xreq_bbce90e2-e355-41ce-8bf9-a66516bbea81`,
  `xreq_770cd6b7-0b82-4971-a166-0aca2392acac`,
  `xreq_e29d5d6f-0e4f-4885-8924-6d84e3d00025`.
