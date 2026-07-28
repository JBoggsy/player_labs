# CTF tentative lessons — session buffer

**Session started:** 2026-07-28 11:05. This is THIS SESSION's lesson buffer. Write candidate
lessons here **as you go** — eagerly and noisily; most will be noise and that's
fine. At the next session start, a hook archives this file automatically to
[`lessons_archive/`](lessons_archive/) and creates a fresh one — nothing you
write here is lost, and nothing carries over by hand.

**Lifecycle.** Per-session buffer → automatic archive (SessionStart hook,
`ctf_lab/tools/rotate_lessons.sh`) → periodic human+agent review
(`/lessons-review`) that clusters RECURRING lessons across archived sessions and
graduates the keepers to `best_practices.md` (CTF-specific) or the root
`best_practices.md` (game-agnostic). Recurrence across independent session
buffers — not in-session hit counts — is the graduation signal.

**Entry format.** `### <lesson, one line>` then `Evidence:` (what you observed,
concrete) and optional `Status:` notes. Terse. One lesson per `###`.

---

### Quantify the complaint from replays ON DISK before designing the fix — the numbers reshape the design

Evidence: James described beacon "clumped, not behind cover, not looking down sightlines" at
frames 350-500. Measuring `scratch/eval_v31_ab/plan_win_bundle.json` (v31 vs focusfire, 0.7.91)
confirmed all three but with specifics that changed the design: pusher nearest-neighbour spacing
13-47px (inside FF range and one 52px grenade blast); free distance toward the enemy 32-108px;
0-3 of 16 ray directions open past 200px at the hold. No new batch needed — the A/B arms were
already fetched with artifacts.
Status: the "download a few replays" step was unnecessary; check `scratch/` first.

### `cover_grid` is non-directional — "near a wall" is not "in cover"

Evidence: `bake_map.build_cover_grid` = walkable cell orthogonally adjacent to non-walkable.
At tick 656 every pusher scored as being in cover (wall 8-15px away) while its east-facing ray
(toward blue) died in 44-108px — i.e. the wall was between them and the threat, not beside them.
Cover is only meaningful relative to a threat direction.
Status: motivates the 16-direction sightline bake; directional cover derives from it (short rays
at ±45° off the threat axis) rather than needing its own field.

### The battle-plan rung never got v25's spread — plan groups navigate to one identical cell

Evidence: `spread_point` is applied only to squad ORDER points (`strategy.py:154`); the plan rung
(3.9, `strategy.py:190`) passes the raw resolved POI to every group member. Five pushers, one
target cell → the 13px spacing above. The v25 A/B "fixed stacking" only for the squad-order path.
Status: a fix landing on one movement path doesn't cover a later path added at the same altitude.
Worth auditing the other rungs for the same omission.

### A 16-direction sightline bake is cheap enough that runtime raycasting isn't warranted

Evidence: prototype bake of free-ray distance per walkable cell × 16 dirs, 4px steps, 400px cap:
**1.5s**, 201 KiB raw uint8 (155×83×16) before npz compression, vs nav.npz's current 19 KiB.
Runtime alternative would ray-cast ~40 candidates × 16 dirs per post decision.
Status: fits the existing bake pattern (walkable/cover/flow_* already ship this way).

### Scoring on real geometry found tactical ground no beacon version has ever occupied

Evidence: scoring cells near the phase-2 pusher waypoint (628,59) on sightline-along-threat +
flank-cover picked (548,20) — 400px of sneak-corridor view with a wall 8px off the flank. Top-5
posts came out ≥56px apart naturally (good firing positions are inherently distributed), so
spread is a SIDE EFFECT of post quality, not a separate force.
Status: caveat — an open-area waypoint may yield no good posts, so `spread_point`'s push-apart
should stay as the floor.

### "Behind if holding, ahead if pushing" must be an explicit scoring term, not emergent

Evidence: the best-scoring post for the phase-2 PUSH waypoint (x=628) was at x=548 — 80px
BEHIND it — because sightline+cover alone favours the defensive side of a corridor. James's
stance intent doesn't fall out of the geometry; it needs its own signed term.

