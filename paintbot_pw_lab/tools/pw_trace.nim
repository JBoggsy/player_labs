## pw_trace: hash-checked Paintbot PW replay expander (lab tool T1).
##
##   pw_trace REPLAY OUT.jsonl [--state-every N] [--window A:B] [--vis-every M]
##
## Re-simulates a POLYWORLDREPLAY tape (raw or gzip) with the engine's own step and checks
## the recorded state hash after every tick. Writes schema-versioned JSONL: one `meta` row,
## `event` rows, `state` rows (every N ticks, default 6, plus every tick inside --window),
## optional `visibility` rows (every M ticks, M a multiple of N), and one `summary` row.
## `summary.verified` true is the only proof the file is complete and exact. Any hash
## mismatch, frames after the match ended, or a failed identity check writes a summary with
## verified=false and exits 1. Contract: docs/tools/pw_trace.md.
##
## Built by tools/build_tools.sh inside the release worktree (copied to
## examples/paintbot/lab_pw_trace.nim) with -d:pwTraining, which exposes the damage hooks.
## One process per replay: the engine keeps match state in module globals.
##
## Tick convention: every row's `t` is the world tick AFTER the step that produced it
## (frame index + 1), which is also the tick the tape stamps shouts with. State at t
## reflects every event at t. t = 0 is the initial world (initial spawns).
import std/[os, json, monotimes, times, strutils, math, tables, algorithm]
import zippy
import game, sim, neural_contract

when not defined(pwTraining):
  {.error: "pw_trace needs -d:pwTraining (damageObserver/damageWeapon)".}

const
  SchemaVersion = 1
  AimTolerance = 150  # units off the aim line for the inferred intended target of a shot
  PwRelease {.strdefine.} = "unknown"
  StateColumns = ["x", "z", "aim_x", "aim_z", "goal_x", "goal_z", "hp", "armor", "lives",
    "shield", "respawn", "cooldown", "disguised", "in_water", "trench", "grenade", "spray_can",
    "charge", "windup", "burst", "captures", "tags",
    "cmd_walk", "cmd_shoot", "cmd_direct", "cmd_sneak", "cmd_charge",
    "cmd_goal_x", "cmd_goal_z", "cmd_aim_x", "cmd_aim_z"]

type
  Options = object
    replay, output: string
    stateEvery, visEvery: int
    windowStart, windowEnd: int
  SeatCounters = object
    aliveTicks, waterTicks, trenchTicks, disguisedTicks: int
    heartReachTicks, contestedReachTicks: int
    ownTerritoryTicks, enemyTerritoryTicks, neutralTerritoryTicks: int
    decisionTicks, idleTicks, sneakTicks: int
    lastActiveCommandTick: int  # -1 when the seat never sent a non-empty command
    idleRunTicks: int           # alive ticks with empty commands since that tick

var
  rows: seq[JsonNode]        # events of the step being simulated
  postTick: int32            # the `t` of rows emitted during the current step
  preArmor: int32            # armor before the current damage() call (observeHit fires first)
  stepDamage: seq[JsonNode]  # damage events of the current step, for shot outcomes
  killEvents, enemyKillEvents: int

proc ev(kind: string, fields: JsonNode = newJObject()): JsonNode =
  fields["type"] = %"event"
  fields["t"] = %postTick
  fields["kind"] = %kind
  rows.add fields
  fields

proc xz(p: Point): JsonNode = %[p.x, p.z]

proc dist(a, b: Point): int = int(sqrt(float(distance2(a, b))))

proc weaponName(d: DamageWeapon): string =
  case d
  of dwGun: "gun"
  of dwGrenade: "grenade"
  of dwSpray: "spray"
  of dwNone: "none"

proc pickupName(k: PickupKind): string = ($k).replace("Pickup", "")

proc gloryKindName(k: GloryKind): string =
  case k
  of gloryQuietSupplies: "quiet_supplies"
  of gloryFriendlyFire: "friendly_fire"
  of gloryHeart: "glory_heart"
  of gloryBehindLives: "behind_lives"
  of gloryBehindCogs: "behind_cogs"

