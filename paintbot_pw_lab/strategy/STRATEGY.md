# Strategy: baseline with comms v1 (M3 implementation)

This file is the source of truth for our Paintbot PW policy. The compiled BASIC is a build
product. Nobody edits compiled BASIC by hand. To change behavior, change this file or a
`skill.bas` and recompile (docs/designs/2026-09-30-strategy-file-format.md).

Thesis: this version keeps the `reference/base.bas` description and adds comms v1
(strategy/comms.md). Only communication and its receiver effects change behavior. All arithmetic is int32. Division truncates
toward zero. Write every expression in the order given here, because the order of truncation
changes results.

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
- Summary: Our own movement since the previous tick, and whether we lost hit points.
- Spec: In `__init`, set `last_x = selfX`, `last_y = selfY`, `last_hp = selfHp`, `last_uniform = 0` and
  `uniform_since = 0`. In `__update`, on every tick, do
  these steps in order. Step 1: set `vx = selfX - last_x` and `vy = selfY - last_y`. Step 2: if
  `vx > teleport_step OR vx < 0 - teleport_step OR vy > teleport_step OR vy < 0 - teleport_step`,
  set `vx = 0`, `vy = 0` and `teleported = 1`. Else set `teleported = 0`. Step 3: set
  `last_x = selfX` and `last_y = selfY`. Step 4: set `hp_drop = 1` when `selfHp < last_hp`, else set
  `hp_drop = 0`. Then set `last_hp = selfHp`. Step 5: if `hasUniform() = 1 AND last_uniform = 0`, set
  `uniform_since = worldTick + 1`. If `hasUniform() = 0`, set `uniform_since = 0`. Then set
  `last_uniform = hasUniform()`.
- Sources: `selfX`, `selfY`, `selfHp`, `hasUniform`
- Memory: last_x, last_y, last_hp and last_uniform, our position, hit points and uniform on the previous living
  tick. Never reset.
- Outputs:
  - vx -- our x movement since the previous tick, cm per tick (0 after a teleport)
  - vy -- our y movement since the previous tick, cm per tick (0 after a teleport)
  - teleported -- 1 when the movement was a respawn jump, else 0
  - hp_drop -- 1 when selfHp is lower than on the previous living tick, else 0
  - uniform_since -- the tick plus 1 when the current disguise started, or 0 when not disguised
- Params:
  - teleport_step = 60 cm -- base.bas value. A respawn moves more than this on one axis.
- Checks:
  - True: vx and vy equal the replay position change, except both are zero on initialization or when either axis exceeds teleport_step. Reads: replay
  - True: hp_drop is 1 exactly on living ticks where the replay hit points fell. Reads: replay
- Status: specified (2026-10-05)
- Rationale: base.bas computes myVX and myVY at the top of the tick and stores lastX at the end.
  selfX does not change during a tick, so storing it here gives the same values. hp_drop feeds
  `COM.under_fire` and uniform_since feeds `COM.disguise_friend`, because a COM send does not run on every
  tick. Steps 1 to 3 are unchanged.

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
  Step 2 (squad). Set `member = (selfId / 2) MOD 8`, `squad = member / 4`, `seat = member MOD 4`.
  Step 3 (target). Set `objective = -1`. If `heartCount() > 0`, do the two passes below. Else
  skip to Step 4.
  Set `other = -1`. Run `pass = 0` then `pass = 1`. In each pass, set `ref_y = homeY - ref_offset`
  for pass 0, and `ref_y = homeY + ref_offset` for pass 1. Then, if `selfTeam = 1`, set
  `ref_y = mirror_y - ref_y`. Set `choice = -1` and `choice_cost = 2147483647`.
  For `j = 0` while `j < heartCount() AND j < 64`, skip j when `controlOwner(j) = selfTeam` or `j = other`. Else set
  `dx = (controlX(j) - homeX) / 8`, `dy = (controlY(j) - ref_y) / 8`, and
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
- Summary: The visible enemy we fight, friend and hostile classification of visible bodies, the visible
  enemy carrier, the local fight balance, and the freshest heard enemy.
- Spec: In `__update`, on every tick, do Steps 0 to 6 in order. A label is an observed seat 0 to 15.
  Step 0 (classification). For each label `i = 0` to 15 set `friend(i) = 0` and `hostile(i) = 0`. Set
  `friend(selfId) = 1`. Then, for each `i <> selfId` with `visible(i)`:
  Step 0a (friendly disguise). If `df_until(i) > worldTick` of `COM.disguise_friend`: when
  `df_until(i) <> kf_src(i)`, set `kf_x(i) = df_x(i)`, `kf_y(i) = df_y(i)` and `kf_src(i) = df_until(i)`. Then,
  when `(playerX(i) - kf_x(i)) * (playerX(i) - kf_x(i)) + (playerY(i) - kf_y(i)) * (playerY(i) - kf_y(i)) <=
  friend_radius * friend_radius`, with friend_radius of `COM.disguise_friend`, set `kf_x(i) = playerX(i)`,
  `kf_y(i) = playerY(i)` and `friend(i) = 1`, and skip to the next i. A friend record always wins over Step 0c.
  Step 0b (enemy parity). If `i MOD 2 <> selfTeam`, set `hostile(i) = 1`.
  Step 0c (teammate parity). Else set `friend(i) = 1`. Then set `hostile(i) = 1` and `friend(i) = 0` when
  either corroboration holds for body i.
  Own evidence: `cm__heard_t(i) > 0`, `worldTick + 1 - cm__heard_t(i) <= x_window`, and
  `(playerX(i) - cm__heard_x(i)) * (playerX(i) - cm__heard_x(i)) + (playerY(i) - cm__heard_y(i)) *
  (playerY(i) - cm__heard_y(i)) > x_distance * x_distance`. The runtime keeps cm__heard_t, cm__heard_x and
  cm__heard_y for each claimed sender seat. cm__heard_t holds the receipt tick plus 1, or 0.
  Two witnesses: `xa_amb(i) = 0`, `xa_t1(i) > worldTick` and `xa_t2(i) > worldTick` of
  `COM.disguise_alert`, `xa_s1(i) <> xa_s2(i)`, and body i is within x_radius of both `(xa_x1(i), xa_y1(i))`
  and `(xa_x2(i), xa_y2(i))`. x_window, x_distance and x_radius are Params of `COM.disguise_alert`.
  A failed message check alone never sets hostile.
  Also set `xe_label = -1`, `xe_x = 0` and `xe_y = 0` at the start of Step 0. Set them to i and the body
  position for the first i (lowest) whose own evidence holds and where `i <> (selfId + 2) MOD 16`.
  Step 1. Set `best = -1`, `best_cost = 2147483647`, `focus_best = -1`, `focus_cost = 2147483647`,
  `thief = -1`, `foes_near = 0`, `friends_near = 1` (we count ourselves), `foe_sum_x = 0`,
  `foe_sum_y = 0` and `foes_seen = 0`.
  Step 2. For `i = 0` to 15, use seat i only when `i <> selfId AND visible(i)`. Set
  `dx = playerX(i) - selfX`, `dy = playerY(i) - selfY` and `d2 = dx * dx + dy * dy`.
  For a hostile body (`hostile(i) = 1`): set `cost = d2 - (3 - playerHp(i)) * hp_weight`. If
  `playerCarrying(i)`, subtract `carrier_bonus` from cost and set `thief = i`. Then, if
  `cost < best_cost AND d2 <= range_sq`, set `best = i` and `best_cost = cost`. Then, if
  `fc_until > worldTick` of `COM.focus_call`, `i = fc_label`, `d2 <= range_sq`, the body is within
  focus_radius of `(fc_x, fc_y)` (focus_radius of `COM.focus_call`), and `cost < focus_cost`, set
  `focus_best = i` and `focus_cost = cost`. Then add 1 to `foes_seen`, add `playerX(i)` to `foe_sum_x` and
  `playerY(i)` to `foe_sum_y`. If `d2 < near_foe_sq`, add 1 to `foes_near`.
  For a friend body (`friend(i) = 1`): if `d2 < near_friend_sq`, add 1 to `friends_near`.
  After the loop, set `focus_used = 0`. If `focus_best >= 0`, set `best = focus_best`,
  `best_cost = focus_cost` and `focus_used = 1`.
  Step 3. Set `best_vx = 0` and `best_vy = 0`. If `best >= 0 AND seen_tick(best) = worldTick - 1`,
  set `best_vx = playerX(best) - old_x(best)` and `best_vy = playerY(best) - old_y(best)`.
  The memory arrays start at 0, so on tick 1 this test compares with 0. Keep that.
  Step 4. For every seat `i = 0` to 15, our own seat included, with `visible(i)`: set
  `old_x(i) = playerX(i)`, `old_y(i) = playerY(i)` and `seen_tick(i) = worldTick`.
  Also set `foe_cx = foe_sum_x / foes_seen` and `foe_cy = foe_sum_y / foes_seen` when
  `foes_seen > 0`. Else set both to 0.
  Step 5 (engagers). Set `best_engagers = 0`. If `best >= 0`, count each friend body `i <> selfId` with
  `visible(i)` and `(playerX(i) - playerX(best)) * (playerX(i) - playerX(best)) + (playerY(i) - playerY(best)) *
  (playerY(i) - playerY(best)) <= engage_range_sq`.
  Step 6 (heard enemy). Set `heard_target = -1`, `heard_x = 0`, `heard_y = 0` and `heard_age = 0`. For each
  label `j = 0` to 15 with `ht_until(j) > worldTick` of `COM.enemy_sighting`, `NOT visible(j)` and `df_until(j) <= worldTick` of `COM.disguise_friend`: choose the j with
  the largest `ht_t(j)`. Strict greater-than keeps the lowest label on a tie. Set `heard_target = j`,
  `heard_x = ht_x(j)` and `heard_y = ht_y(j)`.