### Fog is what killed v19's buddy gate — chat is the fix for any "is it occupied?" check

Evidence: James redirected my seat-deterministic post-claiming proposal to chat-based claiming
(new `K<seat><cell>`, 6 chars). Earshot is free here (bots are 13-47px apart on arrival, radius
~247px); the real budget is one bubble/sec/player, so the claim slots below intel (C>T>G>U>K>E>P)
and only fires while approaching/settling. Contrast v19: buddy-SENSING under fog left the state
permanently unknown → deadlock.
Status: general pattern — a coordination check on unobservable state needs either a comms channel
or a clock fallback; v19 had neither.

### The stance term did NOT change the outcome at its conservative default — measure the crossover, don't assume the term works

Evidence: added a signed stance term so a PUSH waypoint prefers forward ground. At the chosen
default weight 0.12 the verified rank-0 post (548,20) STILL wins the phase-2 push waypoint from
80px BEHIND it (0.856 vs forward candidate (692,20) at 0.787). Solved the crossover exactly:
**0.1727** — above that the forward post wins. So the default ships a term that does not yet do
the thing it was added for.
Status: shipping 0.12 as the conservative default but the first A/B should bracket 0.12 vs 0.18.
General lesson: adding a term is not the same as the term changing behaviour — compute the
threshold at which it flips, and treat that number as part of the deliverable.

### A "one-line insertion" that spans a lifecycle is not one line — the plan-advance ordering was a real latent bug

Evidence: my design said "one insertion in strategy.py rung 3.9". Codex found that
`_plan.advance()` runs BEFORE `current_objective()` (strategy.py:193-194) and its milestone test
uses the SAME `PLAN_ARRIVE_PX`=60 radius the post substitution triggers on — so arriving at the
raw waypoint would advance the phase and discard the post before it was ever occupied. The
flagship behaviour would have had ~zero dwell and the A/B would have read null for a reason
having nothing to do with the idea.
Status: fixed with a `milestone_ready` param defaulting to None (flag-off path byte-identical).
Lesson: when inserting behaviour at an existing rung, check what the surrounding code does with
the SAME threshold you are triggering on.

### Check whether a new chat message displaces an existing one — count the real arbitration chain in code

Evidence: I specified arbitration as `C>T>G>U>K>E>P` from the module docstring's summary. The
actual `choose_shout` chain has `O` (squad order) at chat.py:199 between thief and grenade, so my
list would have silently demoted a load-bearing message. Correct chain: `C>T>O>G>U>K>E>P`.
Status: the docstring's own summary line omitted `O` too — the docstring was stale relative to
its own function. Read the code's branch order, not the docstring's summary.

### A new aim behaviour must be checked against existing aim offsets for magnitude compatibility

Evidence: post-facing centres the sweep on the post's sightline. But `SQUAD_SECTOR_BRADS`=50 (the
per-rank sector offset) is LARGER than `SWEEP_HALF_ARC`=32 — adding it to a post direction would
point shoulder-rank bots entirely off the lane their post exists to watch. Resolution: sectors
apply only when no settled post owns the sweep.
Status: two independently sensible aim mechanisms can be numerically incompatible; compare their
magnitudes before composing them.

### v31's buddy-wait returns kind="hold" AT THE BOT'S OWN POSITION — any consumer of current_objective must guard on it

Evidence: `plan.current_objective` returns `("hold", belief.self_xy, order)` when buddy-wait
pauses a dangerous move (plan.py:280). Without a `kind == order.kind` guard, the post layer would
latch a post around wherever the bot happened to be standing while waiting, silently defeating
buddy-wait. Codex caught this; I had not considered it.

### My own throwaway verification fixtures are a real source of false alarms — Belief.identity is an INT seat, not a nameplate string

