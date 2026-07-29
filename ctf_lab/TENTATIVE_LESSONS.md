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

### PLATFORM STALL (2026-07-28 ~16:00-16:35): xreqs accept but never dispatch, while LEAGUE rounds keep running

Evidence: 4 experience requests (2x10 eps vs alphashot + two 1-episode canaries) all sat at
`status=pending, completed=0, running=0, failed=0, error=None` for 30+ minutes. Earlier the same
session, 6 identical-shape xreqs drained in ~10 min. Isolation done:
- a canary vs **focusfire** (an opponent that worked an hour earlier) ALSO stalled -> not
  alphashot-specific, not a roster/policy problem;
- the API is healthy (older xreqs still read back `completed 10/10`);
- the **division leaderboard advanced 157 -> 158 rounds** during the stall -> the cluster IS
  executing league/commissioner episodes; only ad-hoc xreq dispatch is wedged.
- Coincides with the game redeploying THREE times in ~30 min: 0.7.95 -> 0.7.96 -> 0.7.97 (each
  xreq records the version it was created against, so a stalled batch can be pinned to a
  now-superseded version).
Status: distinguish "my request is malformed" from "the platform isn't dispatching" with a
1-episode canary against a KNOWN-GOOD opponent, plus a leaderboard-rounds check. Cheap and
decisive. Also: a stalled xreq created at 0.7.96 while the deploy is now 0.7.97 is probably worth
re-firing rather than waiting, since arms must be version-matched to compare.

### Version pinning caveat for cross-batch comparison: the game moved under us mid-session

Evidence: the posts A/B ran entirely on **0.7.95** (all 6 arms, verified). The alphashot recon was
created against **0.7.96**, and canaries minutes later reported **0.7.97**. So alphashot results
will NOT be strictly comparable to the morning's focusfire/h050 numbers.
Status: the v33-vs-v32 alphashot comparison stays internally valid (both arms same version), but
do not put alphashot win rates in the same table as the 0.7.95 focusfire/h050 numbers without
saying so. This is the v24/v25 "league redeployed overnight" lesson recurring intra-session.

### ALPHASHOT PROFILE (div rank 1): it beats us on GUNFIGHTING, not on ground — forward sightline reach is IDENTICAL

Evidence: 4 league doubles rounds, beacon:v28 vs alphashot-ghost-red-ca3e95f:v1 (GV23 replays,
`scratch/recon_alphashot/league`). beacon went 1W/3L.
- **Kills 60 vs our 39; kill differential +25 (60-35) vs our -1 (39-40).** It wins the attrition
  war outright, same as h050's pattern.
- **Accuracy 0.202 vs our 0.181** (kills/shot) and it shoots MORE per alive-tick (0.25 vs 0.19) —
  so it is both more accurate AND more aggressive with the trigger.
- **11 clustered kills (two kills by the same policy within 48t) vs beacon's 0** — evidence of
  focus fire / trading in groups. beacon's kills are isolated.
- **It hugs cover far harder: mean distance to nearest wall 146px vs our 321px; 70% of alive
  ticks within 24px of a wall vs our 55%.**
- **BUT forward sightline reach along the threat axis is statistically IDENTICAL** — measured with
  our own baked 32-dir field: alphashot mean 93px / median 80px / 10% open >=200px; beacon mean
  93px / median 80px / 9%. Own-team nearest-neighbour spacing also near-identical (137px vs 132px).
- Neither side steals or captures much (alphashot 0 steals in 4 rounds; the games are pure wipes).
- Item use is low for both (shield 2% vs our 4%, grenade 5% vs our 8%).
**Interpretation: posts give us comparable GROUND to the rank-1 policy; the remaining gap is
marksmanship + trigger discipline + fighting in groups (focus fire), not positioning.** That is a
different lever than the one we just shipped, and it argues the next iteration should target the
FIGHT (accuracy/lead/target selection/focus fire), not more position work.
Caveat: n=4 doubles rounds, beacon:v28 (pre-posts). The 1v1 posts-vs-alphashot xreqs are queued
but the platform stalled; re-run them before trusting this as a v33 baseline.

### Replays carry their OWN GameVersion and the coworld record can be STALE — read the header, don't trust the manifest

Evidence: `coworld show cow_aa3ab14f… --json` reported ctf **0.7.91** / source ref
`e2b7b3c971…`, but a reader built at that ref failed with `Replay game version does not match`.
The replay header is `COWLDCTF` + u16 1 + u16 3 + `"ctf"` + a length-prefixed version string —
which read as **"23"** (I first misparsed it as "238"). GameVersion 23 = coworld-ctf `cdd567f`
("GV23: shield-expiry break + action clock floor, overtimeTicks 500"), NOT the manifest's ref.
Built `tools/bin/expand_replay_json-cdd567f` and it parsed cleanly.
Status: to pin a reader, decode the replay header's version string and map it to the commit whose
`src/ctf/sim.nim` has that `GameVersion*` — `git log --all -- src/ctf/sim.nim` finds it fast.
NOTE GV23 is NEWER than the GV21/GV22 our config/docs assume; the shield now BREAKS on depletion
and there is an overtime clock floor (overtimeTicks 500) — worth auditing against beacon's
assumptions.

