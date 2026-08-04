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
  lastFlowGoal*: Option[Point]

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
    policy.teamsKnown = true
  if percept.walkability.len > 0 and percept.gameTeams.isSome and
      percept.endzones.len >= policy.belief.colors.len:
    let signature = (percept.walkabilityWidth, percept.walkabilityHeight,
      percept.gameTeams.get)
    if policy.belief.worldmap.isNil or policy.belief.worldmap.signature != signature:
      policy.belief.worldmap = newWorldMap(
        percept.walkability, percept.walkabilityWidth, percept.walkabilityHeight,
        percept.gameTeams.get, percept.endzones)
      policy.rolesAssigned = false
      discard policy.belief.worldmap.routeDistance(
        policy.belief.worldmap.center,
        policy.belief.worldmap.capturePoint(policy.belief.team))
  updateBeliefCore(policy.belief, percept, policy.actionState, policy.tick)
  if not policy.rolesAssigned and not policy.belief.worldmap.isNil:
    let seats = policy.belief.worldmap.seatsPerTeam
    policy.belief.role = roleForSeat(policy.belief.seat, seats)
    policy.belief.holdPoint = if policy.belief.role == Defender:
      some(holdPointForSeat(policy.belief.worldmap, policy.belief.team,
        policy.belief.seat, seats))
    else:
      none(Point)
    policy.rolesAssigned = true
  let objective = if policy.belief.alive:
    policy.belief.decideObjective()
  else:
    Objective(intent: Intent(kind: Hold, point: none(Point), reason: "not_alive"),
      flowGoal: none(Point))
  policy.lastIntent = objective.intent
  policy.lastFlowGoal = objective.flowGoal
  result = resolveAction(objective.intent, policy.belief, policy.actionState)
  if Chat and policy.belief.alive:
    let shout = policy.belief.chooseShout()
    if shout.isSome:
      policy.belief.chatLastSentText = shout.get
      result.chat = shout.get