Evidence: my hand-rolled check of "does the mechanism fire" reported POSTS=1 behaving identically
to POSTS=0. Cause: I built a `PlayerTrack(identity='epsilon')` but `identity` is an int seat index
(0=alpha..7=theta, types.py:32-38), so `buddy_near` never matched, buddy-wait paused the push, and
the guard correctly declined to latch a post. With `identity=4` the mechanism fires as designed
(post (716,124), dir 29). Nearly reported a non-existent bug.
Status: when an ad-hoc fixture says "the feature does nothing", suspect the fixture first.

### 32 directions was nearly free — verify the cost of a resolution bump before treating it as a tradeoff

Evidence: James asked for 32-way fans instead of 16. Measured: bake 1.9s -> 3.2s, npz 42 -> 85 KiB
(nav.npz 19,626 -> 106,614 bytes total), angular step 22.5deg -> 11.25deg, max quantisation error
11.25deg -> 5.6deg against a 45deg vision half-cone. Same top-5 post ranking, same scores.
Status: the flank offset just becomes ±4 indices instead of ±2. Cheap resolution bumps are worth
measuring rather than debating.

### A direction COUNT is not comparable across fan resolutions — report forward-reach distance instead

Evidence: the baseline complaint metric was "0-3 of 16 directions open past 200px". At 32
directions the same two cells both read 4 of 32 — the metric moved without the geometry changing.
Relabelling the old measurement as a 32-direction result would have been fabricating data.
Status: keep the measured baseline labelled as 16-ray, and use forward-reach px distributions for
A/B reporting since they are invariant to fan resolution. (Codex raised this unprompted.)

### The repo .venv has a stale shebang — use `uv run python -m pytest`

Evidence: `.venv/bin/pytest` fails with `bad interpreter:
/Users/jamesboggs/coding/personal_labs_CTF/.venv/bin/python: no such file or directory` (note the
case difference in the directory name vs the actual `personal_labs_ctf`). `uv run pytest` also
fails to spawn. `uv run python -m pytest ctf_lab/ctf/beacon/tests/` works: 117 passed.
Status: pre-existing, unrelated to this work, but it will bite every session until the venv is
recreated.

### POSTS A/B RESULT: posts ON improves outcomes on both opponents; the stance sweep is a null

Evidence (matched arms, same image env-flipped, 10 eps/arm, ctf 0.7.95, 0 failures):
- vs ctf-focusfire:v56 — v32(off) 20% win -> v33(posts, stance 0.12) **40%** (p=0.01), score
  -0.60 -> -0.20.
- vs ctf-h050:v1 — v32(off) **0%** win -> v33 **20%** (p=0.00), score -1.00 -> -0.60. First wins
  ever taken off the h0xx line.
- stance 0.18 (v34) also beats off but LESS: focusfire 30%, h050 10%.
- Direct 0.12 vs 0.18: 0.12 ahead on both but p=0.18 / p=0.08 — NOT significant at n=10.
Status: 0.12 stays default. The sweep question needs more power, not a different weight.

### The stance term provably works even though the sweep was null — separate "mechanism fired" from "mechanism helped"

Evidence: raising stance weight 0.12 -> 0.18 (past the computed 0.1727 crossover) moved PUSH
posts forward exactly as designed: mean forward offset vs the waypoint +21.5px -> +32.9px,
median +43 -> +62px, share chosen FORWARD of the waypoint 65% -> 72% (n=567 and 619 push posts).
So the honest reading is "more forward is not better vs focusfire/h050", NOT "the term is inert".
Status: without this geometry measurement the null would have been unreadable — this is the v7/v8
activation-tracing lesson applied to a *scoring weight* rather than a behaviour gate.

### Trace events nest their payload under `data` — a top-level key scan reports false zeros

Evidence: my first activation check read `d.get('post_cell')` on snapshot rows and reported
`snap_with_post=0` across all arms, which looked like total failure. The fields are at
`d['data']['cell']` etc. Re-scanned correctly: 1942 active post events, 181 distinct cells.
Status: nearly declared a working feature dead. When an activation check reports exactly zero
across ALL arms including ones that should differ, suspect the field path before the feature.

### The K claim protocol works in real games — chat-based occupancy beat the fog problem

