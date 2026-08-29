## Stateful stencil decision core.
##
## This module is intentionally transport-free. The port is landing by behavior
## slice; the current command floor is the Python policy's safe pre-init action.

import std/[options, tables]
import action, belief_state, belief_update, chat, config, protocols, perception,
  roles, strategy, types, worldmap

type StencilPolicy* = ref object
  slot*: int
  tick*: int
  belief*: Belief
  actionState*: ActionState
  teamsKnown*: bool
  rolesAssigned*: bool
  lastIntent*: Intent

proc newStencilPolicy*(slot: int): StencilPolicy =
  StencilPolicy(slot: slot, belief: newBelief(slot))

proc decide*(policy: StencilPolicy, client: ProtocolClient): Command =
  inc policy.tick
  let percept = perceive(client, policy.belief.team, policy.belief.colors,
    policy.belief.worldmap.isNil)
  if not policy.teamsKnown and percept.gameTeams.isSome:
    let teams = percept.gameTeams.get
    policy.belief.colors.setLen(teams)
    for index in 0 ..< teams:
      policy.belief.colors[index] = Team(index)
    if percept.selfColor.isNone:
      policy.belief.team = teamForSlot(policy.slot, teams)
    policy.belief.seat = min(policy.slot div teams, 7)
    policy.belief.seatsPerTeam = if teams == 2:
      (if policy.belief.seat == 0: 1 else: 8)
    else:
      (if policy.belief.seat < 4: 4 else: 8)
    policy.teamsKnown = true
  if percept.walkability.len > 0 and percept.gameTeams.isSome and
      percept.endzones.len >= policy.belief.colors.len:
    let signature = (percept.walkabilityWidth, percept.walkabilityHeight,
      percept.gameTeams.get)
    if policy.belief.worldmap.isNil or policy.belief.worldmap.signature != signature:
      policy.belief.worldmap = newWorldMap(
        percept.walkability, percept.walkabilityWidth, percept.walkabilityHeight,
        percept.gameTeams.get, percept.endzones, policy.belief.team)
      policy.rolesAssigned = false
      discard policy.belief.worldmap.routeDistance(
        policy.belief.worldmap.center,
        policy.belief.worldmap.capturePoint(policy.belief.team))
  let previousSeatsPerTeam = policy.belief.seatsPerTeam
  updateBeliefCore(policy.belief, percept, policy.actionState, policy.tick)
  if policy.belief.seatsPerTeam != previousSeatsPerTeam:
    policy.rolesAssigned = false
  if not policy.rolesAssigned and not policy.belief.worldmap.isNil:
    let seats = policy.belief.seatsPerTeam
    policy.belief.role = roleForSeat(policy.belief.seat, seats)
    policy.belief.holdPoint = none(Point)
    policy.belief.defensivePost = none(Point)
    policy.belief.defensivePostDuck = none(Point)
    policy.belief.defensivePostSightlineAim = none(Point)
    policy.belief.defensivePostOpponent = none(Team)
    policy.belief.defensivePostScore = 0.0
    policy.belief.defensivePostHeartDistance = 0
    policy.belief.defensivePostForward = false
    if policy.belief.role == Defender:
      let assignment = if DefensivePosts:
        defensivePostForSeat(policy.belief.worldmap, policy.belief.team,
          policy.belief.seat, seats, policy.belief.freshEnemyPositions)
      else:
        none(tuple[post: PostCandidate, opponent: Team])
      if assignment.isSome:
        let selected = assignment.get
        policy.belief.holdPoint = some(selected.post.pos)
        policy.belief.defensivePost = some(selected.post.pos)
        policy.belief.defensivePostDuck = some(selected.post.duck)
        if selected.post.rayEnds.len > 0:
          policy.belief.defensivePostSightlineAim = some(
            selected.post.rayEnds[selected.post.rayEnds.len div 2])
        policy.belief.defensivePostOpponent = some(selected.opponent)
        policy.belief.defensivePostScore = selected.post.score
        let
          heart = policy.belief.worldmap.pedestal(policy.belief.team)
          enemyHome = policy.belief.worldmap.homeCenter(selected.opponent)
        policy.belief.defensivePostHeartDistance = pyRound(
          policy.belief.worldmap.routeDistance(selected.post.pos, heart))
        # goal=enemyHome reads the init-minted home field; goal=post.pos
        # would mint a full-grid Dijkstra per newly-chosen post (see
        # squads.advancePoint note).
        policy.belief.defensivePostForward =
          policy.belief.worldmap.routeDistance(selected.post.pos, enemyHome) <
          policy.belief.worldmap.routeDistance(heart, enemyHome)
      else:
        policy.belief.holdPoint = some(holdPointForSeat(
          policy.belief.worldmap, policy.belief.team, policy.belief.seat, seats))
        if DefensivePosts:
          inc policy.belief.defensivePostFallbacks
    policy.rolesAssigned = true
  var objective: Objective
  if policy.belief.alive:
    objective = policy.belief.decideObjective()
  else:
    objective = Objective(intent: makeIntent(Hold, none(Point), "not_alive"))
    objective.intent.idleAimCenterBrads = policy.belief.idleAimAxis()
  policy.lastIntent = objective.intent
  result = resolveAction(objective.intent, policy.belief, policy.actionState)
  if Chat and policy.belief.alive:
    let shout = policy.belief.chooseShout()
    if shout.isSome:
      policy.belief.chatLastSentText = shout.get
      result.chat = shout.get