- Sources: `selfId`, `selfTeam`, `selfX`, `selfY`, `worldTick`, `visible`, `playerX`, `playerY`,
  `playerHp`, `playerCarrying`, runtime `cm__heard_t`, `cm__heard_x`, `cm__heard_y`, and messages from
  `COM.enemy_sighting`, `COM.focus_call`, `COM.disguise_alert`, `COM.disguise_friend`
- Uses: `COM.enemy_sighting`, `COM.focus_call`, `COM.disguise_alert`, `COM.disguise_friend`
- Memory: old_x, old_y and seen_tick (16 cells each, private arrays) persist for the whole match.
  Step 3 reads them before Step 4 overwrites them. That is the same as base.bas, which aims
  first and updates old positions after aiming. kf_x, kf_y and kf_src (16 cells each, private arrays) track
  each friendly disguise record from its last matching body.
- Outputs:
  - best -- the hostile body to fight, or -1
  - best_cost -- the cost of best (smaller is more urgent)
  - best_vx -- best's x movement since the previous tick, or 0
  - best_vy -- best's y movement since the previous tick, or 0
  - thief -- the highest-index visible hostile body that carries a heart, or -1
  - foes_near -- visible hostile bodies closer than 26 m
  - friends_near -- 1 plus visible friend bodies closer than 12 m
  - foes_seen -- visible hostile bodies at any range
  - foe_cx -- mean x of visible hostile bodies, or 0
  - foe_cy -- mean y of visible hostile bodies, or 0
  - friend[16] -- 1 for our own seat and each visible body we must not shoot, else 0
  - hostile[16] -- 1 for each visible body we may fight, else 0
  - focus_used -- 1 when best came from the focus call
  - best_engagers -- visible friend bodies other than us within engage range of best
  - heard_target -- the freshest heard enemy label that is not visible, or -1
  - heard_x -- its reported x, or 0
  - heard_y -- its reported y, or 0
  - xe_label -- the lowest label with own conflicting-position evidence, or -1
  - xe_x -- the body x for xe_label, or 0
  - xe_y -- the body y for xe_label, or 0
- Log: best, foes_near, friends_near, focus_used every 24 ticks
- Params:
  - hp_weight = 160000 -- base.bas value, cost bonus per missing hit point
  - carrier_bonus = 2500000 -- base.bas value, cost bonus of a heart carrier
  - range_sq = 27562500 square cm -- base.bas value, 52.5 m target range
  - near_foe_sq = 6760000 square cm -- base.bas value, 26 m
  - near_friend_sq = 1440000 square cm -- base.bas value, 12 m
  - engage_range_sq = 4549689 square cm -- hand-set, rules 49 gun reach 2133 cm squared (mechanics.nim ShortGunRange)
- Checks:
  - Believed: best, the near counts and focus_used are logged. Reads: `K.contacts`.best, `K.contacts`.foes_near, `K.contacts`.friends_near, `K.contacts`.focus_used
  - True: the logged best is a visible hostile body in the replay within range. Reads: `K.contacts`.best, replay
  - Acted properly: with no friendly disguise, alert or focus message in effect, best equals the baseline choice from observed parity. Reads: `K.contacts`.best, `COM.disguise_friend`.packet, `COM.disguise_alert`.packet, `COM.focus_call`.packet, replay
  - Result: a body marked hostile because of corroboration is an enemy in the replay. Reads: `COM.disguise_alert`.packet, replay
- Status: specified (2026-10-05)
- Rationale: With no messages, hostile equals enemy parity and friend equals teammate parity, so the
  baseline choice, counts and costs are unchanged. The focus rule keeps the old cost inside the focus
  group and the old choice outside it. Heard tracks never become fire targets. They only drive the
  motor's look when it has no target.

### K.pickups
- Summary: Supplies seen in the last ten seconds, the nearest one we want now, our own supply takes, and
  supplies that became ready.