Evidence: claim_source distribution over 1942 active post-ticks: uncontested 811,
visible_teammate 641, heard_K:<seat> 490 across SIX distinct seats (0,1,3,4,5,6). So bots really
are displacing each other off contested posts via the 6-char shout, not just theoretically.
Status: validates James's redirect away from seat-deterministic claiming. The v19 deadlock
failure mode (unobservable state, no channel) did not recur.

### All four threat-axis sources fire in real games — the static prior is the minority case

Evidence: threat_source over active post-ticks: enemy_track 1125, plan_facing 448,
enemy_pedestal 288, danger_gradient 81. Live evidence dominates the static prior ~4:1, and the
plan's `facing` annotation (traced-only since v30) is now genuinely load-bearing.
Status: confirms rejecting "static toward the enemy half" as the sole axis was correct.

### `ctf-ab` compare.py parses `--baseline` as name:INT — decorated labels crash it

Evidence: `--baseline "beacon:v32(off)"` raised
`ValueError: invalid literal for int() with base 10: '32(off)'` (compare.py:58 parse_spec) six
times before I noticed. Arm labels must be bare `name:vN`; put the arm description in
`--eyebrow`/`--verdict` instead.

### fetch_artifacts --watch prints "exhausted"/"drained=True" during a healthy run

Evidence: mid-batch the watchers logged `fetched 0/10 (pending 9, exhausted 1, drained=True)`,
which reads like failure. `experience_request.py monitor --once` showed `completed: 10 OK 0 fail`.
The wording is pagination bookkeeping, not episode failures.
Status: confirm batch health with `monitor`, not the fetcher's log line.

### coworld upload-policy has NO --env; knobs ship via --secret-env at upload time

Evidence: the CLI exposes `--secret-env KEY=VALUE` (repeatable) and `--tag` for bookkeeping;
there is no plain `--env`. Three A/B arms = one image + three uploads with different
`--secret-env`, which is what "BEACON_SQUADS env-flips on one image" meant. Also `--tag arm=...`
is useful for telling arms apart later.

### v33 (posts) SUBMITTED -> qualified -> champion; placement is async and "pending with no membership" is normal

Evidence: `coworld submit beacon:v33 --league league_3243d905… --auto-champion lineage` returned
`sub_df9f3ac2…` status=pending. First monitor poll showed status=pending with NO membership; ~2
min later `status=placed membership=lpm_b2f96151…`, then QUALIFIED -> competing -> CHAMPION.
Status: don't re-submit on a pending-with-no-membership read; poll it.

### The monitor's --watch verdict is off the NEWEST membership — it said "competing" while our submission was still pending (3rd occurrence)

Evidence: `policy_lifecycle.py monitor --name beacon --watch` printed
`[watch] DONE — terminal verdict: competing` while `sub_df9f3ac2…` (ours) was still
`status=pending` with no membership at all. The verdict came from v28's older membership. This is
already noted in WORKING_CONTEXT from the v28 submit and it fired again verbatim.
Status: the reliable procedure is: grep the `sub_<id>` line for `membership=lpm_<id>`, THEN read
that specific membership block. Never trust the top-level watch verdict right after a submit.

### Division standings are keyed by PLAYER, not policy version — a fresh champion inherits the old score

Evidence: immediately after v33 became champion, the division leaderboard read "James Boggs rank
5 @ 1559.2133, 157 rounds" — identical to the pre-submit value, because it is cumulative account
history (v28-era rounds). v33 had 0 competition rounds. Three different memberships in the
monitor output all displayed the SAME standings line for this reason.
Status: never read post-submit standings as evidence about the new version. Its effect appears
only as rounds accrue; the A/B is the real evidence, standings are lagging and confounded.

### A NEW "Ctf Doubles" league appeared (2026-07-28) — re-resolving league ids by name is now ambiguous

Evidence: `coworld leagues | grep -i ctf` returns TWO leagues: `league_79796d56…` "Ctf Doubles"
(created today) and `league_3243d905…` "Ctf" (the one beacon competes in, created 2026-07-01).
Status: a name-based grep could submit into the wrong league. Match the exact id from
WORKING_CONTEXT / the division you actually ran recon against.