proc onDamage(w: World, victim, attacker: int, removed: int32, killed: bool) {.nimcall, gcsafe.} =
  {.cast(gcsafe).}:
    let weapon = weaponName(damageWeapon)
    let other = attacker >= 0 and attacker != victim
    let seat = if attacker >= 0: %attacker else: newJNull()  # null: the map (barrage)
    var row = %*{"seat": seat, "victim": victim, "weapon": weapon,
      "hp_removed": removed, "armor_absorbed": preArmor - w.equipment[victim].armor,
      "killed": killed, "friendly": other and team(attacker) == team(victim),
      "self": attacker == victim, "victim_pos": xz(w.cogs[victim].pos),
      "distance": newJNull(), "attacker_pos": newJNull()}
    if attacker >= 0:
      row["distance"] = %dist(w.cogs[attacker].pos, w.cogs[victim].pos)
      row["attacker_pos"] = xz(w.cogs[attacker].pos)
    stepDamage.add ev("damage", row)
    if killed:
      inc killEvents
      if other and team(attacker) != team(victim): inc enemyKillEvents
      discard ev("kill", %*{"seat": seat, "victim": victim, "weapon": weapon,
        "friendly": other and team(attacker) == team(victim), "self": attacker == victim,
        "victim_pos": xz(w.cogs[victim].pos), "distance": row["distance"]})

proc parseOptions(): Options =
  let args = commandLineParams()
  result = Options(stateEvery: 6, visEvery: 0, windowStart: -1, windowEnd: -1)
  var positional: seq[string]
  var i = 0
  while i < args.len:
    case args[i]
    of "--state-every": result.stateEvery = parseInt(args[i+1]); inc i
    of "--vis-every": result.visEvery = parseInt(args[i+1]); inc i
    of "--window":
      let parts = args[i+1].split(':')
      result.windowStart = parseInt(parts[0]); result.windowEnd = parseInt(parts[1]); inc i
    else:
      if args[i].startsWith("--"): quit("unknown option " & args[i], 2)
      positional.add args[i]
    inc i
  if positional.len != 2:
    quit("usage: pw_trace REPLAY OUT.jsonl [--state-every N] [--window A:B] [--vis-every M]", 2)
  if result.stateEvery < 1: quit("--state-every must be >= 1", 2)
  if result.visEvery < 0 or (result.visEvery > 0 and result.visEvery mod result.stateEvery != 0):
    quit("--vis-every must be a multiple of --state-every", 2)
  result.replay = positional[0]
  result.output = positional[1]

proc openTape(path: string): string =
  ## A gzip tape (the public replay_url) is inflated to a temporary file; raw tapes load as is.
  let bytes = readFile(path)
  if bytes.len >= 2 and bytes[0] == '\x1f' and bytes[1] == '\x8b':
    result = getTempDir() / ("pw_trace_" & $getCurrentProcessId() & ".replay")
    writeFile(result, uncompress(bytes, dfGzip))
  else:
    result = path
  if not readFile(result).startsWith("POLYWORLDREPLAY"):
    quit("not a POLYWORLDREPLAY tape: " & path, 2)