- Spec: In `__update`, on every tick, do Steps 0 to 3 in order.
  Step 0 (own take, before refresh). Count candidate stations j (`j < pickupCount() AND j < 64`) that meet every condition below.
  `mem_tick(j) = worldTick` (previously visible and ready). Require `NOT pickupVisible(j)`.
  `(mem_x(j) - prev_x) * (mem_x(j) - prev_x) + (mem_y(j) - prev_y) * (mem_y(j) - prev_y) <= take_radius_sq`. Require the state change for kind `mem_kind(j)`. The changes by kind are: 0 grenade:
  `hasGrenade = 1 AND prev_grenade = 0`. 1 spray: `hasSpray = 1 AND prev_spray = 0`. 2 medkit:
  `selfHp >= prev_hp + 2`. 3 armor: `armorHp = 3 AND prev_armor < 3`. 4 uniform:
  `hasUniform() = 1 AND prev_uniform = 0`. 5 mister: `mistingTicks() > 0 AND prev_mist = 0`. 6 sniper:
  `hasSniper() = 1 AND prev_sniper = 0`. 7 radar: `radarTicks() > prev_radar`.
  When exactly one candidate j exists, set `taken_id = j`, `taken_x = mem_x(j)`, `taken_y = mem_y(j)`,
  `taken_kind = mem_kind(j)`, `taken_tick = worldTick`, and `taken_ready_in = grenade_delay` for kind 0, else
  `supply_delay`. Set `own_ready(j) = worldTick + taken_ready_in`. With zero or several candidates, do not
  change the taken outputs.
  Step 0b (ready transition). For the lowest j with `pickupVisible(j)` and either `mem_tick(j) = 0` or
  `own_ready(j) > worldTick` or `rk_until(j) > worldTick` of `COM.pickup_taken`: set `ready_id = j`,
  `ready_kind = pickupKind(j)`, `ready_x = pickupX(j)`, `ready_y = pickupY(j)` and `ready_tick = worldTick`.
  Step 0c (state memory). Set `prev_x = selfX`, `prev_y = selfY`, `prev_grenade = hasGrenade`,
  `prev_spray = hasSpray`, `prev_hp = selfHp`, `prev_armor = armorHp`, `prev_uniform = hasUniform()`,
  `prev_mist = mistingTicks()`, `prev_sniper = hasSniper()` and `prev_radar = radarTicks()`.
  Step 1 (refresh). For `i = 0` while `i < pickupCount() AND i < 64`: if `pickupVisible(i)`, set
  `mem_x(i) = pickupX(i)`, `mem_y(i) = pickupY(i)`, `mem_kind(i) = pickupKind(i)` and
  `mem_tick(i) = worldTick + 1`. Else, if `rr_t(i) > mem_tick(i)` of `COM.pickup_ready`, set
  `mem_x(i) = rr_x(i)`, `mem_y(i) = rr_y(i)`, `mem_kind(i) = rr_kind(i)`, `mem_tick(i) = rr_t(i)`
  and `own_ready(i) = 0`. A newer ready report supersedes an older local empty memory.
  Step 2 (carrier). Set `carrier = 0`. For `i = 0` to 15, set `carrier = 1` when
  `i <> selfId AND visible(i) AND i MOD 2 <> selfTeam AND playerCarrying(i)`.
  Step 3 (choice). Set `nearest = -1`, `nearest_x = 0`, `nearest_y = 0`. Do the rest of this step
  only when `NOT carrying AND carrier = 0`. Set `nearest_cost = reach_sq`. For `j = 0` while
  `j < pickupCount() AND j < 64`, use j only when
  `mem_tick(j) > 0 AND worldTick - mem_tick(j) < memory_ticks`, and skip j when `NOT pickupVisible(j)` and
  either `own_ready(j) > worldTick` or both `rk_until(j) > worldTick` and `rk_t(j) >= rr_t(j)`.
  A ready report newer than an empty report supersedes it. An equal-tick empty report wins.
  Set `kind = mem_kind(j)` and
  `wanted = (kind = 0 AND NOT hasGrenade) OR (kind = 2 AND selfHp < 3) OR (kind = 3 AND armorHp < 3 AND selfHp = 3)`.
  If wanted: set `dx = mem_x(j) - selfX`, `dy = mem_y(j) - selfY`, and
  `cost = dx * dx + dy * dy`. Then, if
  `kind = 2 AND selfHp = 1`, set `cost = cost / 4`. Then, if
  `cost < arrive_sq AND NOT pickupVisible(j)`, set `mem_tick(j) = 0` and do not use j. Else, if
  `cost < nearest_cost`, set `nearest = j` and `nearest_cost = cost`.
  After the loop, if `nearest >= 0`, set `nearest_x = mem_x(nearest)` and
  `nearest_y = mem_y(nearest)`.
  In `__init`, set `taken_id = -1` and `ready_id = -1`, and set every prev_ value from the current host values.
- Sources: `pickupCount`, `pickupVisible`, `pickupX`, `pickupY`, `pickupKind`, `visible`,
  `playerCarrying`, `carrying`, `hasGrenade`, `hasSpray`, `hasUniform`, `hasSniper`, `mistingTicks`,
  `radarTicks`, `selfHp`, `armorHp`, `selfX`, `selfY`, `worldTick`, and messages from `COM.pickup_taken` and
  `COM.pickup_ready`
- Uses: `COM.pickup_taken`, `COM.pickup_ready`
- Memory: mem_x, mem_y, mem_kind, mem_tick and own_ready (64 cells each, private arrays) persist for the whole
  match and start at 0. prev_x, prev_y and the eight prev_ state values hold the previous living tick.
  The taken and ready outputs keep their last event until a new one.
- Outputs:
  - nearest -- the remembered supply to fetch, or -1
  - nearest_x -- its remembered x, or 0
  - nearest_y -- its remembered y, or 0
  - taken_id -- the station of our last unambiguous take, or -1
  - taken_x -- its x
  - taken_y -- its y
  - taken_kind -- its kind, 0 to 7
  - taken_ready_in -- ticks from the take until it is ready again
  - taken_tick -- the tick of that take
  - ready_id -- the station of our last seen ready transition, or -1
  - ready_kind -- its kind, 0 to 7
  - ready_x -- its x
  - ready_y -- its y
  - ready_tick -- the tick of that transition
- Log: nearest, taken_id every 24 ticks
- Params:
  - memory_ticks = 240 ticks -- base.bas value, ten seconds
  - reach_sq = 4840000 square cm -- base.bas value, 22 m
  - arrive_sq = 10000 square cm -- base.bas value, 1 m. A remembered supply this close and not visible is gone.
  - take_radius_sq = 14400 square cm -- hand-set, engine take radius 120 cm (mechanics.nim pickupEquipment)
  - grenade_delay = 120 ticks -- hand-set, engine grenade station delay (mechanics.nim pickupEquipment)
  - supply_delay = 720 ticks -- hand-set, engine delay of every other station (mechanics.nim pickupEquipment)
- Checks:
  - Believed: the chosen supply and our last take are logged. Reads: `K.pickups`.nearest, `K.pickups`.taken_id
  - True: a supply of the remembered kind was at the remembered point in the replay. Reads: `K.pickups`.nearest, replay
  - True: each logged take matches a replay pickup event by this seat at that station. Reads: `K.pickups`.taken_id, replay
- Status: specified (2026-10-05)
- Rationale: Step 2 repeats the carrier test of `K.contacts` because a Knowledge component cannot
  use another Knowledge component. The result is the same as base.bas's `thief < 0` guard. With no messages
  and no own take, the choice is the baseline choice. The medkit rule asks for a rise of at least 2 because a
  windex-mister heals 1 point at a time. A take with more than one candidate is not claimed.

### K.comms_danger
- Summary: Live grenade zones and the most recent under-fire area that teammates reported.
- Spec: In `__update`, on every tick, do these steps. Step 1: for `i = 0` to 3, copy `gz_x(i)`, `gz_y(i)` and
  `gz_until(i)` of `COM.grenade_warning` into `grenade_x(i)`, `grenade_y(i)` and `grenade_until(i)`. Set
  `grenade_until(i) = 0` when `gz_until(i) <= worldTick`. Set `zone_count` to the number of i with
  `grenade_until(i) > worldTick`. Step 2: if `du_until > worldTick` of `COM.under_fire`, set
  `danger_x = du_x`, `danger_y = du_y`, `danger_dir = du_dir` and `danger_until = du_until`. Else set all four to 0.
