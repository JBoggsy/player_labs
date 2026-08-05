# stencil version log

Read this before assuming what a version contains. Format mirrors
`ctf_lab/ctf/beacon/VERSION_LOG.md`: one entry per uploaded version — what
changed, why, and what the evidence said.

## v22 — exact 32-slot own-aim readback, uploaded 2026-08-04

Immutable policy-version UUID: `74d04f89-43f0-4968-bc94-787e81f982cd`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`.

Submitted to Paintbot on 2026-08-05 with automatic champion promotion:

- submission: `sub_97082b2c-88ab-4fb2-8ae2-63ee17c4402a`;
- membership: `lpm_f0764d92-c162-4a1d-be5e-fb4cf0e9833b`;
- terminal state: `competing`, `active`, and **champion** for James Botts.

- Reads the authoritative Sprite-v1 `own aim <brads>` marker for Stencil's gun
  angle. The prior code inferred aim from the self soldier sprite, which has
  only 16 visual rotations and therefore erased every odd slot from GV36's
  32-slot gun.
- Keeps the sprite-derived angle only as a compatibility fallback. Strategy,
  roles, movement, target selection, lead prediction, and the fire gate are
  unchanged.

The pre-change hosted trace logged about 1,450 aim resyncs in one episode and
reported only multiples of 16 brads despite the live gun's 8-brad slots.

Accepted after a fresh matched 18-episode-per-arm A/B against v21 on six locked
4FFA maps under deployed Paintbot 0.7.186. Replay-expanded gun accuracy rose
from 488/916 (**53.3%**) to 847/1,140 (**74.3%**). Released shots increased
24.5%, kills increased from 177 to 299, and combat deaths fell from 203 to 195.
Every map cleared 70% accuracy (70.1%-80.9%). Wins rose from 3/18 to 7/18.
Across 72 agent traces per arm, cumulative aim resyncs fell from 85,885 to 196.

Request IDs, in small-corners, small-plus, standard-corners, standard-plus,
large-corners, large-plus order:

- v21: `xreq_2479eff3-a2ce-48e0-9c98-8e92c7ece424`,
  `xreq_a5d87427-3d17-4870-bb9a-0ddd8c8b4b98`,
  `xreq_fa1406f4-1550-491b-a55c-1674a0edb230`,
  `xreq_e36fbedd-1e39-4008-8dba-3a1de3bbc1c5`,
  `xreq_922e008a-ae02-4cf7-a498-108bd8ccd792`, and
  `xreq_4ecec622-bbaa-4243-8261-a251c02ef16d`.
- v22: `xreq_3d506be2-cff3-4a12-ba55-2ba2795d3563`,
  `xreq_cbf8d509-5a1e-4feb-87d9-5a3354b057eb`,
  `xreq_ecada834-afb2-4ade-839d-59c7403d9fb7`,
  `xreq_bbce90e2-e355-41ce-8bf9-a66516bbea81`,
  `xreq_770cd6b7-0b82-4971-a166-0aca2392acac`, and
  `xreq_e29d5d6f-0e4f-4885-8924-6d84e3d00025`.

All 36 episodes completed without an episode failure. Full analysis:
`docs/reports/stencil-aim-accuracy-2026-08-04.md`.

## v21 — visible-carrier target override, uploaded 2026-08-04

Immutable policy-version UUID: `da064362-fc5a-4902-9a04-b33b00d9005b`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Retains v20's accepted heart-threat score. Once the heart is stolen, a
  high-confidence, shootable carrier match now overrides competing generic
  targets and bypasses the normal eight-tick target latch.
- `STENCIL_DEFENSIVE_CARRIER_THREAT_MIN` controls the match threshold. End
  counters expose weighted-score overrides and immediate carrier switches.
- Does not change roles, movement, objectives, posts, cover, aim, or the fire
  gate.

Accepted after two independent fresh matched batches against v20 on the same
six locked 4FFA maps, three episodes per map and arm. Both batches improved
from 4W/0D/14L to 5W/0D/13L. Combined, defender kills rose from 4.78 to 6.67
per episode (Welch p=0.024), defender deaths fell from 5.06 to 4.86, replay hit
rate rose from 47.8% to 52.5%, and red-heart steals fell from 51 to 45. The
outcome change from 8W/0D/28L to 10W/0D/26L was directional but not significant
(Fisher p=0.786).

The mechanic activated narrowly and as designed: 77 weighted-score overrides
and 174 immediate carrier switches across 28,168 multi-target defender ticks.
All 26 v21 losses occurred after Stencil had recovered its own heart or never
lost it; the remaining all-map loss mode is third-party FFA capture, outside
this fixed-strategy mechanics iteration.

First-run v20/v21 request IDs, in small-corners, small-plus,
standard-corners, standard-plus, large-corners, large-plus order:

- v20: `xreq_b5fb272e-42ba-4c3d-954c-969d23242d93`,
  `xreq_9f476a6e-a658-4a7b-a7db-1051a2eb6b0f`,
  `xreq_6bb863e7-4cb0-4d1b-9cc2-402a44bbd3dd`,
  `xreq_e411d17f-bf8f-464f-96f6-d251aefa196d`,
  `xreq_afb6c9ec-ead2-4dcd-9550-1adc4befae85`,
  `xreq_ec4701bd-fec5-4279-b66e-1add00caa7c0`.
- v21: `xreq_900110b7-3345-40b6-bda7-89965c414394`,
  `xreq_46ad41e8-c6b4-4e82-8bcb-929f19f93be2`,
  `xreq_768d32da-5c0a-4075-a9c8-daabbe3fe5a0`,
  `xreq_7b028023-d216-4df0-897d-9e291252c4be`,
  `xreq_002bec69-d457-4672-8a70-9e5cba67a4ab`,
  `xreq_832a833a-7667-41fb-a4f3-dbf8baec7633`.

Replication request IDs in the same order:

- v20: `xreq_b45c5327-4f75-45be-8770-dde23293210c`,
  `xreq_f561dfa2-0f54-4d72-83f8-fa45972d0fa6`,
  `xreq_85896369-4933-4f01-ad49-73451299d358`,
  `xreq_12df2f52-436e-45b6-a9e7-13848e055168`,
  `xreq_e8a28dea-3e0b-4497-9924-79dea573a580`,
  `xreq_732201fa-4790-4704-b85c-fa5a81f0b83c`.
- v21: `xreq_216efd5a-dfaf-4602-b7e0-e981c7e695bc`,
  `xreq_bc668bf5-da4c-4142-a14e-71f1e1c21766`,
  `xreq_11e5e195-68cc-4fc9-bebe-2f9276b95c24`,
  `xreq_d5b7d747-a947-4722-9a5e-0afdbd4388bf`,
  `xreq_6a7b32e2-85fb-4e5a-b1cc-df235220567a`,
  `xreq_dd569dba-1b42-43fc-b072-3ffe4e453d48`.

All 72 episodes completed and every artifact bundle was fetched. W/D/L was
computed from the four-team `results.json` win vectors, not the warehouse's
red/blue-only legacy `episodes.winner` projection.

## v20 — defensive heart-threat target selection, uploaded 2026-08-04

Immutable policy-version UUID: `bf6f3048-4fa2-4015-bf75-dc7bf0928149`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Changes only defender gun-target scoring. Before a theft, visible enemies
  receive a bonus that increases with route progress toward Stencil's heart;
  after a theft, the bonus identifies the visible enemy nearest the observed
  thief position. Roles, movement, objectives, post generation/assignment,
  aim, and the fire gate are unchanged.
- `STENCIL_DEFENSIVE_TARGETING`,
  `STENCIL_DEFENSIVE_TARGET_THREAT_WEIGHT`,
  `STENCIL_DEFENSIVE_TARGET_THREAT_RADIUS_PX`, and
  `STENCIL_DEFENSIVE_THIEF_MATCH_PX` isolate the new mechanic.
- Full snapshots expose the selected enemy, team, original generic score,
  defensive threat bonus, and heart distance. End counters record multi-target
  defender ticks and cases where the new term changes the top-scored target.

Accepted after two fresh matched runs on the same six locked 4FFA maps, three
episodes per map and arm. Combined results improved from v19's 2W/1D/33L to
8W/2D/26L (episode-level non-loss Fisher p=0.063). Defender kills rose from
5.11 to 6.42 per episode and team kills from 8.92 to 11.00. The term changed
the generic top target on 1,771 of 26,150 multi-target defender ticks (6.8%).

The tradeoff is lower precision and slightly higher defender mortality: replay
hit rate fell 61.0% to 51.0%, while defender deaths rose 4.36 to 4.97 per
episode. The added volume still produced more hits, kills, wins, and non-losses
in both independent batches. Red-heart steals fell only 43 to 40, so this is a
combat-output improvement rather than a clean theft-prevention result.

First-run v19/v20 request IDs, in small-corners, small-plus,
standard-corners, standard-plus, large-corners, large-plus order:

- v19: `xreq_caa6084e-0177-4011-b694-987ada8f260a`,
  `xreq_48a5714f-f5b9-4b2b-a6a3-185723d28882`,
  `xreq_37ee6e25-7d56-4af5-8cda-88108b02f5e4`,
  `xreq_f381e238-4ce4-41ba-9843-3b7060fc300e`,
  `xreq_e3c0fa37-053d-4a83-8525-b00ab93c1ddc`,
  `xreq_1924b415-3b08-47bd-b365-91956cda8746`.
- v20: `xreq_887e9059-6e79-4bbc-952b-d01ca3935c44`,
  `xreq_c5e35a0c-a62a-4fc6-a486-8c69d6ecec30`,
  `xreq_82acaf8d-9b6d-4d47-9300-bdd597c3e991`,
  `xreq_e651caf9-bebb-4372-8704-d9a6b9ab526d`,
  `xreq_25340901-b7a0-4287-9363-16105087feb5`,
  `xreq_588ca6df-68f4-43a6-817e-445f10e94b21`.

Replication v19/v20 request IDs in the same order:

- v19: `xreq_889e8609-f7d6-46ba-803b-e4673cdc3ce0`,
  `xreq_5dd5b6ac-a6d2-41fb-b8ab-aae8ac585fa8`,
  `xreq_f8e78291-6536-452d-a58c-058892706137`,
  `xreq_5c68f7b0-3423-42f4-bf2f-20a5ed856556`,
  `xreq_e273a730-7ed6-42f8-b185-a3451a80424f`,
  `xreq_aaf8e7f4-53dd-4886-a7ac-fc20f3bae1df`.
- v20: `xreq_689ee7ff-ad50-4a70-a0ce-7939539dc8a8`,
  `xreq_b7e15319-1df6-43b6-b18b-39832d0699b5`,
  `xreq_b1ce8500-e040-4724-a7d9-a985f6b15d52`,
  `xreq_f3841c61-ae75-465e-93eb-e65142b0a0c8`,
  `xreq_4fdbeb86-44c5-4cac-895f-ec26287dd4ab`,
  `xreq_fae640d2-7a52-4bca-ae4f-6eab54343557`.

All 72 episodes completed and all requested artifact bundles were fetched.
The warehouse's legacy `episodes.winner` projection only understands red/blue;
the W/D/L verdict above comes directly from the four-team `results.json` win
vectors.

## v19 — accepted behavior + complete defense diagnostics, uploaded 2026-08-04

Immutable policy-version UUID: `e1b5dfa1-6755-4c4f-99ac-1582dfceec94`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Behavior is identical to v13/v12: accepted five-slot aim, exact homeward post
  ordering, and the existing live-threat cover micro.
- Retains v13's per-tick fire-gate inputs/reason and adds the generated post's
  center sightline point as trace-only `defensive_post_sightline_aim`.
- The navigation viewer now overlays this agent's assigned post, paired duck
  point, and scored sightline axis on the generated map knowledge.
- v14-v18's rejected alignment strafe, wider fire gate, paired-post duck,
  home-banded ranking, and runtime sweep-axis changes are absent.

This is the accepted fully traced inert upload after the mechanics search. It
has not been submitted to a league. Two one-episode runtime probes on canonical
Paintbot 0.7.184 completed with no failed episodes and emitted the new
assignment/sightline fields for both defenders: standard-corners seed 303
(`xreq_6606c47a-731e-4bcc-8153-acaf2127b589`) and large-plus seed 606
(`xreq_4af94dbe-e965-410b-a0d9-a4b7194b336a`). Both episodes were losses to
richard, consistent with the accepted baseline's unresolved 4FFA limit; these
probes validate tracing and rendering, not an outcome improvement.

## v18 — rejected post-corridor sweep axis, uploaded 2026-08-04

Immutable policy-version UUID: `5bef60d2-3c31-4297-87f7-80bcb3b95359`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v13's post assignment, firing, and cover behavior and retains its
  fire-gate diagnostics.
- A posted defender now centers its idle sweep on the middle ray of the
  generated post sightline. Previously generation scored rays along the next
  route waypoint, but runtime aimed directly at the distant opponent pedestal,
  which could point through a bend or wall.
- Adds `defensive_post_aim` to each snapshot so the exact runtime sweep axis is
  visible beside the navigation-map rays.
- Does not change strategy, roles, objective priority, post selection, target
  selection, or active target aiming.

Across the 36 v13 assignments in the locked field, the old runtime axis differed
from the scored center ray by median 9.8 degrees and mean 23.2 degrees; six
assignments exceeded 45 degrees and three were 90 degrees off.

Rejected after the matched 18-episode-per-arm six-map evaluation. Defender hit
rate rose from 51.05% to 55.15% and deaths fell from 5.11 to 4.89 per episode,
but defender kills fell from 6.44 to 4.72 and outcomes fell from 3 to 2 wins
(Fisher p=1.0; defender-kill Welch p=0.194). The runtime sweep change was
removed; the generated center ray remains trace-only navigation knowledge.

## v17 — rejected home-banded post score selection, uploaded 2026-08-04

Immutable policy-version UUID: `d2127c91-28d3-4056-bcb7-d3eca7f13e25`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v13's firing and cover behavior and retains its diagnostic fields.
- Preserves homeward post selection, but groups candidates into 64 px
  home-distance bands and ranks by the generated sightline/corridor/duck score
  within a band. Previously score only broke an exact-distance tie, so the
  generated metric was usually ignored during assignment.
- `STENCIL_POST_HOME_BAND_PX` controls the local band size.
- Does not change strategy, roles, objective priority, target selection, or
  post generation.

Rejected after the matched 18-episode-per-arm six-map evaluation. Assignment
changed on small and standard maps, but the outcome shift from 3 to 4 wins was
noise (Fisher p=0.691), and the defensive mechanism was flat: defender kills
6.44 to 6.22, deaths 5.11 to 5.17, and normalized fire 7.58 to 7.50 per 1,000
alive ticks. The team-kill increase from 10.17 to 11.78 came from attackers,
not the changed posts. Exact homeward ordering was restored.

## v16 — rejected paired post-duck cover, uploaded 2026-08-04

Immutable policy-version UUID: `0db06dde-21c9-45f6-aeac-839297fdcf00`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Restores v13's firing behavior and retains its diagnostic fields.
- When a defender is holding a generated post and its gun is cooling down, it
  uses that post's generated duck point if the point is reachable and blocks
  the current threat ray. Otherwise the existing live-threat cover search
  remains the fallback.
- `micro=post_duck` and `defensive_post_duck_ticks` trace activation.
- Does not change strategy, role assignment, objective priority, post
  selection, target selection, or firing behavior.

Rejected after the matched 18-episode-per-arm six-map evaluation. v16 activated
`post_duck` for 127 defender ticks and increased normalized defender firing
from 7.58 to 8.50 shots per 1,000 alive ticks, but defender hit rate fell from
51.05% to 45.05% and defender kills fell from 6.44 to 4.67 per episode. The
outcome moved from 3 to 4 wins (no draws), which was noise at this sample size;
defender-kill Welch p=0.109. The paired-duck runtime behavior was removed.

## v15 — exact gun-hit corridor, uploaded 2026-08-04

Immutable policy-version UUID: `0f2f918b-504b-4661-8bd1-79e823070eda`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Keeps v13's behavior and fire-gate diagnostics, except that the gun alignment
  gate now uses the live simulation's exact centered-body hit corridor:
  `PlayerHalf` (6 px) + `BulletHalfWidth` (8 px) = 14 px.
- Removes the old guessed split of 8 px beyond 220 px and 16 px within it.
- Does not change strategy, role assignment, post selection, target selection,
  movement, cover use, or objective priority.

Rejected after the matched 18-episode-per-arm six-map evaluation tied v13 at
3 wins / 15 losses. Defender kills fell from 6.44 to 5.44 per episode, while
defender deaths fell from 5.11 to 4.61; neither combat change was significant
(Welch p=0.471 and p=0.384 respectively), and the outcome Fisher p-value was
1.0. The wider gate modestly raised hit rate (52.75% to 54.70%) but lowered
normalized defender firing from 7.58 to 5.83 shots per 1,000 alive ticks. The
fire-gate change was removed; v13's diagnostics remain.

## v14 — rejected cover-preserving discrete-aim alignment, uploaded 2026-08-04

Immutable policy-version UUID: `1706a574-4c47-46d2-860d-3adcbe38c250`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- When a defender holding its assigned post has a ready, unobstructed target
  that no legal aim slot can hit from the current position, it may strafe to
  the nearest walkable cover cell within three nav cells where a legal slot
  intersects that target.
- Does not change strategy, role assignment, post selection, target selection,
  or objective priority. `STENCIL_AIM_ALIGN_STRAFE=0` disables the mechanic.
- `micro=aim_align` and cumulative `aim_alignment_strafe_ticks` trace
  activation. The v13 fire-gate probe motivated the change: aim alignment was
  the dominant visible-target blocker (1,858 ticks), and 943 cases could not
  be solved by rotation alone; at `hold_post`, 173/323 blocked ticks were
  geometrically unshootable from the current point.

Rejected after the encouraging six-game screen failed replication. In the
matched 18-episode-per-arm six-map field, v13 went 3 wins / 15 losses while v14
went 1 win / 17 losses (loss/non-loss Fisher p=0.603); defender kills fell from
6.44 to 5.06 per episode and team deaths rose from 10.78 to 10.94. The candidate did
raise attacker kills and produce four captures, but those are outside the
defensive-mechanics target and did not improve outcomes. Its movement code was
removed before v15.

## v13 — fire-gate diagnostic probe, uploaded 2026-08-04

Immutable policy-version UUID: `46cb093a-5310-4ace-9dcf-6d9d0b88f755`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Behavior is identical to v12.
- Adds per-tick target range, nearest-slot angular/lateral error, fire-ready
  state, ray-clear and teammate-blocked inputs, and a normalized fire-gate
  reason (`cooldown`, `aim_alignment`, `wall`, `teammate`, `fire`, or trigger
  `release`).
- Purpose: distinguish the dominant cause of visible-but-not-firing defender
  ticks before changing aim movement, cover micro, or fire cadence.

## v12 — accepted aim fix + observable homeward posts, uploaded 2026-08-04

Immutable policy-version UUID: `5889dc2e-170a-4082-8f52-b149333d552a`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Preserves v9's strategy and homeward-ranked defensive-post behavior while
  retaining the accepted 32-slot/five-slot aim controller.
- Adds trace-only `defensive_post_heart_distance` and
  `defensive_post_forward` fields so a post selection can be judged directly
  without changing how it is selected.
- Reverts v10/v11's post-ranking experiments after the locked-map A/B showed
  that forcing defenders farther forward reduced combat output.

Two final hosted probes on canonical Paintbot 0.7.184 completed without
failure. On locked small-plus 4FFA seed 202, v12 won `+4` against daveey,
richard, and Andre (`xreq_af902ca9-55b0-4168-94c7-b0f77e9a946a`). On locked
standard-sides 2v2 seed 808, v12 and richard won `+2` against daveey and Andre
(`xreq_4eae7ddd-79dd-40c9-b42f-8769730da1cb`). Defender traces contained
generated post coordinates, associated opponent fronts, score, heart distance,
and forwardness; attacker traces contained no post assignment.

## v11 — rejected forced-forward post ranking, uploaded 2026-08-04

Immutable policy-version UUID: `4b731d4c-2c6c-4b83-a05a-2bed892b7db2`;
never submitted.

- Restricted defender assignments to generated posts forward of the heart and
  within gun range of it, then ranked those candidates by post score.
- Added trace fields for the selected post's heart distance and forwardness.
- Activation was correct: all 12 defender assignments in the locked 4FFA
  matrix reported `defensive_post_forward=true`.

The six-map locked 4FFA A/B rejected the behavior. v9 drew one and lost five;
v11 lost all six. More importantly, v11 fell from 285 shots / 156 hits / 56
kills (54.7% hit rate) to 205 / 90 / 23 (43.9%). Both arms recovered all seven
observed thefts of Stencil's heart, so the forward constraint did not improve
the defense mechanism it was meant to strengthen. In the separate locked
four-map 2v2 matrix both versions won all four, which was insufficient to
rescue the clear 4FFA combat regression.

## v10 — rejected opponent-route post ordering, uploaded 2026-08-04

Immutable policy-version UUID: `284654a3-507d-4504-bd46-0cba8b2bcf29`;
never submitted.

- Assigned distinct opponent fronts and ranked posts by the shortest enemy
  route to the defended heart.
- Initial score comparisons were run with the generic `seed` field. Inspection
  showed that this did not lock Paintbot terrain: reproducibility requires
  `mapSeed`, `mapSize`, and `mapLayout`. Those comparisons were therefore
  discarded rather than treated as evidence, and v11 was evaluated with a
  properly locked matrix.

## v9 — deployed five-slot aim controller, uploaded 2026-08-04

Immutable policy-version UUID: `30ee0431-1f3d-4ecd-9686-208c3894a1f4`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Models the live 0.7.184/GV36 combination exactly: 32 aim slots and the
  variants' explicit `aimTurnRate=5`, yielding a 40-brad jump per held tick.
- Replaces greedy angular-sign turning with modular slot routing. It compares
  the number of +5 and -5 slot commands required to reach the nearest target
  slot, preventing unreachable-angle oscillation.
- Keeps defensive strategy, generated posts, cover decisions, target
  selection, and fire gating unchanged. Full traces retain v8's aim target,
  error, grid error, and authoritative wire resync fields.

Against the current top 4FFA field over eight natural generated maps, v9 won
two, drew one, and lost five versus v7's zero wins, three draws, and five
losses. Replay-derived combat improved from 4.63 to 11.13 kills/episode and
from 20.9% to 51.5% hit rate; deaths fell from 10.13 to 8.50 per episode.
Stencil captured four hearts versus zero for v7. Both arms experienced 1.13
own-heart steals per episode, and all nine v9 thefts were returned before a
capture. Requests: v9 `xreq_c104f2ee-625f-4bbb-a9ee-c245f50e0c86`; v7
`xreq_4d287287-945f-40f8-89a1-ea85a267b746`.

## v8 — rejected incomplete GameVersion 36 compatibility, uploaded 2026-08-04

Immutable policy-version UUID: `c849fad4-645a-44ca-8c7f-32e7f0358525`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Pins canonical Paintbot 0.7.184 at source ref
  `352d0e5408245710874abcfb861ad88491156238` (GameVersion 36).
- Updated Stencil's aim integrator from the removed 5-brad continuous turn to
  an assumed one-slot / 8-brad step and made each wire marker authoritative.
  Live XP episode configuration then showed that 0.7.184's variants still
  explicitly set `aimTurnRate=5`; under GV36 that means five slots / 40 brads.
  v8 was therefore rejected before evaluation.
- Adds per-tick `aim_target_brads`, `aim_error_brads`, and
  `aim_grid_error_brads` tracing. Strategy, roles, objectives, posts, cover,
  target selection, and fire gating are otherwise unchanged.

The v8 request `xreq_1d7e54b5-af94-4a4a-a7da-1b0f81961b08` was cancelled
before any episode completed. Baseline request
`xreq_2833a2c2-2036-4e16-8bf4-427763938bb4` continued for diagnosis.

## v7 — distinct homeward-ranked defensive posts, uploaded 2026-08-04

Immutable policy-version UUID: `91cd9b6d-df02-4887-8ed0-24cc8379030b`.
Uploaded with `STENCIL_TRACE_OUTPUTS=jsonl@artifact`,
`STENCIL_TRACE_NAVIGATION=1`, and `STENCIL_DIAG_EVERY_TICKS=1`; not submitted
to a league.

- Deduplicates the generated post union and ranks it by Euclidean distance from
  the team's home center, then assigns defender seat N to rank N. This fixes v6's
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