proc stateRow(w: World, cmds: seq[Command], haveCmds: bool): JsonNode =
  var seats = newJArray()
  for i in 0..<Seats:
    let c = w.cogs[i]; let e = w.equipment[i]
    var row = %[c.pos.x.int, c.pos.z.int, c.aim.x.int, c.aim.z.int, c.goal.x.int, c.goal.z.int,
      c.hp.int, e.armor.int, e.lives.int, c.shield.int, c.respawn.int, c.cooldown.int,
      int(w.uniforms[i]), int(inWater(c.pos)), w.trenchAt(c.pos), int(e.grenade), int(e.sprayCan),
      e.charge.int, e.windup.int, e.burst.int, c.captures.int, c.tags.int]
    if haveCmds:
      let m = cmds[i]
      for v in [int(m.walk), int(m.shoot), int(m.direct), int(m.sneak), int(m.chargeGrenade),
          m.goal.x.int, m.goal.z.int, m.aim.x.int, m.aim.z.int]:
        row.add %v
    else:
      for _ in 0..8: row.add newJNull()
    seats.add row
  var hearts = newJArray()
  for n, h in w.controlHearts:
    let cap = w.heartCaptures[n]
    hearts.add %[h.owner.int, cap.team.int, cap.ticks.int, int(cap.contested)]
  %*{"type": "state", "t": w.tick, "seats": seats, "hearts": hearts,
    "meter_ticks": [w.scoreTicks[0], w.scoreTicks[1]], "glory": [w.glory[0], w.glory[1]],
    "team_lives": [w.teamLives(0), w.teamLives(1)],
    "cogs_out": [w.teamCogsOut(0), w.teamCogsOut(1)], "winner": w.winner}

proc visibilityRow(w: World): JsonNode =
  var sees = newJArray()
  for i in 0..<Seats:
    var seen = newJArray()
    if w.cogs[i].hp > 0:
      for j in 0..<Seats:
        if i != j and w.visible(i, j): seen.add %j
    sees.add seen
  %*{"type": "visibility", "t": w.tick, "sees": sees}

proc newGlory(before, after: seq[GloryEvent]): seq[GloryEvent] =
  ## Awards added by this step. gloryEvents is a rolling 4 s window, and heart awards are
  ## stamped with the pre-increment tick while the others use the post-increment tick, so
  ## filtering by tick double-counts. Old events only ever leave the window from the front,
  ## so the multiset difference after - before is exactly this step's awards.
  var seen = initCountTable[string]()
  for e in before: seen.inc($e)
  for e in after:
    let key = $e
    if seen[key] > 0: seen.inc(key, -1)
    else: result.add e

proc newGloryPickups(before, after: seq[GloryPickup]): seq[GloryPickup] =
  var seen = initCountTable[string]()
  for e in before: seen.inc($e)
  for e in after:
    let key = $e
    if seen[key] > 0: seen.inc(key, -1)
    else: result.add e

proc aimTarget(w: World, cogs: seq[Cog], seat: int, aim: Point): tuple[seat, along, across: int] =
  ## Inferred intended target: the nearest living enemy within AimTolerance of the aimed
  ## line (the pre-jitter gunAim from the shooter's position), out to GunRange. -1 if none.
  result = (-1, 0, 0)
  let len = sqrt(float(aim.x)*float(aim.x)+float(aim.z)*float(aim.z))
  if len == 0: return
  for j in 0..<cogs.len:
    if team(j) == team(seat) or cogs[j].hp <= 0: continue
    let dx = float(cogs[j].pos.x-cogs[seat].pos.x); let dz = float(cogs[j].pos.z-cogs[seat].pos.z)
    let along = (dx*float(aim.x)+dz*float(aim.z))/len
    let across = abs(dx*float(aim.z)-dz*float(aim.x))/len
    if along <= 0 or along > GunRange.float or across > AimTolerance.float: continue
    if result.seat < 0 or along < result.along.float: result = (j, int(along), int(across))

proc reachesHeart(w: World, p: Point, h: ControlHeart): bool =
  ## Capture reach: the engine's updateTerritory test (ControlHeartRadius and a traversable line).
  distance2(p, h.pos) <= ControlHeartRadius.int64*ControlHeartRadius and w.traversable(p, h.pos)