- Sources: messages from `COM.grenade_warning` and `COM.under_fire`
- Uses: `COM.grenade_warning`, `COM.under_fire`
- Outputs:
  - grenade_x[4] -- x of each grenade zone
  - grenade_y[4] -- y of each grenade zone
  - grenade_until[4] -- last tick plus 1 of each zone, 0 when expired
  - zone_count -- live grenade zones
  - danger_x -- x of the latest under-fire report, or 0
  - danger_y -- y of the latest under-fire report, or 0
  - danger_dir -- its gunfire octant 0 to 7, 8 unknown, or 0
  - danger_until -- its last tick plus 1, 0 when expired
- Log: zone_count, danger_until every 24 ticks
- Params:
  - clear_radius = 450 cm [250, 700, 50] -- hand-set, comms.md grenade_clear_radius default
- Checks:
  - Believed: live zones and the danger expiry are logged. Reads: `K.comms_danger`.zone_count, `K.comms_danger`.danger_until
  - True: a live zone covers the replay landing point of the reported grenade. Reads: `COM.grenade_warning`.packet, replay
- Status: specified (2026-10-05)
- Rationale: `SK.motor` reads these outputs and clear_radius. A Skill cannot read a COM component.

### K.glory_hearts
- Summary: Glory hearts we see or that teammates reported. Memory only. No rule uses it.
- Spec: In `__update`, on every tick: set `count = 0`, `nearest_x = 0`, `nearest_y = 0`, `nearest_left = 0` and
  `nearest_d2 = 2147483647`. For `i = 0` while `i < gloryHeartCount() AND i < 8`, use i when
  `gloryHeartTicksLeft(i) >= 0` (it is in view). For `j = 0` to 7, use j when `gl_until(j) > worldTick` of
  `COM.glory_seen` and no visible glory heart is within h_match of `(gl_x(j), gl_y(j))`, with h_match of
  `COM.glory_seen`. For each used heart, add 1 to count. If its squared distance to us is less than nearest_d2,
  set nearest_d2, nearest_x and nearest_y, and set nearest_left to its ticks left
  (`gloryHeartTicksLeft(i)`, or `gl_until(j) - worldTick`).
- Sources: `gloryHeartCount`, `gloryHeartX`, `gloryHeartY`, `gloryHeartTicksLeft`, `selfX`, `selfY`, `worldTick`,
  and messages from `COM.glory_seen`
- Uses: `COM.glory_seen`
- Outputs:
  - count -- glory hearts known now
  - nearest_x -- x of the nearest known glory heart, or 0
  - nearest_y -- y of the nearest known glory heart, or 0
  - nearest_left -- its ticks left, or 0
- Log: count, nearest_left every 24 ticks
- Checks:
  - Believed: the known count is logged. Reads: `K.glory_hearts`.count
  - True: each known heart exists in the replay at that point and tick. Reads: `K.glory_hearts`.count, replay
- Status: specified (2026-10-05)

## Situations

### S.losing_fight
- Summary: We see more near enemies than near friends, so we refuse the fight.
- Spec: Set `on = 1` when
  `foes_near - friends_near >= 1 AND NOT carrying AND heart_count > 0`, using the outputs of
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
  `(best < 0 OR best_cost > fight_clear_sq OR selfHp = 1)` with best and best_cost of
  `K.contacts`. Else set `on = 0`.
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
  with lead, hold fire on friends, and charge grenades to the range. Step out of reported grenade zones.
- Spec: The code is authored in `skill.bas`. A capability calls `sk_motor__act(gx, gy, hold)`
  exactly once on every tick, with its goal point and holding flag. `act` sets `quiet = 0` and
  `charging = 0`. It runs these parts in order: the gun wait countdown, the look sweep, footwork,
  grenade-zone avoidance, then the dry route with one `walkTo`. The gun and grenade follow. The look sweep runs
  only when there is no target. With no target, it faces non-team speech first, then the heard enemy of
  `K.contacts`, then the latest under-fire report of `K.comms_danger`. Avoidance moves the walk target outside
  `clear_radius` plus 50 of a live zone when we or the walk target are inside it. Line-clear and grenade safety
  treat every body with `friend(i) = 1` of `K.contacts` as a friend. `charge_started = 1` on the first tick of a
  new charge (charging was 0 on the previous act). While the grenade routine orders a charge, `charging = 1`, `charge_x` and `charge_y` are the charge target, and `release_in` is the charge still needed,
  clamped to 0..24. `sk_motor__sneak(on)` sets `quiet = on` and calls the host command `sneak(on)`.
  `sk_motor__isqrt(n)` puts the integer square root of n into the output root.
- Uses: `P.walkTo`, `P.lookAt`, `P.shootAt`, `P.chargeGrenade`, `K.contacts`, `K.self_motion`, `K.comms_danger`
- Code: skills/motor/skill.bas
- Outputs:
  - root -- the result of the last sk_motor__isqrt call
  - threw -- 1 on a tick where the grenade charge reached the need, else 0
  - charging -- 1 on a tick where the grenade routine orders a charge, else 0
  - charge_started -- 1 on the first tick of a new charge, else 0
  - charge_x -- x of the charge target
  - charge_y -- y of the charge target
  - release_in -- charge ticks still needed, 0 to 24
  - quiet -- 1 when the capability called sk_motor__sneak(1) this tick, else 0
- Params:
  - wet_cost = 6 -- base.bas value, a wet metre costs this many dry metres in the dry route
  - lead_ticks = 6 ticks -- base.bas value, the gun windup
  - drift_ticks = 5 ticks -- base.bas value, our own drift to cancel
  - gun_wait_light = 25 ticks -- base.bas value, gun cooldown
  - gun_wait_heavy = 73 ticks -- base.bas value, cooldown with armor, in a trench, or carrying
  - spray_range_sq = 640000 -- base.bas value, the spray gun shoots only below this target cost
- Checks:
  - Acted properly: a shot is ordered only when the gun wait is zero, the friend line is clear, and the spray range condition holds. Reads: replay
  - Acted properly: while inside a live reported zone, the walk target is outside the zone. Reads: `K.comms_danger`.zone_count, replay
  - Result: hit rate per shot at range. Reads: replay
- Status: specified (2026-10-05)

## Capabilities