### `--policy <name>` artifact fetch returns episodes by RECENCY, not episodes containing that policy's opponents

Evidence: `fetch_artifacts.py --policy alphashot-ghost-red-ca3e95f` failed outright ("No policy
versions found" — it resolves OUR policies only). Fetching `--policy beacon -n 25` returned 25
recent beacon episodes of which only **4** contained alphashot; 17 were vs `ctf-exp:v18/v53`
(someone else's experiment policies, not even in the standings).
Status: to profile a specific opponent from league history, over-fetch our own episodes and FILTER
on `policy_results[].policy.name`. Also note league episodes use `policy_results`, not
`participants` — and `coworld_version` is None on them, so version must come from the replay header.

### ALPHASHOT 1v1 CONFIRMED (n=10/arm, 0.7.96): posts do NOT regress vs the field leader, and the league profile REPLICATES

Evidence: v32(off) 10% win / -0.80 vs v33(posts) 20% win / -0.60, p=0.08 (non-significant but
positive). 20/20 episodes, 0 failures, both arms same version. Report:
`scratch/recon_alphashot/reports/v33_vs_v32_alphashot.html`.
- kills 136 -> 174 with posts (deaths 238 -> 227); alphashot 234 -> 222 kills.
- **The n=4 league doubles finding replicated exactly at n=10 1v1: forward sightline reach is
  IDENTICAL** (beacon 92px mean/84 median, alphashot 93/84; both 7-9% open >=200px).
Status: the regression check passes — posts are safe against an opponent they were never tuned on.

### THE ALPHASHOT GAP IS ENGAGEMENT RANGE + FOCUS FIRE, not positioning

Evidence (kill rows carry killer_x/y and victim_x/y — use them):
- **Kill range: alphashot 222px mean / 218px median vs beacon 187px / 182px.** 59% of OUR kills
  are inside 200px vs their 44%; we take **0%** of kills beyond 400px vs their 4%. They fight at
  a longer, safer range; we get pulled into close trades where trading is even at best.
- **Focus fire: 101 clustered kills (same side, two kills within 48t) vs our 61.**
- Ground is even (see above), team spacing comparable (110px vs 143px).
Status: this is the same conclusion the league sample gave, now at 10x the sample. **Positioning
is no longer the binding constraint vs the field leader.** Next lever candidates: a hold-fire
range gate tuned upward (FIRE_MAX_RANGE_PX is 350 — we're killing at ~187px, so we're fighting
much closer than our own gate allows), wounded-target priority, and real focus-fire coordination.

### Posts had almost no room to work vs alphashot — max dwell 71 ticks because beacon only LIVES 407 ticks

Evidence: 472 active post-ticks / 113 distinct cells, but max ticks_on_post = **71** (vs **525**
against focusfire). Cause: mean beacon lifespan vs alphashot is 407t with posts (366t without) —
median 331t. Posts DID extend survival ~9% (+41t) and raise kills 136->174, but a bot that dies
in ~5 seconds cannot settle, hold a sightline, and profit from it.
Status: a positional mechanism's value is bounded by SURVIVAL TIME. Against a fast-killing
opponent, fix the dying before expecting position work to pay. Also explains why the same feature
produced 1942 active post-ticks vs focusfire and only 472 here.

### Kill events DO carry positions (killer_x/y, victim_x/y) — my first pass wrongly concluded they didn't

Evidence: I filtered on `'x' in v` and got zero rows, concluding position was absent. The actual
schema is `{"victim_slot":12,"victim_label":"...","victim_x":461,"victim_y":217,"killer_x":713,
"killer_y":401}` — and `r['player']` is the KILLER slot. Dumping one raw row settled it in seconds.
Status: dump one raw event row before writing any extraction over an unfamiliar reader build.

### FIREFIGHT MODE built (v34-pending, flags OFF): intentional target selection + local focus claims

Evidence: beacon's combat WAS one line — `min(visible_enemies, key=distance)` (action.py:87-91).
New `fight.py` scores each visible enemy on wound / range-band / claim / shootability / aim-cost /
shield and latches with hysteresis; new `FI`/`FC` claim shouts sit at `C>T>O>G>U>K>F>E>P`.
Verified numerically: a claim (0.12) breaks a tie above the 0.10 switch margin but CANNOT drag a bot
off a better target (wounded@150px 0.940 vs claimed-healthy@340px 0.530); one wound level (0.25)
outweighs a claim. Behaviour change confirmed on the measured gap: two healthy enemies at 187px
(our habit) and 260px (ideal band) -> old rule picks 187, firefight picks 260.
154 tests pass (was 117). Both flags default OFF.
Status: NOT uploaded. `BEACON_FIREFIGHT` / `BEACON_FOCUS_CLAIMS` gate it independently so the A/B
can separate better target choice from coordination.

### Enemy HP was observable all along and beacon was discarding it — the docstring even said so

Evidence: the game emits `hp <lit>/3` as a distinct object **fog-gated with each player**
(`labels.nim` LabelPrefixHp), so any visible enemy's health is readable. beacon's
`perception._overhead_state` scanned every `hp ` object, kept only the one nearest ITSELF, and
dropped the rest — while its own docstring said "a wounded enemy's hp is readable intel".
Status: two traps encoded in the new code: (1) the numerator is LIT BAR SEGMENTS, not hit points
(`hp + shieldHp` mapped onto thirds; the game source warns they coincide today only because
hitPoints also defaults to 3), and (2) it INCLUDES shield, so a shielded enemy reads high — which
usefully doubles as shield detection.

### GV23 changes fight economics: shields BREAK, and kills EXTEND the clock

Evidence: `absorbDamage` (sim.nim:4523-4539) — a shield absorbs up to 3hp and the moment it empties
the shield is GONE along with the wearer's 3x `ShieldFireSlowdown`. So the first 3hp into a shielded
enemy buys no kill but strips armor AND removes their fire penalty (an externality: good for the
team, briefly better for them). `floorGameClock` + `ActionClockFloorTicks = 500` — any kill or steal
within 500 ticks of the limit banks overtime, so late aggression BUYS time instead of risking it.
Status: both now reflected in scoring (small shield penalty, 0.10) and both argue for finishing
kills rather than stalling. Neither was known to beacon before.

### Verify a mechanism by RUNNING it, not by reading the diff — but check your fixture first

Evidence: my first two firefight checks reported `firefight_active=False` and `select_target=None`,
looking like dead code. Both were MY fixtures: `update_firefight` requires `belief.alive` (I left it
False) and `select_target` requires `firefight_active` (never set). Third attempt with a correct
fixture showed the mechanism working exactly as designed. This is the SECOND time this session an
ad-hoc fixture produced a false "feature is dead" reading (the first was `PlayerTrack.identity`
being an int seat, not a nameplate string).
Status: when an ad-hoc check says a new feature does nothing, suspect the fixture before the code.

### Sweepable knobs need a REGISTRY, not just env vars — and the registry must generate the values

Evidence: James asked for the weights to be "surfaced somewhere easy to change" for optimization
sweeps. All 21 firefight knobs were already `_env_float`-backed (so sweepable via `--secret-env`),
but config.py has **122** env knobs and NOTHING enumerated them — a sweep harness would hardcode the
list and drift. Built `TUNABLE_REGISTRY` + `ctf.beacon.tuning` CLI: 23 registered tunables with
ranges, 8 cross-knob invariants, `dump` (JSON for a harness) and `secret-env` (emits the exact
upload flags).
Status: the strong form is that the registry **generates** the config values (`_float_tunable(...)`),
so a default cannot disagree with its registration by construction. A test additionally asserts the
registered `BEACON_FF_*` set equals the env vars found in the config source — I PROVED it fails by
injecting a raw `_env_float("BEACON_FF_BOGUS")` that bypassed the registry.

### Encode cross-knob invariants so a sweep can't propose an incoherent arm

Evidence: 8 invariants now reject bad configs BEFORE any hosted episodes are burned. Verified by
running them: `FF_CLAIM_WEIGHT=0.9` -> rejected ("claim bonus may not exceed one health-bar segment
of wound score" — machine-enforcing James's soft-bias-not-order rule); `FF_RANGE_IDEAL_MAX_PX=500`
-> rejected (band must stay inside the 350px fire gate); `FOCUS_CLAIMS=true` alone -> rejected
(claims require firefight). Also encoded: `FF_DEATH_MISSING_TICKS < FF_TARGET_MISSING_TICKS <
FF_CLAIM_TTL_TICKS`, a real ordering the claim lifecycle depends on.
Status: this is the cheapest possible place to catch a bad sweep arm — an invalid config costs one
CLI error instead of a 10-episode batch.

### Codex caught an unobservable requirement in my spec: beacon cannot trace kill range

Evidence: I specified a "kill-range distribution" trace as the primary mechanism metric. Codex
correctly refused — beacon has NO kill percept (no corpse reading, no damage event). Corrected
split: beacon traces SHOT range and SELECTED-TARGET range (which it knows); true kill range comes
from replay ground truth via `killer_x/y` + `victim_x/y`, which is how the 187px-vs-222px figure was
computed in the first place.
Status: when specifying tracing, check each field is derivable from the POLICY's observations, not
from the analysis pipeline's.

### Flags-off byte-identity is worth proving against the committed baseline, not just a unit test

Evidence: generated 60 varied beliefs and compared `resolve_action` held_mask between the real HEAD
(v33) checkout and the new code with both flags off: **IDENTICAL, 60/60**. Codex's own off-path test
is good (it pre-seeds firefight state to prove the flag gates it) but tests the new tree against
itself; the cross-checkout comparison is what actually proves no regression risk in the champion
path.

### FIREFIGHT LADDER dispatched: 4 arms x 3 opponents x 30 eps = 360 episodes (v35-v38)

Evidence: one image `players-beacon:fight`, four env-flipped uploads, each layering ONE change so
the axes are separable:
- **v35 postsonly** — POSTS+POST_FACING (the v33 champion equivalent; the baseline)
- **v36 noclaim** — + FIREFIGHT (scored target selection, NO coordination)
- **v37 claims** — + FOCUS_CLAIMS (adds the F claim nudge)
- **v38 wide** — + POST_MIN_SEPARATION_PX=80 (wider spread, testing James's "tune spreading and
  focus fire to avoid friendly fire" hypothesis)
Opponents are the current top three, re-resolved at dispatch: **focusfire:v62** (rank 1),
**alphashot:v180** (rank 3), **h050:v1** (rank 5 — Jordan is rank 4 but has only 125 rounds vs
everyone else's 247, so excluded as an immature entry). 30 eps/arm chosen because the stance sweep
was null at n=10 (p=0.18); 30 roughly triples the power.
Status: xreq ids in `scratch/eval_fight_ab/xreq_ids.txt`. Read `friendly_fire_suppressed` per arm —
it is the metric that distinguishes "focus fire didn't help" from "focus fire made us hold fire".

### v33 (posts) CLIMBED THE LEAGUE: rank 5 @ 1559 -> rank 2 @ 1929 as rounds accrued

Evidence: at submit time the standings showed rank 5 @ 1559.21/157 rounds, which was v28-era
inherited history (the leaderboard is per-PLAYER, not per-version). 247 rounds later we are **rank 2
@ 1929.39**, behind only daveey (2293). This is independent confirmation that the posts A/B result
(40% vs focusfire, 20% vs h050) translated into league standing.
Status: the earlier lesson stands — post-submit standings are lagging and confounded, so judge a
version by its A/B and let the standings confirm days later.

### THE FIELD MOVED HARD AGAIN — re-resolve opponents at DISPATCH time, not from notes

Evidence: our alphashot profile was against **alphashot-ghost-red-ca3e95f:v1**. At dispatch the
division shows **alphashot:v180** (different policy name AND 180 versions on) and
**ctf-focusfire:v62** (was v56, and now rank 1 at 2293 — it overtook everyone). h035 -> h050 earlier
in the session was the same pattern.
Status: a policy_version_id from even a few hours ago may profile a policy that no longer exists.
Always `experience_request.py resolve --division ... --top N` immediately before composing bodies.

### The tunable registry caught TWO missing knobs the moment I tried to compose real arms

Evidence: composing the ladder required `POSTS`/`POST_FACING`, which were NOT registered — only the
posts *spacing* knobs were. `tuning secret-env POSTS=true` errored with "unknown tunable: POSTS",
which is exactly the drift the registry exists to surface. Registered both (28 tunables now) plus a
`post_facing_requires_posts` invariant mirroring `focus_requires_firefight`.
Status: the registry earns its keep at ARM-COMPOSITION time. Build the arms through the CLI rather
than hand-writing --secret-env flags; hand-written flags would have silently shipped an arm with
posts OFF, making every firefight number incomparable to the v33 champion.

### PLATFORM STALL RECURRED on a 360-episode batch (2026-07-29)

Evidence: all 12 xreqs sat `pending, 0 completed, 0 running, 0 failed` for 7+ minutes while the
division leaderboard advanced 246 -> 247 rounds — the cluster is executing league work, only ad-hoc
xreq dispatch is queued. Same signature as the ~16:00 stall yesterday. Earlier platform inspection
showed CTF sitting at its 100-job league cap with a p95 experience-request admission delay of ~65
minutes, which is a plausible mechanism for a 360-episode submission.
Status: budget HOURS not minutes for large batches; background a watcher and do other work rather
than polling. A 1-episode canary against a known-good opponent remains the fast way to tell
"malformed request" from "platform queued".