proc main() =
  let opt = parseOptions()
  let t0 = getMonoTime()
  let tapePath = openTape(opt.replay)
  let r = loadRecording(tapePath)   # binds rules, mode, map, vision, glory and seat count
  if tapePath != opt.replay: removeFile(tapePath)
  var w = newWorld(r.seed, r.endTick)
  let n = Seats
  let rules = replayRulesVersion
  var output = open(opt.output, fmWrite)
  proc emit(row: JsonNode) = output.writeLine($row)

  var pickups = newJArray()
  for k, p in w.pickups: pickups.add %*{"idx": k, "kind": pickupName(p.kind), "pos": xz(p.pos)}
  var hearts = newJArray()
  for k, h in w.controlHearts: hearts.add %*{"idx": k, "pos": xz(h.pos), "owner": h.owner}
  emit(%*{"type": "meta", "schema_version": SchemaVersion, "tool": "pw_trace",
    "engine_release": PwRelease, "nim_version": NimVersion,
    "replay": opt.replay, "rules": rules, "mode": (if ffa(): "ffa_kin" else: "teams"),
    "map": r.map, "vision": r.vision, "glory_config": %r.glory, "seats": n, "seed": r.seed,
    "end_tick": r.endTick, "frames": r.frames.len, "names": r.names, "tick_rate": TickRate,
    "meter_target_ticks": w.heartMeterTarget(), "hearts": hearts, "pickups": pickups,
    "trenches": %w.trenches, "cover_count": w.cover.len,
    "homes": [xz(home(0)), xz(home(1))],
    "options": {"state_every": opt.stateEvery, "vis_every": opt.visEvery,
      "window": (if opt.windowStart >= 0: %[opt.windowStart, opt.windowEnd] else: newJNull())},
    "state_columns": StateColumns,
    "heart_columns": ["owner", "capture_team", "capture_ticks", "contested"]})

  # Shouts are recorded with the tick of the step that follows them (game.nim advance).
  var shoutsAt = initTable[int, seq[Communication]]()
  for c in r.communications: shoutsAt.mgetOrPut(c.tick, @[]).add c

  # CombatTelemetry is one SeatStats per seat the build supports (MaxSeats = 256 at 0.3.79; 16 in
  # older builds): a match wider than the build's telemetry skips it (seat_stats and kill check null).
  var stats: CombatTelemetry
  let useTelemetry = n <= stats.len
  for i in 0..<stats.len: stats[i].firstFriendlyFireTick = -1
  var counters = newSeq[SeatCounters](n)
  for c in counters.mitems: c.lastActiveCommandTick = -1
  var gloryAwards, gloryCountdown: array[2, int32]
  let gloryInitial = w.glory  # every match starts with glory (600 at rules 47)
  var gloryRunning = w.glory
  var gloryMismatch = ""
  var tagCount = 0
  var pendingFires: seq[int]   # seats whose gun ray was released this step
  var failure = ""
  var mismatchTick = -1

  observeShot = proc(tick: int32, slot: int) = pendingFires.add slot
  observeHit = proc(tick: int32, victim, attacker: int, pos: Point) =
    preArmor = w.equipment[victim].armor
  observeTag = proc(tick: int32, victim, attacker: int, pos: Point) = inc tagCount
  damageObserver = onDamage

  # t = 0: initial spawns and state.
  postTick = 0
  for i in 0..<n:
    if w.cogs[i].hp > 0:
      discard ev("spawn", %*{"seat": i, "pos": xz(w.cogs[i].pos), "lives": w.equipment[i].lives,
        "initial": true})
  for c in shoutsAt.getOrDefault(0): discard ev("shout", %*{"seat": c.slot, "text": c.text,
    "bytes": c.text.len, "heard_by": newJArray()})
  for row in rows: emit(row)
  rows.setLen(0)
  emit(stateRow(w, @[], false))
  if opt.visEvery > 0: emit(visibilityRow(w))

  for f, fr in r.frames:
    if w.winner != -1:
      failure = "replay has frames after the match ended at tick " & $w.tick
      break
    let preTick = w.tick
    postTick = preTick + 1
    let prevCogs = w.cogs
    let prevEq = w.equipment
    let prevUni = w.uniforms
    let prevCaps = w.heartCaptures
    let prevGloryEvents = w.gloryEvents
    let prevGloryPickups = w.gloryPickups
    var prevOwners, prevReady: seq[int32]
    for h in w.controlHearts: prevOwners.add h.owner
    for p in w.pickups: prevReady.add p.readyAt
    var prevWet, prevTrench: seq[bool]
    for i in 0..<n:
      prevWet.add inWater(w.cogs[i].pos)
      prevTrench.add w.trenchAt(w.cogs[i].pos) >= 0
    let prevGlory = w.glory
    rows.setLen(0)
    stepDamage.setLen(0)
    pendingFires.setLen(0)

    # Shouts delivered before this step: heard by living seats within Width/5 of a living
    # sender, on the pre-step world (bots.nim deliverSpeech).
    for c in shoutsAt.getOrDefault(postTick):
      var heard = newJArray()
      if w.cogs[c.slot].hp > 0:
        for j in 0..<n:
          if j != c.slot and w.cogs[j].hp > 0 and
              distance2(w.cogs[c.slot].pos, w.cogs[j].pos) <= (Width div 5).int64*(Width div 5):
            heard.add %j
      discard ev("shout", %*{"seat": c.slot, "text": c.text, "bytes": c.text.len, "heard_by": heard})

    # Command-based counters use the pre-step life: dead seats do not run their policy.
    for i in 0..<n:
      if prevCogs[i].hp <= 0: continue
      let m = fr.commands[i]
      inc counters[i].decisionTicks
      if m.sneak: inc counters[i].sneakTicks
      if m == Command():
        inc counters[i].idleTicks
        inc counters[i].idleRunTicks
      else:
        counters[i].lastActiveCommandTick = postTick
        counters[i].idleRunTicks = 0

    if useTelemetry: combatTelemetry = addr stats
    w.step(fr.commands, rules)
    combatTelemetry = nil
    if w.stateHash() != fr.hash:
      mismatchTick = w.tick
      failure = "hash mismatch at tick " & $w.tick
      break

    # Gun rays: observeShot seats, matched to this step's new Paintball (life 6 at rules >= 9).
    for seat in pendingFires:
      var endPoint = prevCogs[seat].pos
      for b in w.balls:
        if b.owner == seat and b.life == (if rules >= 9: 6 else: 2): endPoint = b.pos
      let origin = prevCogs[seat].pos
      var victims = newJArray()
      for d in stepDamage:
        if d["seat"].kind == JInt and d["seat"].getInt == seat and d["weapon"].getStr == "gun":
          victims.add d["victim"]
      var row = %*{"seat": seat, "origin": xz(origin), "end": xz(endPoint),
        "length": dist(origin, endPoint), "gun_aim": xz(w.equipment[seat].gunAim),
        "hit": victims.len > 0, "victim": (if victims.len > 0: victims[0] else: newJNull()),
        "inferred_shielded": newJArray(), "inferred_dead": newJArray(),
        "inferred_trench_dodge": newJArray()}
      if victims.len == 0:
        # A miss may be a ray that reached a spawn-shielded or already-dead cog (damage()
        # returns before any hook) or a 70% trench dodge. Not exact: flagged, never counted.
        for j in 0..<n:
          if j == seat: continue
          if distance2(endPoint, prevCogs[j].pos) <= (Radius+20).int64*(Radius+20) or
              distance2(endPoint, w.cogs[j].pos) <= (Radius+20).int64*(Radius+20):
            if prevCogs[j].shield > 1 and prevCogs[j].hp > 0: row["inferred_shielded"].add %j
            elif prevCogs[j].hp > 0 and w.cogs[j].hp <= 0: row["inferred_dead"].add %j
          if prevCogs[j].hp > 0 and w.trenchAt(prevCogs[j].pos) >= 0 and
              w.trenchAt(prevCogs[j].pos) != w.trenchAt(origin):
            # Distance from the cog to the ray segment.
            let ax = float(endPoint.x-origin.x); let az = float(endPoint.z-origin.z)
            let px = float(prevCogs[j].pos.x-origin.x); let pz = float(prevCogs[j].pos.z-origin.z)
            let len2 = ax*ax+az*az
            let s = if len2 > 0: clamp((px*ax+pz*az)/len2, 0.0, 1.0) else: 0.0
            let dx = px-s*ax; let dz = pz-s*az
            if dx*dx+dz*dz <= float(Radius*Radius): row["inferred_trench_dodge"].add %j
      let target = aimTarget(w, prevCogs, seat, w.equipment[seat].gunAim)
      row["aim_target"] = if target.seat >= 0: %target.seat else: newJNull()
      row["aim_target_distance"] = if target.seat >= 0: %target.along else: newJNull()
      row["aim_target_across"] = if target.seat >= 0: %target.across else: newJNull()
      discard ev("fire", row)

    for i in 0..<n:
      let c = w.cogs[i]; let p = prevCogs[i]
      let e = w.equipment[i]; let pe = prevEq[i]
      if c.hp > 0 and p.hp <= 0:
        var nearHeart = newJNull()
        for k, h in w.controlHearts:
          if h.owner == team(i).int32 and distance2(c.pos, h.pos) <= 400'i64*400: nearHeart = %k
        discard ev("spawn", %*{"seat": i, "pos": xz(c.pos), "lives": e.lives, "initial": false,
          "near_owned_heart": nearHeart})
      if e.windup == GunWindupTicks and pe.windup != GunWindupTicks:
        discard ev("windup", %*{"seat": i, "aim": xz(c.aim), "gun_aim": xz(e.gunAim)})
      if e.burst > pe.burst:
        discard ev("spray", %*{"seat": i, "pos": xz(c.pos), "spray_aim": xz(e.sprayAim)})
      if e.charge > 0 and pe.charge == 0:
        discard ev("grenade_charge", %*{"seat": i})
      if w.uniforms[i] != prevUni[i]:
        if w.uniforms[i]: discard ev("disguise_on", %*{"seat": i})
        else: discard ev("disguise_off", %*{"seat": i,
          "cause": (if c.hp <= 0 and p.hp > 0: "death" else: "attack")})
      if c.hp > 0 and p.hp > 0:
        let wet = inWater(c.pos); let tr = w.trenchAt(c.pos) >= 0
        if wet != prevWet[i]: discard ev(if wet: "enter_water" else: "leave_water", %*{"seat": i})
        if tr != prevTrench[i]: discard ev(if tr: "enter_trench" else: "leave_trench", %*{"seat": i})

    for g in w.grenades:
      if g.releasedAt == preTick:
        discard ev("grenade_throw", %*{"seat": g.owner, "from": xz(g.start), "to": xz(g.target),
          "lands_at": g.landsAt + 1})
    for b in w.blasts:
      if b.tick == preTick:
        var victims = newJArray()
        for d in stepDamage:
          if d["weapon"].getStr == "grenade" and (if d["seat"].kind == JInt: d["seat"].getInt else: -1) == b.owner:
            victims.add d["victim"]
        discard ev("grenade_blast", %*{"seat": b.owner, "pos": xz(b.pos), "trench": b.trench,
          "victims": victims})

    # Pickups: a pickup's readyAt jump names the pickup; the taker is the seat within 120 units
    # whose state changed the matching way (pickupEquipment), first in this tick's seat order.
    var taken = newSeq[bool](n)
    var order = w.seatOrder()  # post-step tick: flip it back to the pre-step order
    if rules >= 35 and preTick mod 2 != w.tick mod 2:
      for i in countup(0, n-2, 2): swap(order[i], order[i+1])
    for k, pk in w.pickups:
      if pk.readyAt == prevReady[k]: continue
      var candidates: seq[int]
      for i in order:
        if taken[i] or w.cogs[i].hp <= 0 or distance2(w.cogs[i].pos, pk.pos) > 120*120: continue
        let ok = case pk.kind
          of grenadePickup: w.equipment[i].grenade and not prevEq[i].grenade
          of sprayPickup: w.equipment[i].sprayCan and not prevEq[i].sprayCan
          of medkitPickup: prevCogs[i].hp > 0 and w.cogs[i].hp > prevCogs[i].hp
          of uniformPickup: w.uniforms[i] and not prevUni[i]
          of armorPickup: w.equipment[i].armor == 3 and prevEq[i].armor < 3 and prevCogs[i].hp > 0
        if ok: candidates.add i
      var seat = newJNull()
      if candidates.len > 0:
        seat = %candidates[0]
        taken[candidates[0]] = true
      discard ev("pickup", %*{"seat": seat, "idx": k, "pickup_kind": pickupName(pk.kind),
        "pos": xz(pk.pos), "ambiguous": candidates.len > 1})

    # Captures (teams, rules >= 24): heartCaptures and owner diffs; credited seat = the cog
    # whose captures counter rose.
    for k, h in w.controlHearts:
      let cap = w.heartCaptures[k]; let pc = prevCaps[k]
      if h.owner != prevOwners[k]:
        var credited = newJNull()
        for i in 0..<n:
          if w.cogs[i].captures > prevCogs[i].captures and team(i).int32 == h.owner: credited = %i
        discard ev("capture_complete", %*{"heart": k, "team": h.owner, "previous_owner": prevOwners[k],
          "seat": credited})
      elif cap.team >= 0 and pc.team != cap.team:
        discard ev("capture_start", %*{"heart": k, "team": cap.team, "replaced_team": pc.team})
      elif cap.team < 0 and pc.team >= 0:
        discard ev("capture_reset", %*{"heart": k, "team": pc.team, "lost_ticks": pc.ticks})
      if cap.contested != pc.contested:
        discard ev(if cap.contested: "contest_start" else: "contest_end", %*{"heart": k,
          "capture_team": (if cap.team >= 0: %cap.team else: newJNull()), "capture_ticks": cap.ticks})

    # Glory: new awards by kind (deduped), glory-heart takers, and the running identity check.
    var earlyAwards: array[2, int32]
    for e in newGlory(prevGloryEvents, w.gloryEvents):
      discard ev("glory", %*{"team": e.team, "glory_kind": gloryKindName(e.kind), "amount": e.amount,
        "engine_tick": e.tick})
      gloryAwards[e.team] += e.amount
      gloryRunning[e.team] += e.amount
      if e.tick == preTick: earlyAwards[e.team] += e.amount
    for g in newGloryPickups(prevGloryPickups, w.gloryPickups):
      discard ev("glory_heart_taken", %*{"seat": g.seat, "amount": g.amount, "pos": xz(g.pos)})
    if rules >= 37 and not ffa():
      for side in 0..1:
        # updateGlory counts down after the tick advances, after heart awards, before the rest.
        if w.tick mod TickRate == 0 and prevGlory[side] + earlyAwards[side] > 0:
          dec gloryRunning[side]; inc gloryCountdown[side]
        let expected = if w.winner == -1 or w.winner == side.int32: gloryRunning[side] else: 0
        if expected != w.glory[side] and gloryMismatch.len == 0:
          gloryMismatch = "team " & $side & " glory " & $w.glory[side] & " != initial + awards - countdown " &
            $expected & " at tick " & $w.tick

    # Exact per-tick positional counters (post-step life).
    for i in 0..<n:
      let c = w.cogs[i]
      if c.hp <= 0: continue
      inc counters[i].aliveTicks
      if inWater(c.pos): inc counters[i].waterTicks
      if w.trenchAt(c.pos) >= 0: inc counters[i].trenchTicks
      if w.uniforms[i]: inc counters[i].disguisedTicks
      var reach, contested = false
      for k, h in w.controlHearts:
        if w.reachesHeart(c.pos, h):
          reach = true
          if w.heartCaptures[k].contested: contested = true
      if reach: inc counters[i].heartReachTicks
      if contested: inc counters[i].contestedReachTicks
      let owner = w.territoryOwner(c.pos)
      if owner < 0: inc counters[i].neutralTerritoryTicks
      elif owner == team(i).int32: inc counters[i].ownTerritoryTicks
      else: inc counters[i].enemyTerritoryTicks

    for row in rows: emit(row)
    let inWindow = opt.windowStart >= 0 and w.tick >= opt.windowStart and w.tick <= opt.windowEnd
    if w.tick mod opt.stateEvery == 0 or inWindow or w.winner != -1 or f == r.frames.high:
      emit(stateRow(w, fr.commands, true))
    if opt.visEvery > 0 and w.tick mod opt.visEvery == 0: emit(visibilityRow(w))

  # Identity checks.
  var checks = newJObject()
  if failure.len == 0 and w.tick != r.frames.len:
    failure = "simulated " & $w.tick & " ticks of " & $r.frames.len & " frames"
  if failure.len == 0 and w.winner == -1 and not ffa():
    failure = "tape ended before the match did (tick " & $w.tick & ")"
  checks["glory"] = if rules >= 37 and not ffa():
      %*{"ok": gloryMismatch.len == 0, "detail": gloryMismatch, "initial": gloryInitial, "awards": gloryAwards,
        "countdown": gloryCountdown, "unsettled": gloryRunning, "final": w.glory}
    else: newJNull()
  if failure.len == 0 and gloryMismatch.len > 0: failure = "glory identity failed: " & gloryMismatch
  var seatStats = newJNull()
  if useTelemetry:
    var statKills, statDeaths = 0
    seatStats = newJArray()
    for i in 0..<n:
      seatStats.add %stats[i]
      statKills += stats[i].kills
      statDeaths += stats[i].deaths
    # SeatStats.kills counts enemy kills only; deaths count every killing damage event.
    let ok = enemyKillEvents == statKills and killEvents == statDeaths
    checks["kills"] = %*{"ok": ok, "enemy_kill_events": enemyKillEvents, "seat_stats_kills": statKills,
      "kill_events": killEvents, "seat_stats_deaths": statDeaths, "tags": tagCount}
    if failure.len == 0 and not ok: failure = "kill identity failed"
  else:
    checks["kills"] = newJNull()

  var perSeat = newJArray()
  for i in 0..<n:
    let c = counters[i]
    perSeat.add %*{"seat": i, "team": team(i), "alive_ticks": c.aliveTicks,
      "water_ticks": c.waterTicks, "trench_ticks": c.trenchTicks,
      "disguised_ticks": c.disguisedTicks, "heart_reach_ticks": c.heartReachTicks,
      "contested_reach_ticks": c.contestedReachTicks,
      "own_territory_ticks": c.ownTerritoryTicks, "enemy_territory_ticks": c.enemyTerritoryTicks,
      "neutral_territory_ticks": c.neutralTerritoryTicks, "decision_ticks": c.decisionTicks,
      "idle_ticks": c.idleTicks, "sneak_ticks": c.sneakTicks,
      "last_active_command_tick": c.lastActiveCommandTick,
      "final_idle_run_ticks": c.idleRunTicks,
      "captures": w.cogs[i].captures, "tags": w.cogs[i].tags, "lives_left": w.equipment[i].lives}
  var owned = [0, 0]
  for h in w.controlHearts:
    if h.owner >= 0: inc owned[h.owner]
  emit(%*{"type": "summary", "schema_version": SchemaVersion, "verified": failure.len == 0,
    "failure": (if failure.len > 0: %failure else: newJNull()), "hash_mismatch_tick": mismatchTick,
    "final_hash": w.stateHash(), "ticks": w.tick, "frames": r.frames.len, "winner": w.winner,
    "glory": [w.glory[0], w.glory[1]], "meter_ticks": [w.scoreTicks[0], w.scoreTicks[1]],
    "hearts_owned": owned, "team_lives": [w.teamLives(0), w.teamLives(1)],
    "cogs_out": [w.teamCogsOut(0), w.teamCogsOut(1)], "checks": checks, "seats": perSeat,
    "seat_stats": seatStats, "elapsed_ms": (getMonoTime()-t0).inMilliseconds})
  output.close()
  if failure.len > 0:
    stderr.writeLine("pw_trace FAILED: ", failure)
    quit(1)
  echo "verified ticks=", w.tick, " hash=", w.stateHash(), " ms=", (getMonoTime()-t0).inMilliseconds

main()