### C.take_heart
- Summary: Stand in the capture ring of the squad target (squad seats 0 and 1).
- Spec: `__start` does nothing. `__tick` does these steps in order. Step 1: set
  `goal_x = controlX(objective)` and `goal_y = controlY(objective)`, with objective of
  `K.squad_target`. Step 2: set `dx = goal_x - selfX` and `dy = goal_y - selfY`. Set `hold = 1` when
  `dx * dx + dy * dy < hold_sq`. Else set `hold = 0`. Step 3: call `sk_motor__act(goal_x, goal_y, hold)` of
  `SK.motor`. Step 4 (quiet approach): call `sk_motor__sneak(1)` of `SK.motor` when all of these hold. best
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
  `goal_x = hx + (ax * 3 - ay * 2 * side) * post_radius / root` and
  `goal_y = hy + (ay * 3 + ax * 2 * side) * post_radius / root`. Step 3: set `dx = goal_x - selfX` and `dy = goal_y - selfY`. Set `hold = 1` when
  `dx * dx + dy * dy < hold_sq`. Else set `hold = 0`. Step 4: call
  `sk_motor__act(goal_x, goal_y, hold)`. Step 5 (quiet approach): call `sk_motor__sneak(1)` of
  `SK.motor` when all of these hold. best of `K.contacts` is less than 0. `soundCount() > 0`. `(controlX(objective) - selfX) * (controlX(objective) - selfX) +
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
  `SK.motor`. Step 3 (quiet approach): call `sk_motor__sneak(1)` of `SK.motor` when all of these
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
  `K.pickups`. Step 2 (quiet approach): call `sk_motor__sneak(1)` of `SK.motor` when all of these
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
  `away_score = -2147483647`. For `j = 0` while `j < heartCount() AND j < 64`, set `ex = (controlX(j) - cx) / 16`,
  `ey = (controlY(j) - cy) / 16`, `mx = (controlX(j) - selfX) / 16`,
  `my = (controlY(j) - selfY) / 16`, and `score = ex * ex + ey * ey - (mx * mx + my * my) / 2`.
  If `score > away_score`, set `away = j` and `away_score = score`. Step 2: if `away >= 0`, the
  goal is `(controlX(away), controlY(away))`. Else the goal is our own position. Step 3: call
  `sk_motor__act(goal_x, goal_y, 0)` of `SK.motor`. Step 4 (quiet approach): call `sk_motor__sneak(1)` of
  `SK.motor` when all of these hold. best of `K.contacts` is less than 0. `soundCount() > 0`.
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
- Spec: The squad seat is `((selfId / 2) MOD 8) MOD 4`. Ring seats have squad seat 0 or 1.
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

### COM.disguise_friend
- Summary: Tell teammates that our disguised body is a friend, and keep their friend records.
- Spec: In `__send`: when `uniform_since > 0` of `K.self_motion`, a teammate-parity seat `i <> selfId` is
  visible within `d_range_sq`, and either `ds_t < uniform_since` or `worldTick +
  1 - ds_t >= d_refresh`, send D. Call `cm__send(8, label, 0, 0, quiet)` with `label = selfId + 1 - 2 * (selfId MOD
  2)` and quiet of `SK.motor`. When `cm__sent = 1`, set `ds_t = worldTick + 1`. ds_t starts at 0. In `__recv`:
  set `L = cm__fa`. If `L = selfId`, set `L = (L + 2) MOD 16` (the observer alias). Set `df_x(L) = cm__rx_x`,
  `df_y(L) = cm__rx_y` and `df_until(L) = worldTick + friend_ttl`. `__recv` runs once for each decoded message
  of this wire type, after generated code fills `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`,
  `cm__speaker` (the claimed sender seat) and `cm__rx_x`, `cm__rx_y` (the sender's exact position at send time).
  The message was sent on tick `worldTick - 1`. `__send` proposes at most one message with `cm__send(type,
  fieldsA, fieldsB, cell, quiet)`. It runs only when no message of higher priority was sent this tick. It
  changes its own memory only after `cm__sent = 1`. A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1`
  and `h = mapMaxY() - mapMinY() + 1`. Encode: `gx = (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) *
  256 / h`, each clamped to 0..255, and `cell = gx + 256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell /
  256`, `x = mapMinX() + (gx * w + w / 2) / 256` and `y = mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `K.self_motion`, `SK.motor`
- Content: the apparent label of our disguised body
- Encoding: comms-v1 8 -- D, strategy/comms.md
- Send when: we wear a uniform and a teammate is in view within 12.8 m
- On receipt: the receiver keeps a friend record for that label at the sender position
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - df_x[16] -- sender x of the friend record of each label
  - df_y[16] -- sender y of the friend record of each label
  - df_until[16] -- last tick plus 1 of the friend record of each label, or 0
- Log: packet
- Params:
  - d_refresh = 24 ticks [12, 72, 12] -- hand-set, comms.md default
  - friend_radius = 250 cm [100, 500, 50] -- hand-set, comms.md default
  - friend_ttl = 48 ticks [24, 120, 12] -- hand-set, comms.md default
  - d_range_sq = 1638400 square cm -- hand-set, engine hearing radius 1280 cm squared (seat_view.nim deliverSpeech)
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.disguise_friend`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.disguise_friend`.packet, PWC.s, PWC.w, replay
  - Result: a friend record never protects a body that is an enemy in the replay. Reads: `COM.disguise_friend`.packet, replay
- Status: specified (2026-10-05)
- Rationale: The alias step is vacuous for teammate receivers, because the label has enemy parity. It keeps the rule the same as for alerts. The aim-at-us trigger of comms.md is not available, because there is no aim host call.

### COM.disguise_alert
- Summary: Report uncertain disguise evidence and keep distinct witness reports.
- Spec: In `__send`: choose the evidence. Strong evidence: `xe_label >= 0` of `K.contacts`, with `L =
  xe_label`, the point `(xe_x, xe_y)` and `age = worldTick + 1 - cm__heard_t(L)`. Use weak evidence only without strong evidence. Choose the lowest label L with `cm__suspect_t(L) > 0`, `worldTick + 1 -
  cm__suspect_t(L) <= x_window`, `L <> selfId` and `L <> (selfId + 2) MOD 16` (not our own alias). Use the
  point `(cm__suspect_x(L), cm__suspect_y(L))` and `age = worldTick + 1 - cm__suspect_t(L)`. The runtime keeps
  cm__suspect_t, cm__suspect_x and cm__suspect_y for each teammate label whose speech failed the message
  check. cm__suspect_t holds the receipt tick plus 1, or 0. Send only when `xs_t(L) = 0 OR worldTick + 1 -
  xs_t(L) >= x_refresh`. Clamp age to 0..255 and call `cm__send(7, L, age, cell, quiet)` with the cell of the
  point and quiet of `SK.motor`. When `cm__sent = 1`, set `xs_t(L) = worldTick + 1`. xs_t is a private array
  of 16 cells and starts at 0. In `__recv`: set `L = cm__fa`, `amb = 0` and `until = worldTick - 1 - cm__fb +
  disguise_ttl` (the evidence expiry, from its age). Ignore the message when `until <= worldTick`. If `L =
  selfId`, set `L = (L + 2) MOD 16` and `amb = 1`. Decode the cell to `(px, py)`. When amb is 1, set
  `xa_amb(L) = 1`. If `xa_t1(L) <= worldTick`, or `xa_s1(L) = cm__speaker AND until > xa_t1(L)`, set `xa_s1(L)
  = cm__speaker`, `xa_x1(L) = px`, `xa_y1(L) = py` and `xa_t1(L) = until`. Else, when `xa_s1(L) <>
  cm__speaker`, `(px - xa_x1(L)) * (px - xa_x1(L)) + (py - xa_y1(L)) * (py - xa_y1(L)) <= x_radius *
  x_radius`, and `xa_t2(L) <= worldTick OR (xa_s2(L) = cm__speaker AND until > xa_t2(L))`, set `xa_s2(L) =
  cm__speaker`, `xa_x2(L) = px`, `xa_y2(L) = py` and `xa_t2(L) = until`. A report never refreshes a claim with
  a later expiry, and one sender never fills both witnesses. Set `xa_amb(L) = 0` again when both witnesses
  expire. `__recv` runs once for each decoded message of this wire type, after generated code fills `packet`.
  It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker` (the claimed sender seat) and `cm__rx_x`, `cm__rx_y`
  (the sender's exact position at send time). The message was sent on tick `worldTick - 1`. `__send` proposes
  at most one message with `cm__send(type, fieldsA, fieldsB, cell, quiet)`. It runs only when no message of
  higher priority was sent this tick. It changes its own memory only after `cm__sent = 1`. A cell packs a
  point. Set `w = mapMaxX() - mapMinX() + 1` and `h = mapMaxY() - mapMinY() + 1`. Encode: `gx = (x -
  mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`, each clamped to 0..255, and `cell = gx + 256 *
  gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x = mapMinX() + (gx * w + w / 2) / 256` and `y =
  mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `K.contacts`, `SK.motor`
- Content: the fake label, the evidence age, and the position of the fake body
- Encoding: comms-v1 7 -- X, strategy/comms.md
- Send when: our own position evidence shows a fake body, or, weaker, a teammate label failed the message check
- On receipt: the receiver keeps up to two distinct witness reports per label, which `K.contacts` uses
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - xa_s1[16] -- claimed sender seat of the first witness of each label
  - xa_x1[16] -- first witness x
  - xa_y1[16] -- first witness y
  - xa_t1[16] -- last tick plus 1 of the first witness, or 0
  - xa_s2[16] -- claimed sender seat of the second distinct witness
  - xa_x2[16] -- second witness x
  - xa_y2[16] -- second witness y
  - xa_t2[16] -- last tick plus 1 of the second witness, or 0
  - xa_amb[16] -- 1 when the label was remapped because this receiver is the impersonated seat
- Log: packet
- Params:
  - x_window = 24 ticks [12, 72, 12] -- hand-set, comms.md default
  - x_distance = 1000 cm [700, 1500, 100] -- hand-set, new. Above 24 ticks of free walking (672 cm) plus margin. The comms.md 600 is below that walk.
  - x_radius = 300 cm [100, 600, 50] -- hand-set, comms.md default
  - disguise_ttl = 72 ticks [24, 240, 24] -- hand-set, comms.md default
  - x_refresh = 24 ticks [12, 72, 12] -- hand-set, new
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.disguise_alert`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.disguise_alert`.packet, PWC.s, PWC.w, replay
  - True: the reported body was a disguised enemy in the replay. Reads: `COM.disguise_alert`.packet, replay
- Status: specified (2026-10-05)
- Rationale: James chose corroboration (2026-10-05). A failed check can raise an alert but never fire. The message check is not authentication, so one report never makes a target. The receiver needs two distinct claimed senders, or its own evidence in `K.contacts`. A friend record always wins. An alias label is ambiguous, so it never makes a report-based target.

### COM.focus_call
- Summary: Call our fight target so that teammates who see it prefer it.
- Spec: In `__send`: when `best >= 0` of `K.contacts`, `(playerHp(best) < full_hp OR best_engagers >= 2)`, and
  `fs_label <> best OR worldTick - fs_t >= focus_refresh`, call `cm__send(1, best + 16 * hp, 0, cell, quiet)`
  with `hp = playerHp(best)` clamped to 0..15, the cell of `(playerX(best), playerY(best))` and quiet of
  `SK.motor`. When `cm__sent = 1`, set `fs_label = best` and `fs_t = worldTick`. In `__init`, set `fs_label =
  -1` and `fc_label = -1`. In `__recv`: set `fc_label = cm__fa MOD 16`, decode the cell to `(fc_x, fc_y)`, and
  set `fc_until = worldTick + focus_ttl`. The latest call wins. `__recv` runs once for each decoded message of
  this wire type, after generated code fills `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker`
  (the claimed sender seat) and `cm__rx_x`, `cm__rx_y` (the sender's exact position at send time). The message
  was sent on tick `worldTick - 1`. `__send` proposes at most one message with `cm__send(type, fieldsA,
  fieldsB, cell, quiet)`. It runs only when no message of higher priority was sent this tick. It changes its
  own memory only after `cm__sent = 1`. A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1` and `h =
  mapMaxY() - mapMinY() + 1`. Encode: `gx = (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`,
  each clamped to 0..255, and `cell = gx + 256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x =
  mapMinX() + (gx * w + w / 2) / 256` and `y = mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `K.contacts`, `SK.motor`
- Content: the target label, its hit points, and its position
- Encoding: comms-v1 1 -- F, strategy/comms.md
- Send when: our target is wounded, or two teammates can engage it
- On receipt: the receiver prefers that target when it sees it within range
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - fc_label -- label of the latest focus call, or -1
  - fc_x -- its target x
  - fc_y -- its target y
  - fc_until -- its last tick plus 1, or 0
- Log: packet
- Params:
  - focus_refresh = 24 ticks [12, 48, 12] -- hand-set, comms.md default
  - focus_ttl = 36 ticks [12, 72, 12] -- hand-set, comms.md default
  - focus_radius = 400 cm [100, 800, 50] -- hand-set, new
  - full_hp = 10 -- hand-set, rules 49 base hit points (sim.nim maxHp). Wounded means below this.
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.focus_call`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.focus_call`.packet, PWC.s, PWC.w, replay
  - Result: called targets die sooner than uncalled targets. Reads: `COM.focus_call`.packet, replay
- Status: specified (2026-10-05)

### COM.glory_seen
- Summary: Report glory hearts we see, and keep teammates' reports.
- Spec: In `__send`, consider hearts i with `i < gloryHeartCount() AND i < 8` and `gloryHeartTicksLeft(i) >= 0`.
  Skip a heart when any slot j has `gl_until(j) > worldTick` and `worldTick - gl_t(j) < h_refresh`, within h_match of `(gl_x(j), gl_y(j))`.
  Also skip it when any own slot k has `hs_t(k) > 0` and `worldTick + 1 - hs_t(k) < h_refresh`, within h_match of `(hs_x(k), hs_y(k))`.
  Choose the lowest remaining i. Call `cm__send(4, left, 0, cell, quiet)` with `left = gloryHeartTicksLeft(i)` clamped to 0..720.
  Use the cell of `(gloryHeartX(i), gloryHeartY(i))` and quiet of `SK.motor`.
  When `cm__sent = 1`, use the own slot k within h_match of the heart, else the slot with the smallest hs_t.
  Set `hs_x(k)`, `hs_y(k)` to the heart and `hs_t(k) = worldTick + 1`. hs_x, hs_y and
  hs_t are private arrays of 8 cells. Heart indices can renumber, so memory is matched by position. In
  `__recv`: decode the cell to `(px, py)`. Use the slot j that is within h_match of `(px, py)`, else the slot
  with the smallest gl_until. Set `gl_x(j) = px`, `gl_y(j) = py`, `gl_t(j) = worldTick` and `gl_until(j) =
  worldTick - 1 + cm__fa`. `__recv` runs once for each decoded message of this wire type, after generated code
  fills `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker` (the claimed sender seat) and
  `cm__rx_x`, `cm__rx_y` (the sender's exact position at send time). The message was sent on tick `worldTick -
  1`. `__send` proposes at most one message with `cm__send(type, fieldsA, fieldsB, cell, quiet)`. It runs only
  when no message of higher priority was sent this tick. It changes its own memory only after `cm__sent = 1`.
  A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1` and `h = mapMaxY() - mapMinY() + 1`. Encode: `gx =
  (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`, each clamped to 0..255, and `cell = gx +
  256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x = mapMinX() + (gx * w + w / 2) / 256` and `y =
  mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `SK.motor`
- Content: a glory heart position and its ticks left
- Encoding: comms-v1 4 -- H, strategy/comms.md
- Send when: we see a glory heart that no teammate reported recently
- On receipt: the receiver keeps the heart until it expires
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - gl_x[8] -- reported glory heart x
  - gl_y[8] -- reported glory heart y
  - gl_until[8] -- reported expiry tick, or 0
  - gl_t[8] -- tick of the latest report of each slot
- Log: packet
- Params:
  - h_refresh = 120 ticks [48, 240, 24] -- hand-set, comms.md default
  - h_match = 200 cm -- hand-set, new. Two reports this close are one heart.
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.glory_seen`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.glory_seen`.packet, PWC.s, PWC.w, replay
- Status: specified (2026-10-05)

### COM.enemy_sighting
- Summary: Report a visible enemy to teammates, and keep heard enemy tracks.
- Spec: In `__send`: consider each label `i <> selfId` with `visible(i)` and `hostile(i) = 1` of `K.contacts`,
  where `es_t(i) = 0 OR worldTick + 1 - es_t(i) >= e_refresh` or the body moved more than e_move from
  `(es_x(i), es_y(i))`. Choose the one nearest to any teammate seat s with `cm__heard_t(s) > 0` and `worldTick
  + 1 - cm__heard_t(s) <= heard_ttl` (position `cm__heard_x(s)`, `cm__heard_y(s)`). If there is no such
  teammate, choose the one nearest to us. Strict less-than keeps the lowest label. Call `cm__send(0, i + 16 *
  (hp + 16 * 8), 0, cell, quiet)` with `hp = playerHp(i)` clamped to 0..15, heading 8 (unknown), the cell of
  `(playerX(i), playerY(i))` and quiet of `SK.motor`. When `cm__sent = 1`, set `es_t(i) = worldTick + 1`,
  `es_x(i) = playerX(i)` and `es_y(i) = playerY(i)`. In `__recv`: set `L = cm__fa MOD 16` and `seen =
  worldTick - 1 - cm__fb` (the sighting tick, fieldsB is its age). When `ht_until(L) = 0 OR seen > ht_t(L)`,
  decode the cell to `(ht_x(L), ht_y(L))`, set `ht_t(L) = seen` and `ht_until(L) = seen + heard_ttl`. An older
  or equal sighting never refreshes a track. `__recv` runs once for each decoded message of this wire type,
  after generated code fills `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker` (the claimed sender
  seat) and `cm__rx_x`, `cm__rx_y` (the sender's exact position at send time). The message was sent on tick
  `worldTick - 1`. `__send` proposes at most one message with `cm__send(type, fieldsA, fieldsB, cell, quiet)`.
  It runs only when no message of higher priority was sent this tick. It changes its own memory only after
  `cm__sent = 1`. A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1` and `h = mapMaxY() - mapMinY() +
  1`. Encode: `gx = (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`, each clamped to 0..255,
  and `cell = gx + 256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x = mapMinX() + (gx * w + w /
  2) / 256` and `y = mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `K.contacts`, `SK.motor`
- Content: an enemy label, its hit points, and its position
- Encoding: comms-v1 0 -- E, strategy/comms.md
- Send when: we see an enemy that we did not report recently
- On receipt: the receiver keeps a heard track for that label
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - ht_x[16] -- heard x of each enemy label
  - ht_y[16] -- heard y of each enemy label
  - ht_t[16] -- tick of the latest report of each label
  - ht_until[16] -- last tick plus 1 of each track, or 0
- Log: packet
- Params:
  - e_refresh = 12 ticks [6, 48, 6] -- hand-set, comms.md default
  - e_move = 300 cm [100, 800, 50] -- hand-set, comms.md default
  - heard_ttl = 48 ticks [24, 120, 12] -- hand-set, new
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.enemy_sighting`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.enemy_sighting`.packet, PWC.s, PWC.w, replay
  - True: the reported label was a visible body at the reported cell and an enemy in the replay. A corroborated misclassification fails this by design. Reads: `COM.enemy_sighting`.packet, replay
- Status: specified (2026-10-05)
- Rationale: No receiver effect uses heading, so the sender sends 8 (unknown). Heard tracks never make a fire target.

### COM.grenade_warning
- Summary: Warn teammates where our grenade will land, and keep their warnings.
- Spec: In `__send`: when `charging = 1` of `SK.motor` and either `charge_started = 1` of `SK.motor`,
  `gs_until <= worldTick`, or `(charge_x - gs_x) * (charge_x - gs_x) + (charge_y - gs_y) * (charge_y - gs_y) >
  g_move * g_move`, call `cm__send(2, release_in, 0, cell, quiet)` with release_in, charge_x and charge_y from `SK.motor`. Use the cell of `(charge_x, charge_y)` and quiet of `SK.motor`. When `cm__sent = 1`, set `gs_x =
  charge_x`, `gs_y = charge_y` and `gs_until = worldTick + release_in + 24`. In `__recv`: decode the cell to
  `(px, py)`. Use the slot j (0 to 3) with the smallest gz_until. Set `gz_x(j) = px`, `gz_y(j) = py` and
  `gz_until(j) = worldTick - 1 + cm__fa + 24`. `__recv` runs once for each decoded message of this wire type,
  after generated code fills `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker` (the claimed sender
  seat) and `cm__rx_x`, `cm__rx_y` (the sender's exact position at send time). The message was sent on tick
  `worldTick - 1`. `__send` proposes at most one message with `cm__send(type, fieldsA, fieldsB, cell, quiet)`.
  It runs only when no message of higher priority was sent this tick. It changes its own memory only after
  `cm__sent = 1`. A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1` and `h = mapMaxY() - mapMinY() +
  1`. Encode: `gx = (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`, each clamped to 0..255,
  and `cell = gx + 256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x = mapMinX() + (gx * w + w /
  2) / 256` and `y = mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `SK.motor`
- Content: the grenade target and the ticks until release
- Encoding: comms-v1 2 -- G, strategy/comms.md
- Send when: we charge a grenade, and again if the target moved
- On receipt: the receiver keeps a zone until 24 ticks after release
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - gz_x[4] -- zone x
  - gz_y[4] -- zone y
  - gz_until[4] -- last tick plus 1 of each zone, or 0
- Log: packet
- Params:
  - g_move = 200 cm [100, 400, 50] -- hand-set, comms.md default
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.grenade_warning`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.grenade_warning`.packet, PWC.s, PWC.w, replay
  - True: a grenade from the sender lands within 150 cm of the reported cell. Reads: `COM.grenade_warning`.packet, replay
- Status: specified (2026-10-05)
- Rationale: This replaces the literal "Grenade out!" shout of the baseline (decided 2026-10-05).

### COM.under_fire
- Summary: Report that we lose hit points and see no enemy, and keep the latest such report.
- Spec: In `__send`: when `hp_drop = 1` of `K.self_motion` and `foes_seen = 0` of `K.contacts`: choose the gun
  sound i (`soundKind(i) = 1`) with the smallest `soundAge(i)`, for `i < soundCount() AND i < 12`. Set `dir =
  soundDirection(i)` and `dist = soundDistance(i)`, or `dir = 8` and `dist = 3` when there is none. Call
  `cm__send(3, hp + 16 * dir, dist, 0, quiet)` with `hp = selfHp` clamped to 0..15 and quiet of `SK.motor`. In
  `__recv`: set `du_x = cm__rx_x`, `du_y = cm__rx_y`, `du_dir = cm__fa / 16` and `du_until = worldTick +
  danger_ttl`. `__recv` runs once for each decoded message of this wire type, after generated code fills
  `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker` (the claimed sender seat) and `cm__rx_x`,
  `cm__rx_y` (the sender's exact position at send time). The message was sent on tick `worldTick - 1`.
  `__send` proposes at most one message with `cm__send(type, fieldsA, fieldsB, cell, quiet)`. It runs only
  when no message of higher priority was sent this tick. It changes its own memory only after `cm__sent = 1`.
  A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1` and `h = mapMaxY() - mapMinY() + 1`. Encode: `gx =
  (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`, each clamped to 0..255, and `cell = gx +
  256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x = mapMinX() + (gx * w + w / 2) / 256` and `y =
  mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `K.self_motion`, `K.contacts`, `SK.motor`
- Content: our hit points, the gunfire direction octant, and the distance class
- Encoding: comms-v1 3 -- U, strategy/comms.md
- Send when: we lost hit points and see no enemy
- On receipt: the receiver keeps the latest danger area at the sender position
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - du_x -- sender x of the latest report
  - du_y -- sender y of the latest report
  - du_dir -- gunfire octant of the latest report, 8 unknown
  - du_until -- its last tick plus 1, or 0
- Log: packet
- Params:
  - danger_ttl = 48 ticks [24, 120, 12] -- hand-set, comms.md default
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.under_fire`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.under_fire`.packet, PWC.s, PWC.w, replay
- Status: specified (2026-10-05)
- Rationale: The octant and distance class are the engine's sound fields (mechanics.nim soundDirection, emitSound). Gun shots are sound kind 1.

### COM.pickup_taken
- Summary: Report a supply we took, and keep teammates' reports of taken supplies.
- Spec: In `__send`: when `taken_id >= 0` of `K.pickups`, `taken_tick + 1 > ks_tick` and `worldTick -
  taken_tick <= event_window`, call `cm__send(5, taken_id, left, cell, quiet)` with `left = taken_ready_in -
  (worldTick - taken_tick)` clamped to 0..720, the cell of `(taken_x, taken_y)` and quiet of `SK.motor`. When
  `cm__sent = 1`, set `ks_tick = taken_tick + 1`. In `__recv`: when `cm__fa < 64`, set `rk_until(cm__fa) =
  worldTick - 1 + cm__fb` and `rk_t(cm__fa) = worldTick`. rk_t is the send tick plus 1,
  so it is comparable to rr_t of a ready report. `__recv` runs once for each decoded message of this wire type, after generated code
  fills `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker` (the claimed sender seat) and
  `cm__rx_x`, `cm__rx_y` (the sender's exact position at send time). The message was sent on tick `worldTick -
  1`. `__send` proposes at most one message with `cm__send(type, fieldsA, fieldsB, cell, quiet)`. It runs only
  when no message of higher priority was sent this tick. It changes its own memory only after `cm__sent = 1`.
  A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1` and `h = mapMaxY() - mapMinY() + 1`. Encode: `gx =
  (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`, each clamped to 0..255, and `cell = gx +
  256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x = mapMinX() + (gx * w + w / 2) / 256` and `y =
  mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `K.pickups`, `SK.motor`
- Content: the station, the ticks until it is ready, and its position
- Encoding: comms-v1 5 -- K, strategy/comms.md
- Send when: we took a supply in the last event_window ticks
- On receipt: the receiver does not walk to that station until it is ready
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - rk_until[64] -- the tick each station is ready again by report, or 0
  - rk_t[64] -- send tick plus 1 of the latest empty report, or 0
- Log: packet
- Params:
  - event_window = 24 ticks [6, 48, 6] -- hand-set, new. A take waits this long for the one shout.
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.pickup_taken`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.pickup_taken`.packet, PWC.s, PWC.w, replay
  - True: the reported station was taken by the sender within event_window ticks before the send in the replay. Reads: `COM.pickup_taken`.packet, replay
- Status: specified (2026-10-05)

### COM.pickup_ready
- Summary: Report a supply that became ready, and keep teammates' ready reports.
- Spec: In `__send`: when `ready_id >= 0` of `K.pickups`, `ready_tick + 1 > rs_tick` and `worldTick -
  ready_tick <= event_window`, and `pickupVisible(ready_id)` still holds, call `cm__send(6, ready_id + 256 * ready_kind, 0, cell, quiet)` with the cell
  of `(ready_x, ready_y)` and quiet of `SK.motor`. When `cm__sent = 1`, set `rs_tick = ready_tick + 1`. In
  `__recv`: set `j = cm__fa MOD 256`. When `j < 64`, set `rr_kind(j) = cm__fa / 256`, decode the cell to
  `(rr_x(j), rr_y(j))`, and set `rr_t(j) = worldTick`. `__recv` runs once for each decoded message of this
  wire type, after generated code fills `packet`. It reads `cm__fa`, `cm__fb`, `cm__cell`, `cm__speaker` (the
  claimed sender seat) and `cm__rx_x`, `cm__rx_y` (the sender's exact position at send time). The message was
  sent on tick `worldTick - 1`. `__send` proposes at most one message with `cm__send(type, fieldsA, fieldsB,
  cell, quiet)`. It runs only when no message of higher priority was sent this tick. It changes its own memory
  only after `cm__sent = 1`. A cell packs a point. Set `w = mapMaxX() - mapMinX() + 1` and `h = mapMaxY() -
  mapMinY() + 1`. Encode: `gx = (x - mapMinX()) * 256 / w` and `gy = (y - mapMinY()) * 256 / h`, each clamped
  to 0..255, and `cell = gx + 256 * gy`. Decode: `gx = cell MOD 256`, `gy = cell / 256`, `x = mapMinX() + (gx
  * w + w / 2) / 256` and `y = mapMinY() + (gy * h + h / 2) / 256`.
- Uses: `K.pickups`, `SK.motor`
- Content: the station, its kind, and its position
- Encoding: comms-v1 6 -- R, strategy/comms.md
- Send when: we see a station ready that our memory did not hold as ready
- On receipt: the receiver remembers the station as seen ready
- Directions: both
- Outputs:
  - packet[2] -- the decoded payload blocks A and B of the last message, filled by generated code
  - rr_x[64] -- reported x of each station
  - rr_y[64] -- reported y of each station
  - rr_kind[64] -- reported kind of each station
  - rr_t[64] -- tick of the latest ready report, or 0
- Log: packet
- Params:
  - event_window = 24 ticks [6, 48, 6] -- hand-set, new. A transition waits this long for the one shout.
- Checks:
  - Acted properly: each sent packet decodes and its fields match the sender's replay state at the send tick. Reads: `COM.pickup_ready`.packet, PWC.s, replay
  - Result: teammates alive within 12.8 m of the sender decode it on the next tick, within decode capacity. Reads: `COM.pickup_ready`.packet, PWC.s, PWC.w, replay
  - True: the reported station was ready at the send tick in the replay. Reads: `COM.pickup_ready`.packet, replay
- Status: specified (2026-10-05)

## Open questions

- A Knowledge component cannot use another Knowledge component, so `K.pickups` repeats a carrier
  test. A Skill cannot use another Skill, so the mechanics are one skill.
- The comms runtime gives K.contacts read access to cm__heard_t, cm__heard_x and cm__heard_y.
  The compiler must allow that read.
