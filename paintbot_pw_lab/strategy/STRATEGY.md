# Strategy: compiled foundation with measured improvements

This file is the source of truth for our Paintbot PW policy. The compiled BASIC is a build
product. Nobody edits compiled BASIC by hand. To change behavior, change this file or a
`skill.bas` and recompile (docs/designs/2026-09-30-strategy-file-format.md).

Thesis: retain the foundation's squad play while closing the measured gap to upstream
`reference/base-bassy-28030de6.bas`. Each behavior change has its own source commit,
compiled build and local screen; hosted evaluation decides field strength.
All strategy arithmetic is integer. Use Bassy integer division `\`, which truncates
toward zero; never use fixed-point `/`. Boolean outputs specified as 0/1 must remain
0/1 (use explicit branches, because Bassy comparisons return -1). Legacy scalar host
observations remain valid on Bassy. Implement exactly the component specifications below.
Write every expression in the given order, because truncation order changes results.

Reading aid (the compiler receives component fields, not this introduction):

- "Enemy seat" means a seat `i` with `i MOD 2 <> selfTeam` (observed slot parity). A disguise
  changes this parity, so a disguised teammate counts as an enemy. Do not use `playerTeam`.
- "Teammate seat" means a seat `i` with `i MOD 2 = selfTeam`.
- "d2 from A to B" means `(Bx - Ax) * (Bx - Ax) + (By - Ay) * (By - Ay)`, squared centimeters.
- "Heart j" means the control point `j`, with `controlX(j)`, `controlY(j)`, `controlOwner(j)`.
  Every loop over hearts runs `j = 0` while `j < heartCount() AND j < 64`.

## Primitives

### P.walkTo
- Summary: Walk toward a point. The engine paths around walls but not around water.
- Spec: Host command `walkTo(x, y)`.
- Status: specified (2026-10-05)

### P.lookAt
- Summary: Turn to face a point.
- Spec: Host command `lookAt(x, y)`.
- Status: specified (2026-10-05)

### P.shootAt
- Summary: Order a gun shot at a point.
- Spec: Host command `shootAt(x, y)`. The ray leaves six moves after the order.
- Status: specified (2026-10-05)

### P.chargeGrenade
- Summary: Charge a grenade, or throw it.
- Spec: Host command `chargeGrenade(flag)`. A tick with flag 0 after charging throws the grenade.
- Status: specified (2026-10-05)

### P.shout
- Summary: Speak a text message to every cog within 12.8 m.
- Spec: Host command `shout(strNew("text"))`. Enemies hear it too.
- Status: specified (2026-10-05)

## Knowledge

### K.self_motion
- Summary: Our own movement since the previous tick.
- Spec: In `__init`, set `last_x = selfX` and `last_y = selfY`. In `__update`, on every tick, do
  these steps in order. Step 1: set `vx = selfX - last_x` and `vy = selfY - last_y`. Step 2: if
  `vx > teleport_step OR vx < 0 - teleport_step OR vy > teleport_step OR vy < 0 - teleport_step`,
  set `vx = 0`, `vy = 0` and `teleported = 1`. Else set `teleported = 0`. Step 3: set
  `last_x = selfX` and `last_y = selfY`.
- Sources: `selfX`, `selfY`
- Memory: last_x and last_y, our position on the previous living tick. Never reset.
- Outputs:
  - vx -- our x movement since the previous tick, cm per tick (0 after a teleport)
  - vy -- our y movement since the previous tick, cm per tick (0 after a teleport)
  - teleported -- 1 when the movement was a respawn jump, else 0
- Params:
  - teleport_step = 60 cm -- base.bas value. A respawn moves more than this on one axis.
- Checks:
  - True: vx and vy equal the replay position change, except both are zero on initialization or when either axis exceeds teleport_step. Reads: replay
- Status: specified (2026-10-05)
- Rationale: base.bas computes myVX and myVY at the top of the tick and stores lastX at the end.
  selfX does not change during a tick, so storing it here gives the same values.

### K.squad_target
- Summary: The heart that our squad of four attacks, derived from squad arithmetic, heart
  ownership and our own avoid memory.
- Spec: In `__update`, on every tick, do Steps 1 to 4 in order.
  Step 1 (stall memory). This step reads the value of `objective` from the previous tick. It is 0
  before the first assignment, not -1. When `worldTick MOD progress_period = 0`: set
  `px = selfX - progress_x` and `py = selfY - progress_y`. If
  `px * px + py * py < stall_sq AND objective >= 0 AND objective < 64`, set
  `hx = controlX(objective) - selfX` and `hy = controlY(objective) - selfY`. If
  `hx * hx + hy * hy > far_sq`, set `avoid_until(objective) = worldTick + avoid_ticks`. Then, on
  every tick where `worldTick MOD progress_period = 0`, set `progress_x = selfX` and
  `progress_y = selfY`.
  Step 2 (squad). Set `member = (selfId \ 2) MOD 8`, `squad = member \ 4`, `seat = member MOD 4`.
  Step 3 (target). Set `objective = -1`. If `heartCount() > 0`, do the two passes below. Else
  skip to Step 4.
  Set `other = -1`. Run `pass = 0` then `pass = 1`. In each pass, set `ref_y = homeY - ref_offset`
  for pass 0, and `ref_y = homeY + ref_offset` for pass 1. Then, if `selfTeam = 1`, set
  `ref_y = mirror_y - ref_y`. Set `choice = -1` and `choice_cost = 2147483647`.
  For `j = 0` while `j < heartCount() AND j < 64`, skip j when `controlOwner(j) = selfTeam` or `j = other`. Else set
  `dx = (controlX(j) - homeX) \ 8`, `dy = (controlY(j) - ref_y) \ 8`, and
  `cost = dx * dx + dy * dy`. If `controlOwner(j) = -1`, subtract `neutral_bonus` from cost. If
  `pass = squad AND avoid_until(j) > worldTick`, add `avoid_penalty` to cost. If
  `cost < choice_cost`, set `choice = j` and `choice_cost = cost`. Strict less-than keeps the
  lowest index on a tie.
  At the end of each pass: if `pass = squad`, set `objective = choice`. Else, if `pass < squad`,
  set `other = choice`. After both passes: if `objective < 0 AND other >= 0`, set
  `objective = other`.
  Step 4 (idle capture). If `objective >= 0 AND seat >= 2`: if
  `controlCaptureTeam(objective) = selfTeam`, set `idle_capture = 0`. Else add 1 to
  `idle_capture`. In all other cases do not change `idle_capture`.
  Also set `heart_count = heartCount()` on every tick.
- Sources: `selfId`, `selfTeam`, `selfX`, `selfY`, `homeX`, `homeY`, `worldTick`, `heartCount`,
  `controlX`, `controlY`, `controlOwner`, `controlCaptureTeam`
- Memory: avoid_until (64 cells, a private array, ticks), progress_x, progress_y, objective and
  idle_capture persist for the whole match. Nothing resets them on death, respawn or a rule
  change. All start at 0.
- Outputs:
  - objective -- the target heart index, or -1 when there is none
  - squad -- 0 or 1, from selfId
  - seat -- 0 to 3, our place in the squad (2 and 3 cover)
  - idle_capture -- ticks in a row that our team was not capturing the objective (cover seats)
  - heart_count -- heartCount() on this tick
- Log: objective, idle_capture every 24 ticks
- Params:
  - progress_period = 72 ticks -- base.bas value, three seconds
  - stall_sq = 40000 square cm -- base.bas value, less than 2 m of progress
  - far_sq = 160000 square cm -- base.bas value, more than 4 m from the heart
  - avoid_ticks = 360 ticks -- base.bas value, fifteen seconds
  - ref_offset = 1500 cm -- base.bas value, squad reference point above or below home
  - mirror_y = 4000 cm -- base.bas value, blue mirrors the reference y about this line
  - neutral_bonus = 20000 -- base.bas value, cost bonus of a neutral heart
  - avoid_penalty = 4000000 -- base.bas value, cost added to an avoided heart on our own pass
- Checks:
  - Believed: objective is logged as a heart index or -1. Reads: `K.squad_target`.objective
  - True: the logged objective equals the replay re-computation using public heart state and this cog's reconstructed avoid memory. Reads: `K.squad_target`.objective, replay
- Status: specified (2026-10-05)
- Rationale: base.bas says the target is a pure function of public heart state. That is not
  exactly true. Each cog applies its own avoid_until memory in its own pass. A squad 1 cog
  predicts the squad 0 choice without squad 0's avoid memory. So two cogs of one squad can
  disagree after one of them marks a heart as stalled.

### K.contacts
- Summary: The visible enemy we fight, the visible enemy carrier, and the local fight balance.
- Spec: In `__update`, on every tick, do Steps 1 to 4 in order.
  Step 1. Set `best = -1`, `best_cost = 2147483647`, `thief = -1`, `foes_near = 0`,
  `friends_near = 1` (we count ourselves), `foe_sum_x = 0`, `foe_sum_y = 0`, `foes_seen = 0`.
  Step 2. For `i = 0` to 15, use seat i only when `i <> selfId AND visible(i)`. Set
  `dx = playerX(i) - selfX`, `dy = playerY(i) - selfY`, `d2 = dx * dx + dy * dy`.
  For an enemy seat (`i MOD 2 <> selfTeam`, not playerTeam): set `cost = d2 - (3 - playerHp(i)) * hp_weight`. If `playerCarrying(i)`,
  subtract `carrier_bonus` from cost and set `thief = i`. Then, if
  `cost < best_cost AND d2 <= gunRange() * gunRange()`, set `best = i` and `best_cost = cost`.
  For activation tracing, independently count each visible enemy observation with
  `d2 <= former_range_sq AND d2 > gunRange() * gunRange()` by adding 1 to
  `range_rejected_total`. This counter is cumulative across ticks, starts at zero, and
  never changes target ranking or other behavior. Then add 1 to
  `foes_seen`, add `playerX(i)` to `foe_sum_x` and `playerY(i)` to `foe_sum_y`. If
  `d2 < near_foe_sq`, add 1 to `foes_near`.
  For a teammate seat (`i MOD 2 = selfTeam`): if `d2 < near_friend_sq`, add 1 to `friends_near`.
  Step 3. Set `best_vx = 0` and `best_vy = 0`. If `best >= 0 AND seen_tick(best) = worldTick - 1`,
  set `best_vx = playerX(best) - old_x(best)` and `best_vy = playerY(best) - old_y(best)`.
  The memory arrays start at 0, so on tick 1 this test compares with 0. Keep that.
  Step 4. For every seat `i = 0` to 15, our own seat included, with `visible(i)`: set
  `old_x(i) = playerX(i)`, `old_y(i) = playerY(i)` and `seen_tick(i) = worldTick`.
  Also set `foe_cx = foe_sum_x \ foes_seen` and `foe_cy = foe_sum_y \ foes_seen` when
  `foes_seen > 0`. Else set both to 0.
- Sources: `selfId`, `selfTeam`, `selfX`, `selfY`, `worldTick`, `visible`, `playerX`, `playerY`,
  `playerHp`, `playerCarrying`, `gunRange`
- Memory: range_rejected_total persists for the whole match, initialized to 0.
  Also, old_x, old_y and seen_tick (16 cells each, private arrays) persist for the whole match.
  Step 3 reads them before Step 4 overwrites them. That is the same as base.bas, which aims
  first and updates old positions after aiming.
- Outputs:
  - best -- the enemy seat to fight, or -1
  - best_cost -- the cost of best (smaller is more urgent)
  - best_vx -- best's x movement since the previous tick, or 0
  - best_vy -- best's y movement since the previous tick, or 0
  - thief -- the highest-index visible enemy seat that carries a heart, or -1
  - foes_near -- visible enemy seats closer than 26 m
  - friends_near -- 1 plus visible teammate seats closer than 12 m
  - foes_seen -- visible enemy seats at any range
  - foe_cx -- mean x of visible enemy seats, or 0
  - foe_cy -- mean y of visible enemy seats, or 0
  - range_rejected_total -- cumulative visible enemy observations excluded by the real gun range but within the former range
- Log: best, foes_near, friends_near, range_rejected_total every 24 ticks
- Params:
  - hp_weight = 160000 -- base.bas value, cost bonus per missing hit point
  - carrier_bonus = 2500000 -- base.bas value, cost bonus of a heart carrier
  - former_range_sq = 27562500 square cm -- former 52.5 m cap, used only for activation tracing
  - near_foe_sq = 6760000 square cm -- base.bas value, 26 m
  - near_friend_sq = 1440000 square cm -- base.bas value, 12 m
- Checks:
  - Believed: best and the near counts are logged. Reads: `K.contacts`.best, `K.contacts`.foes_near, `K.contacts`.friends_near
  - True: the logged best is a visible enemy-parity seat in the replay within range. Reads: `K.contacts`.best, replay
- Status: specified (2026-10-05)

### K.pickups
- Summary: Supplies seen in the last ten seconds, and the nearest one we want at our observed spawn HP.
- Spec: In `__update`, first set `hp_cap = selfHp` when `selfHp > hp_cap`.
  Set `critical = 1` when `selfHp > 0 AND selfHp * 3 <= hp_cap`, else 0.
  Then do Steps 1 to 3 in order.
  Step 1 (refresh). For `i = 0` while `i < pickupCount() AND i < 64`: if `pickupVisible(i)`, set
  `mem_x(i) = pickupX(i)`, `mem_y(i) = pickupY(i)`, `mem_kind(i) = pickupKind(i)` and
  `mem_tick(i) = worldTick + 1`.
  Step 2 (carrier). Set `carrier = 0`. For `i = 0` to 15, set `carrier = 1` when
  `i <> selfId AND visible(i) AND i MOD 2 <> selfTeam AND playerCarrying(i)`.
  Step 3 (choice). Set `nearest = -1`, `nearest_x = 0`, `nearest_y = 0`. Do the rest of this step
  only when `carrying = 0 AND carrier = 0`. Set `nearest_cost = reach_sq`. For `j = 0` while
  `j < pickupCount() AND j < 64`, use j only when
  `mem_tick(j) > 0 AND worldTick - mem_tick(j) < memory_ticks`. Set `kind = mem_kind(j)` and
  `wanted = (kind = 0 AND hasGrenade = 0) OR (kind = 2 AND selfHp < hp_cap) OR (kind = 3 AND armorHp < 3 AND selfHp = hp_cap)`.
  For activation tracing only, compute `old_wanted` with the same expression but both
  `hp_cap` references replaced by 3. If the truth of wanted differs from old_wanted,
  increment `hp_changed_total` once for this remembered pickup observation.
  If wanted: set `dx = mem_x(j) - selfX`, `dy = mem_y(j) - selfY`, and
  `cost = dx * dx + dy * dy`. Then, if
  `kind = 2 AND critical = 1`, set `cost = cost \ 4`. Then, if
  `cost < arrive_sq AND pickupVisible(j) = 0`, set `mem_tick(j) = 0` and do not use j. Else, if
  `cost < nearest_cost`, set `nearest = j` and `nearest_cost = cost`.
  After the loop, if `nearest >= 0`, set `nearest_x = mem_x(nearest)` and
  `nearest_y = mem_y(nearest)`.
- Sources: `pickupCount`, `pickupVisible`, `pickupX`, `pickupY`, `pickupKind`, `visible`,
  `playerCarrying`, `carrying`, `hasGrenade`, `selfHp`, `armorHp`, `selfX`, `selfY`, `worldTick`
- Memory: hp_cap and hp_changed_total start at 0 and persist for the whole match.
  mem_x, mem_y, mem_kind and mem_tick (64 cells each, private arrays) persist for the
  whole match and start at 0.
- Outputs:
  - nearest -- the remembered supply to fetch, or -1
  - nearest_x -- its remembered x, or 0
  - nearest_y -- its remembered y, or 0
  - hp_cap -- maximum selfHp observed since initialization
  - critical -- 1 when alive and at most one third of hp_cap, else 0
  - hp_changed_total -- cumulative remembered pickup observations whose eligibility changed with spawn-HP thresholds
- Log: nearest, hp_cap, hp_changed_total every 24 ticks
- Params:
  - memory_ticks = 240 ticks -- base.bas value, ten seconds
  - reach_sq = 4840000 square cm -- base.bas value, 22 m
  - arrive_sq = 10000 square cm -- base.bas value, 1 m. A remembered supply this close and not visible is gone.
- Checks:
  - Believed: the chosen supply is logged. Reads: `K.pickups`.nearest
  - True: a supply of the remembered kind was at the remembered point in the replay. Reads: `K.pickups`.nearest, replay
- Status: specified (2026-10-05)
- Rationale: Step 2 repeats the carrier test of `K.contacts` because a Knowledge component cannot
  use another Knowledge component. The result is the same as base.bas's `thief < 0` guard.

## Situations

### S.losing_fight
- Summary: We see more near enemies than near friends, so we refuse the fight.
- Spec: Set `on = 1` when
  `foes_near - friends_near >= 1 AND carrying = 0 AND heart_count > 0`, using the outputs of
  `K.contacts` and `K.squad_target`. Else set `on = 0`.
- Uses: `K.contacts`, `K.squad_target`
- Checks:
  - Believed: the flag is logged with the decision. Reads: PWD.f
- Status: specified (2026-10-05)
- Rationale: The heart_count term covers a base.bas case. With no heart, the retreat block finds
  no heart and keeps the earlier goal.

### S.supply_worth
- Summary: A wanted supply is remembered and no close fight stops us from fetching it.
- Spec: Set `on = 1` when `nearest >= 0` of `K.pickups` and
  `(best < 0 OR best_cost > fight_clear_sq OR critical = 1)` with best and best_cost of
  `K.contacts`, and critical of `K.pickups`. Else set `on = 0`.
- Uses: `K.pickups`, `K.contacts`
- Params:
  - fight_clear_sq = 1440000 -- base.bas value, cost above which the target does not hold us
- Checks:
  - Believed: the flag is logged with the decision. Reads: PWD.f
- Status: specified (2026-10-05)
- Rationale: `K.pickups` already applies the carrying and carrier guards.

### S.has_target_heart
- Summary: Our squad has a target heart.
- Spec: Set `on = 1` when objective of `K.squad_target` is 0 or more. Else set `on = 0`.
- Uses: `K.squad_target`
- Checks:
  - Believed: the flag is logged with the decision. Reads: PWD.f
- Status: specified (2026-10-05)

## Skills

### SK.motor
- Summary: The baseline mechanics. Look around, dodge with timed legs, route around water, aim
  with lead, hold fire on teammates, and finish committed grenade charges.
- Spec: The code is authored in `skill.bas`. A capability calls `sk_motor__act(gx, gy, hold)`
  exactly once on every tick, with its goal point and holding flag. `act` runs six parts in
  this order. They are the gun wait countdown, the look sweep, footwork, the dry route with the
  one `walkTo`, the gun, and the grenade. The look sweep runs only when there is no target. `sk_motor__isqrt(n)` puts the integer square root of n
  into the output root. Grenades retain the original visible-teammate and distance checks
  when starting, and additionally require mistingTicks() and radarTicks() to be zero.
  On a start, lock the aim point and required charge. Continue charging toward that point
  until the locked charge is reached, even if contact or start eligibility is lost; do not
  let an omitted command release an undercharged grenade. Reset commitment after release
  or loss of the grenade. Rules 49 forces release if disarmed mid-charge; count that event.
  During an existing committed charge, while armed, if the current target passes the same
  existing visibility, distance and teammate-safety checks (eligible = 1), refresh locked_x,
  locked_y and locked_need to nx, ny and need before deciding whether to keep charging.
  Increment tracking_updates_total once on a tick where any of those three values changes.
  On lost eligibility retain the last safe aim and need, and continue the original committed
  charge logic. Never release merely because visibility or eligibility disappeared.
  This is charge continuity with safe target tracking, not a guarantee that teammates cannot
  enter the eventual blast.
  Before footwork, compute spray_distance_sq from self to the current best target's actual
  playerX/playerY coordinates when best of `K.contacts` is nonnegative. Use this distance
  instead of best_cost in both spray-range tests: footwork want_shot and the gun's firing
  gate. Keep the existing strict spray_range_sq threshold and every other gate unchanged.
  Best_cost remains the HP-weighted ranking score; do not treat it as a physical distance.
  After an actual shootAt request with hasSpray, increment spray_distance_shots_total if
  the former best_cost test would have rejected it. This counter starts at zero and persists.
  Count starts, disarmed start blocks, ticks where continuation avoids the original release,
  and forced disarmed releases. Expose the release charge and locked need for each throw.
- Uses: `P.walkTo`, `P.lookAt`, `P.shootAt`, `P.chargeGrenade`, `K.contacts`, `K.self_motion`
- Code: skills/motor/skill.bas
- Outputs:
  - root -- the result of the last sk_motor__isqrt call
  - threw -- 1 on a commanded or forced grenade release tick, else 0
  - release_charge -- observed charge on this release decision
  - release_need -- committed charge required for this throw
  - starts_total -- cumulative committed grenade starts
  - blocked_total -- cumulative otherwise eligible starts blocked while disarmed
  - continued_total -- cumulative ticks where continuity prevents the old early release
  - forced_total -- cumulative releases forced by becoming disarmed during a charge
  - tracking_updates_total -- cumulative armed charging ticks with a changed safe aim or charge requirement
  - spray_distance_shots_total -- actual spray requests enabled by the physical-distance range check
- Params:
  - wet_cost = 6 -- base.bas value, a wet metre costs this many dry metres in the dry route
  - lead_ticks = 6 ticks -- base.bas value, the gun windup
  - drift_ticks = 5 ticks -- base.bas value, our own drift to cancel
  - gun_wait_light = 25 ticks -- base.bas value, gun cooldown
  - gun_wait_heavy = 73 ticks -- base.bas value, cooldown with armor, in a trench, or carrying
  - spray_range_sq = 640000 -- base.bas value, the spray gun shoots only below this target cost
- Checks:
  - Acted properly: a shot is ordered only when the gun wait is zero, the teammate line is clear, and the spray range condition holds. Reads: replay
  - Acted: committed grenade charge continues until its locked need unless equipment is lost or disarm forces release. Reads: replay
  - Result: grenade teammate and self damage per episode, with enemy damage retained. Reads: replay
  - Result: hit rate per shot at range. Reads: replay
- Status: specified (2026-10-05)

## Capabilities

### C.take_heart
- Summary: Stand in the capture ring of the squad target (squad seats 0 and 1).
- Spec: `__start` does nothing. `__tick` does these steps in order. Step 1: set
  `goal_x = controlX(objective)` and `goal_y = controlY(objective)`, with objective of
  `K.squad_target`. Step 2: set `dx = goal_x - selfX` and `dy = goal_y - selfY`. Set `hold = 1` when
  `dx * dx + dy * dy < hold_sq`. Else set `hold = 0`. Step 3: call `sk_motor__act(goal_x, goal_y, hold)` of
  `SK.motor`. Step 4 (quiet approach): call the host command `sneak(1)` when all of these hold. best
  of `K.contacts` is less than 0. `soundCount() > 0`. `(controlX(objective) - selfX) * (controlX(objective) - selfX) +
  (controlY(objective) - selfY) * (controlY(objective) - selfY) < quiet_sq`, with objective of
  `K.squad_target`. Step 5: set status to 0.
- Uses: `K.squad_target`, `K.contacts`, `SK.motor`
- Params:
  - hold_sq = 8100 square cm -- base.bas value, within 90 cm of the post
  - quiet_sq = 810000 square cm -- base.bas value, within 9 m of the objective
- Done when: never
- Checks:
  - Acted: the rule selects this capability when the squad has a target. Reads: PWD.r, PWD.c
  - Result: our team captures the target heart during the activation. Reads: PWE.e, replay
- Status: specified (2026-10-05)

### C.cover_heart
- Summary: Cover the squad target from outside the ring, and step in when nobody captures it
  (squad seats 2 and 3).
- Spec: `__start` does nothing. `__tick` does these steps in order. Step 1: set
  `hx = controlX(objective)`, `hy = controlY(objective)`, with objective of `K.squad_target`.
  Set `goal_x = hx` and `goal_y = hy`. Step 2: set `dx = hx - selfX` and `dy = hy - selfY`. If
  `dx * dx + dy * dy > step_in_sq OR idle_capture < idle_limit`, with idle_capture of
  `K.squad_target`, compute the cover post. Set `side = 1`, or `side = -1` when seat of
  `K.squad_target` is 3. Set `ax = post_x - hx` and `ay = post_y - hy`. If `selfTeam = 0`, add
  `post_shift` to ax. Else subtract `post_shift` from ax. Call `sk_motor__isqrt(ax * ax + ay * ay)`
  of `SK.motor`. If root of `SK.motor` is more than 0, set
  `goal_x = hx + (ax * 3 - ay * 2 * side) * post_radius \ root` and
  `goal_y = hy + (ay * 3 + ax * 2 * side) * post_radius \ root`. Step 3: set `dx = goal_x - selfX` and `dy = goal_y - selfY`. Set `hold = 1` when
  `dx * dx + dy * dy < hold_sq`. Else set `hold = 0`. Step 4: call
  `sk_motor__act(goal_x, goal_y, hold)`. Step 5 (quiet approach): call the host command
  `sneak(1)` when all of these hold. best of `K.contacts` is less than 0. `soundCount() > 0`. `(controlX(objective) - selfX) * (controlX(objective) - selfX) +
  (controlY(objective) - selfY) * (controlY(objective) - selfY) < quiet_sq`, with objective of
  `K.squad_target`. Step 6: set status to 0.
- Uses: `K.squad_target`, `K.contacts`, `SK.motor`
- Params:
  - step_in_sq = 640000 square cm -- base.bas value, 8 m
  - idle_limit = 96 ticks -- base.bas value, four seconds without our team capturing
  - post_x = 3200 cm -- base.bas value, x of the point the post faces away from
  - post_y = 2000 cm -- base.bas value, y of the point the post faces away from
  - post_shift = 1200 cm -- base.bas value, team offset of that point
  - post_radius = 90 -- base.bas value, post distance scale
  - hold_sq = 8100 square cm -- base.bas value, within 90 cm of the post
  - quiet_sq = 810000 square cm -- base.bas value, within 9 m of the objective
- Done when: never
- Checks:
  - Acted: the rule selects this capability when the squad has a target. Reads: PWD.r, PWD.c
  - Acted properly: a cover cog stays near its post while a teammate captures. Reads: `K.squad_target`.idle_capture, replay
- Status: specified (2026-10-05)

### C.default_goal
- Summary: With no squad target, go for the thief, home, or the heart.
- Spec: `__start` does nothing. `__tick` does these steps in order. Step 1: with thief of
  `K.contacts`: if `carrying`, then the goal is the position of thief when
  `ownHeartStolen AND thief >= 0`, else `(homeX, homeY)`. If not carrying, the goal is the
  position of thief when `thief >= 0`, else `(heartX, heartY)`. The position of a seat is
  `(playerX(seat), playerY(seat))`. Step 2: call `sk_motor__act(goal_x, goal_y, 0)` of
  `SK.motor`. Step 3 (quiet approach): call the host command `sneak(1)` when all of these
  hold. best of `K.contacts` is less than 0. `soundCount() > 0`. objective of `K.squad_target` is
  0 or more. `(controlX(objective) - selfX) * (controlX(objective) - selfX) +
  (controlY(objective) - selfY) * (controlY(objective) - selfY) < quiet_sq`. Step 4: set status to 0.
- Uses: `K.contacts`, `K.squad_target`, `SK.motor`
- Params:
  - quiet_sq = 810000 square cm -- base.bas value, within 9 m of the objective
- Done when: never
- Checks:
  - Acted: the rule selects this capability when no other rule holds. Reads: PWD.r, PWD.c
- Status: specified (2026-10-05)
- Rationale: The rule selects this capability only when objective is -1. Step 3 never fires then.
  It stays for a literal match with base.bas.

### C.resupply
- Summary: Walk to the remembered supply.
- Spec: `__start` does nothing. `__tick` does these steps in order. Step 1: call
  `sk_motor__act(nearest_x, nearest_y, 0)` of `SK.motor`, with nearest_x and nearest_y of
  `K.pickups`. Step 2 (quiet approach): call the host command `sneak(1)` when all of these
  hold. best of `K.contacts` is less than 0. `soundCount() > 0`. objective of `K.squad_target` is
  0 or more. `(controlX(objective) - selfX) * (controlX(objective) - selfX) +
  (controlY(objective) - selfY) * (controlY(objective) - selfY) < quiet_sq`. Step 3: set status to 0.
- Uses: `K.pickups`, `K.contacts`, `K.squad_target`, `SK.motor`
- Params:
  - quiet_sq = 810000 square cm -- base.bas value, within 9 m of the objective
- Done when: never
- Checks:
  - Acted: the rule selects this capability when a supply is worth it. Reads: PWD.r, PWD.c
  - Result: we take a supply during the activation. Reads: PWE.e, replay
- Status: specified (2026-10-05)

### C.fall_back
- Summary: Head for the heart that is far from the enemies and near us.
- Spec: `__start` does nothing. `__tick` does these steps in order. Step 1: set
  `cx = foe_cx` and `cy = foe_cy` of `K.contacts`. Set `away = -1` and
  `away_score = -2147483647`. For `j = 0` while `j < heartCount() AND j < 64`, set `ex = (controlX(j) - cx) \ 16`,
  `ey = (controlY(j) - cy) \ 16`, `mx = (controlX(j) - selfX) \ 16`,
  `my = (controlY(j) - selfY) \ 16`, and `score = ex * ex + ey * ey - (mx * mx + my * my) \ 2`.
  If `score > away_score`, set `away = j` and `away_score = score`. Step 2: if `away >= 0`, the
  goal is `(controlX(away), controlY(away))`. Else the goal is our own position. Step 3: call
  `sk_motor__act(goal_x, goal_y, 0)` of `SK.motor`. Step 4 (quiet approach): call the host command
  `sneak(1)` when all of these hold. best of `K.contacts` is less than 0. `soundCount() > 0`.
  objective of `K.squad_target` is 0 or more. `(controlX(objective) - selfX) * (controlX(objective) - selfX) +
  (controlY(objective) - selfY) * (controlY(objective) - selfY) < quiet_sq`. Step 5:
  set status to 0.
- Uses: `K.contacts`, `K.squad_target`, `SK.motor`
- Params:
  - quiet_sq = 810000 square cm -- base.bas value, within 9 m of the objective
- Done when: never
- Checks:
  - Acted: the rule selects this capability when we are losing the fight. Reads: PWD.r, PWD.c
  - Result: we survive the activation. Reads: PWE.e, replay
- Status: specified (2026-10-05)
- Rationale: `S.losing_fight` needs a heart, so away is never -1 here. A losing fight also means a
  visible target, so Step 4 never fires. Both stay for a literal match with base.bas.

## Strategy

### ST.roles
- Summary: Two squads of four per team. Seats 0 and 1 of a squad take the ring, seats 2 and 3 cover.
- Spec: The squad seat is `((selfId \ 2) MOD 8) MOD 4`. Ring seats have squad seat 0 or 1.
  Cover seats have squad seat 2 or 3.
- Roles squad:
  - ring = seats 0,1,2,3,8,9,10,11
  - cover = seats 4,5,6,7,12,13,14,15
- Checks:
  - Acted: ring seats select only ring or shared rules. Reads: PWD.r
- Status: specified (2026-10-05)

### ST.rules
- Summary: Retreat beats resupply, resupply beats the squad target, the squad target beats the default goal.
- Spec: Evaluate the rules below each tick. The highest priority rule whose condition holds wins.
- Checks:
  - Acted properly: re-running selection from the logged flags gives the logged rule. Reads: PWD.r, PWD.f, PWP.n
- Status: specified (2026-10-05)
- Rationale: base.bas computes one goal and lets later blocks override it. The retreat block
  comes last, then supply, then the squad target. These priorities give the same order.
- `R.fall_back` [400]: WHEN `S.losing_fight` DO `C.fall_back`
- `R.resupply` [300]: WHEN `S.supply_worth` DO `C.resupply`
- `R.take_heart` [200]: WHEN `S.has_target_heart` DO `C.take_heart` FOR squad=ring
- `R.cover_heart` [200]: WHEN `S.has_target_heart` DO `C.cover_heart` FOR squad=cover
- `R.default_goal` [100]: ALWAYS DO `C.default_goal`

### ST.commitment
- Summary: Select the best rule on every tick. Keep nothing from earlier ticks.
- Spec: Switch to the best rule as soon as it differs from the current rule.
- Params:
  - min_hold = 0 ticks -- base.bas has no commitment
  - preempt_margin = 0 points -- base.bas has no commitment
  - interrupt_at = 0 points -- every better rule interrupts at once
- Checks:
  - Acted properly: the selected rule is always the best rule. Reads: PWD.h, PWD.r
- Status: specified (2026-10-05)

## Communication

### COM.status_call
- Summary: Every fifteen seconds, say whether we are in contact, falling back, or moving.
- Spec: In `__send`, when `worldTick MOD 360 = selfId * 21`, shout one message. If best of
  `K.contacts` is 0 or more, shout "Contact! Cover this lane.". Else, if
  `foes_near - friends_near >= 1` of `K.contacts`, shout "Too many. Falling back.". Else shout
  "Moving with the squad.". Set sent to 1 on a tick with a shout, else 0.
  On a send, copy starts_total, blocked_total, continued_total, forced_total and
  tracking_updates_total and spray_distance_shots_total from `SK.motor` into same-named outputs
  for periodic telemetry.
- Uses: `K.contacts`, `SK.motor`, `P.shout`
- Content: our contact state. No teammate decodes it.
- Encoding: literal text, `shout(strNew("..."))`, with the three exact strings in Spec.
- Send when: `worldTick MOD 360 = selfId * 21`
- Outputs:
  - starts_total -- committed starts through this status snapshot
  - blocked_total -- disarmed start blocks through this status snapshot
  - continued_total -- rescued charging ticks through this status snapshot
  - forced_total -- disarmed forced releases through this status snapshot
  - tracking_updates_total -- safe aim/need changes through this status snapshot
  - spray_distance_shots_total -- actual newly enabled spray requests through this snapshot
- Log: starts_total, blocked_total, continued_total, forced_total, tracking_updates_total, spray_distance_shots_total
- Directions: send
- Checks:
  - Acted: the shout appears in the replay on the scheduled ticks. Reads: replay
- Status: specified (2026-10-05)
- Rationale: Listeners turn to the first heard message. base.bas shouts this before the grenade
  call, so this component comes first.

### COM.grenade_out
- Summary: Call out a grenade when the charge is ready.
- Spec: In `__send`, when threw of `SK.motor` is 1, shout "Grenade out!" and set sent to 1. Else
  set sent to 0.
- Uses: `SK.motor`, `P.shout`
- Content: a warning. No teammate decodes it.
- Encoding: literal text, `shout(strNew("Grenade out!"))`
- Send when: threw of `SK.motor` is 1
- Directions: send
- Checks:
  - Acted: the shout appears in the replay with each full charge. Reads: replay
- Status: specified (2026-10-05)

## Open questions

- A Knowledge component cannot use another Knowledge component, so `K.pickups` repeats a carrier
  test. A Skill cannot use another Skill, so the mechanics are one skill.
