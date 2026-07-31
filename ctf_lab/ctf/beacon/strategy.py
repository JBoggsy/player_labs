"""The priority ladder — choose ONE navigation objective per tick (v2, role-aware).

Combat and aim are NOT a rung here; they ride as an overlay in action.py (sweep the
threat axis, snap-and-fire on any visible enemy). The ladder only decides *where to
move*. See design §5, and TENTATIVE_LESSONS (games are decided by wipe → defense wins).

Returns an Intent plus the flow-field kind to use ("steal" / "home" / None for A*).
"""

from __future__ import annotations

import math

from ctf.beacon import items, poi, posts, squads
from ctf.beacon import plan as _plan
from ctf.beacon.config import (
    ANTI_TURTLE,
    ANTI_TURTLE_MIN_TICK,
    ANTI_TURTLE_OUTSIDE_RATE_MAX,
    BASE_ASSAULT_LIFE_DEFICIT,
    BASE_FRONT_X,
    GRENADE_WARN_CLEAR_PX,
    HOLD_ARRIVE_PX,
    ITEM_ASSIGNED_DETOUR_PX,
    ITEM_CONVENIENCE,
    ITEMS,
    ITEM_RESPAWN_WINDOW_TICKS,
    ITEM_SHADOW_EVERY_TICKS,
    MEDKIT_CONVENIENT_DETOUR_PX,
    ORDER_TTL_TICKS,
    PEDESTAL,
    PLAN_ARRIVE_PX,
    PLAN_NAME,
    POSTS,
    SQUAD_COMMAND,
    SQUADS,
    TEAM_TOTAL_LIVES,
)
from ctf.beacon.types import Belief, Intent


def _dist(a: tuple[int, int], b: tuple[int, int]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _post_objective(belief: Belief, post: posts.Post, reason: str) -> tuple[Intent, None]:
    """Hold a settled post; otherwise reach it through the normal motion stack."""

    if belief.post_settled_ticks > 0:
        return Intent(kind="hold", reason=reason), None
    return Intent(kind="navigate_to", point=post.cell, reason=reason), None


def _own_lives_left(belief: Belief) -> int | None:
    if belief.own_team_score is None:
        return None
    return max(0, TEAM_TOTAL_LIVES - belief.own_team_score[1])


def _enemy_life_advantage(belief: Belief) -> int | None:
    own = _own_lives_left(belief)
    enemy = squads.enemy_lives_left(belief)
    if own is None or enemy is None:
        return None
    return enemy - own


def _inside_enemy_base(belief: Belief, point: tuple[int, int]) -> bool:
    assert belief.team is not None
    enemy = "blue" if belief.team == "red" else "red"
    front_x = BASE_FRONT_X[enemy]
    return point[0] >= front_x if enemy == "blue" else point[0] <= front_x


def _update_anti_turtle(belief: Belief) -> None:
    """Latch a rally hold for opponents that remain behind their lineup."""
    advantage = _enemy_life_advantage(belief)
    belief.base_caution_active = (
        advantage is not None and advantage >= BASE_ASSAULT_LIFE_DEFICIT
    )
    if belief.base_caution_active:
        belief.base_caution_ticks += 1

    if belief.anti_turtle_latched:
        belief.anti_turtle_ticks += 1
        return
    if (
        not ANTI_TURTLE
        or belief.tick < ANTI_TURTLE_MIN_TICK
        or belief.enemy_observation_ticks == 0
        or not belief.post_committed
        or belief.post_context != "plan"
    ):
        return
    book = _plan.PlanBook.load(PLAN_NAME) if PLAN_NAME else None
    if book is None or belief.plan_phase != len(book.phases) - 1:
        return
    outside_rate = (
        belief.enemy_outside_base_ticks / belief.enemy_observation_ticks
    )
    if outside_rate <= ANTI_TURTLE_OUTSIDE_RATE_MAX:
        belief.anti_turtle_latched = True
        belief.anti_turtle_activations += 1
        belief.anti_turtle_ticks += 1


def _item_anchor(belief: Belief, enemy: str) -> tuple[tuple[int, int], str]:
    """Current non-emergency objective used to price a pickup detour."""
    if belief.post_cell is not None and (
        belief.post_committed or belief.post_settled_ticks > 0
    ):
        return belief.post_cell, "post"
    if (
        belief.order is not None
        and belief.tick - belief.order[2] <= ORDER_TTL_TICKS
    ):
        return belief.order[1], "order"
    if PLAN_NAME:
        book = _plan.PlanBook.load(PLAN_NAME)
        if book is not None:
            # Do not call current_objective here: buddy-wait accounting makes
            # that accessor stateful. The actual plan rung owns that mutation;
            # item pricing needs only a pure approximation of its destination.
            group = book.group_of(belief.seat, belief.plan_phase)
            order = (
                book.primary_order(group, belief.plan_phase)
                if group is not None
                else None
            )
            if order is not None:
                target = (
                    order.fallback
                    if (
                        order.kind == "hold"
                        and belief.plan_fell_back
                        and order.fallback is not None
                    )
                    else order.target
                )
                objective_xy = poi.resolve(target, belief.team)
                if objective_xy is not None:
                    return objective_xy, "plan"
    if belief.role == "defender" and belief.hold_point is not None:
        return belief.hold_point, "role"
    return PEDESTAL[enemy], "role"


def _item_intent(
    belief: Belief,
    anchor: tuple[int, int],
    anchor_kind: str,
    *,
    respawning: bool = False,
    incidental_only: bool = False,
) -> tuple[Intent, None] | None:
    if not ITEMS:
        return None
    choice = items.evaluate_fetch(
        belief,
        anchor,
        anchor_kind=anchor_kind,
        respawning=respawning,
        incidental_only=incidental_only,
    )
    if choice is None or not choice.accepted:
        return None
    reason = "fetch_medkit" if choice.spawn.kind == "medkit" else "fetch_item"
    return Intent(kind="navigate_to", point=choice.spawn.pos, reason=reason), None


def decide_objective(belief: Belief) -> tuple[Intent, str | None]:
    """Pick the single movement objective. Returns (intent, flow_kind)."""
    team = belief.team
    assert team is not None
    enemy = "blue" if team == "red" else "red"
    # Activation is recomputed every tick. Higher rungs therefore suppress post
    # claims and post-facing without needing to know that posts exist.
    belief.post_active = False
    if ITEM_CONVENIENCE:
        belief.item_options = []
        belief.item_choice = None
    _update_anti_turtle(belief)

    # Squad command upkeep (v22): refresh presence from badge sightings; leaders
    # run the rule engine (sets belief.order); heard orders arrive via belief.
    if SQUAD_COMMAND:
        squads.update_presence(belief)
        squads.lead_squad(belief)

    # Rung 1 (everyone): carrying the enemy flag -> run it home. A carried flag is a
    # win one delivery away, and dying returns it instantly. Overrides role.
    if belief.i_carry_enemy_flag:
        return Intent(kind="navigate_to", point=None, reason="carry_home"), "home"

    # Rung 1.5 (v22 respawn discipline): freshly respawned -> REJOIN the squad
    # first. Move to the snapshotted regroup point (the squad HOLDS on member
    # loss, so the stale memory is accurate); the peek/duck micro + danger field
    # supply the caution en route. Exits on squad contact or timeout. Sits below
    # carry (a flag in hand always runs home) and above everything else — a lone
    # agent trickling into contact is the exact feed this rung exists to stop.
    if SQUAD_COMMAND and belief.rejoin_until >= 0 and belief.self_xy is not None:
        if belief.tick >= belief.rejoin_until or squads.in_squad_contact(belief):
            belief.rejoin_until = -1
            belief.rejoin_point = None
        elif belief.rejoin_point is not None:
            if ITEM_CONVENIENCE:
                item_intent = _item_intent(
                    belief,
                    belief.rejoin_point,
                    "rejoin",
                    respawning=True,
                    incidental_only=True,
                )
                if item_intent is not None:
                    return item_intent
            belief.rejoin_ticks += 1
            if _dist(belief.self_xy, belief.rejoin_point) > 40:
                return Intent(kind="navigate_to", point=belief.rejoin_point, reason="rejoin"), None
            # At the point but no contact yet: hold there (sweep covers the arc).
            return Intent(kind="hold", reason="rejoin_hold"), None

    # Rung 2 (everyone): our flag is stolen and we have a thief fix -> intercept.
    # Killing the carrier returns the flag instantly; this is the anti-capture play.
    # The fix is our OWN eyes first, else a teammate's T shout (v18) — chat turns a
    # personal sighting into a team-wide manhunt.
    if belief.own_flag_stolen:
        if belief.own_flag_thief_pos is not None:
            return Intent(kind="navigate_to", point=belief.own_flag_thief_pos, reason="intercept_thief"), None
        if belief.thief_fix is not None:
            return Intent(kind="navigate_to", point=belief.thief_fix[0], reason="intercept_thief_heard"), None

    # Rung 3 (attackers): a TEAMMATE is carrying our stolen enemy flag -> escort it.
    # Sight-based fix first (the flag sprite rides the carrier); else the carrier's
    # C heartbeat (v18) — projected one step along its shouted heading octant, so a
    # fogged carrier still gathers its escorts. Attackers converge and move home
    # WITH it — the fix for "grabs the flag but dies before delivery".
    if belief.role == "attacker" and not belief.i_carry_enemy_flag and not belief.enemy_flag_on_pedestal:
        if belief.enemy_flag_pos is not None:
            return Intent(kind="navigate_to", point=belief.enemy_flag_pos, reason="escort_carrier"), None
        if belief.carrier_fix is not None:
            (cx, cy), octant, heard_tick = belief.carrier_fix
            dt = min(belief.tick - heard_tick, 48)
            ang = octant * math.pi / 4
            px = int(cx + math.cos(ang) * 1.9 * dt)  # ~70% of max speed while carrying
            py = int(cy - math.sin(ang) * 1.9 * dt)
            return Intent(kind="navigate_to", point=(px, py), reason="escort_carrier_heard"), None

    # Rung 3.4 (v18): a teammate shouted a grenade landing near us -> step clear.
    # The blast (52px) hurts teammates; the warning names the landing cell.
    if belief.self_xy is not None:
        for gpos, _t in belief.grenade_warnings:
            d = _dist(belief.self_xy, gpos)
            if d < GRENADE_WARN_CLEAR_PX:
                # Flee directly away from the landing point.
                dx = belief.self_xy[0] - gpos[0]
                dy = belief.self_xy[1] - gpos[1]
                n = max(d, 1.0)
                flee = (
                    int(belief.self_xy[0] + dx / n * GRENADE_WARN_CLEAR_PX),
                    int(belief.self_xy[1] + dy / n * GRENADE_WARN_CLEAR_PX),
                )
                return Intent(kind="navigate_to", point=flee, reason="clear_grenade"), None

    # Rung 3.5: insert a pickup only when its extra walkable-route cost relative
    # to the current post/order/plan/role objective is genuinely convenient.
    if belief.self_xy is not None:
        if ITEMS and not ITEM_CONVENIENCE:
            # Shadow the route scorer while preserving v48's active behavior.
            if (
                belief.tick + belief.seat
            ) % ITEM_SHADOW_EVERY_TICKS == 0:
                anchor, anchor_kind = _item_anchor(belief, enemy)
                items.evaluate_fetch(
                    belief,
                    anchor,
                    anchor_kind=anchor_kind,
                    respawning=(
                        belief.tick - belief.respawned_tick
                        <= ITEM_RESPAWN_WINDOW_TICKS
                    ),
                )
        if ITEMS:
            # Preserve v48's medkit and assigned-item decisions exactly. The
            # convenience capability is additive only after both decline.
            kit = items.medkit_target(
                belief,
                MEDKIT_CONVENIENT_DETOUR_PX,
            )
            if kit is not None:
                return (
                    Intent(
                        kind="navigate_to",
                        point=kit.pos,
                        reason="fetch_medkit",
                    ),
                    None,
                )
            assigned = items.assigned_fetch(belief)
            if (
                assigned is not None
                and _dist(belief.self_xy, assigned.pos)
                <= ITEM_ASSIGNED_DETOUR_PX
            ):
                return (
                    Intent(
                        kind="navigate_to",
                        point=assigned.pos,
                        reason="fetch_item",
                    ),
                    None,
                )
        if ITEM_CONVENIENCE:
            anchor, anchor_kind = _item_anchor(belief, enemy)
            item_intent = _item_intent(
                belief,
                anchor,
                anchor_kind,
                respawning=(
                    belief.tick - belief.respawned_tick
                    <= ITEM_RESPAWN_WINDOW_TICKS
                ),
                incidental_only=True,
            )
            if item_intent is not None:
                return item_intent

    # Rung 4 (v22): obey the squad order when one is live. Goals map onto the
    # existing machinery: H/S hold a point (sectors cover the approaches), P
    # pushes a point fighting en route, F flags (steal / the escort rungs above
    # already handle a live carrier), T hunts at the ordered fix.
    if SQUAD_COMMAND and belief.order is not None and belief.self_xy is not None:
        goal, opos, set_tick = belief.order
        if belief.tick - set_tick > ORDER_TTL_TICKS:
            # Order DECAY (v24): a member whose order went stale (leader dead /
            # out of earshot) backs off into a HOLD at its position stepped
            # toward home — the same posture as losing a teammate. No orders =
            # no coordination = no business pushing (lives > captures). The
            # self-issued hold refreshes its own TTL; a live leader overrides
            # it on the next heard O. v26: unless the WIPE IS IN REACH — the
            # scoreboard is global, so a leaderless member can still convert
            # (backing off 2 kills from a wipe is the worst move in the game).
            if squads.wipe_in_reach(belief):
                belief.order = ("T", squads.convert_hunt_point(belief), belief.tick)
                belief.order_source = "convert"
            else:
                belief.order = (
                    "H",
                    squads.decay_hold_point(belief),
                    belief.tick,
                )
                belief.order_source = "decay"
            goal, opos, set_tick = belief.order
        order_center = opos
        if (
            POSTS
            and goal in ("H", "S", "P")
            and (
                _dist(belief.self_xy, order_center) <= HOLD_ARRIVE_PX * 2
                or (
                    belief.post_context == "order"
                    and belief.post_center == order_center
                )
            )
        ):
            mode: posts.PostMode = "push" if goal == "P" else "hold"
            post = posts.resolve_post_target(
                belief,
                order_center,
                mode=mode,
                context="order",
            )
            if post is not None:
                return _post_objective(belief, post, "order_post")

        # Spread (v25): rank-offset the shared order point so the squad fans out
        # across its lane instead of stacking on one cell (FF + splash safety).
        if goal in ("H", "S", "P"):
            opos = squads.spread_point(belief.seat, order_center)
        if goal in ("H", "S"):
            if _dist(belief.self_xy, opos) <= HOLD_ARRIVE_PX * 2:
                return Intent(kind="hold", reason="order_hold"), None
            return Intent(kind="navigate_to", point=opos, reason="order_to_hold"), None
        if goal == "P":
            if _dist(belief.self_xy, opos) <= HOLD_ARRIVE_PX * 2:
                return Intent(kind="hold", reason="order_push_arrived"), None
            return Intent(kind="navigate_to", point=opos, reason="order_push"), None
        if goal == "T":
            return Intent(kind="navigate_to", point=opos, reason="order_hunt"), None
        if goal == "F":
            return Intent(kind="navigate_to", point=PEDESTAL[enemy], reason="steal"), "steal"

    # Rung 3.8 (v29): the CONVERT TRIGGER, standalone. Preserved through the
    # squad rollback because it is NOT coordination — it reads the global team
    # scoreboard (fog-independent, same value for every agent) and it is the
    # single biggest measured win (v26 A/B: every focusfire draw became a win).
    # When the wipe is in reach, everyone hunts the freshest enemy evidence.
    if squads.wipe_in_reach(belief) and belief.self_xy is not None:
        hunt_point = squads.convert_hunt_point(belief)
        base_assault_blocked = (
            _inside_enemy_base(belief, hunt_point)
            and (belief.anti_turtle_latched or belief.base_caution_active)
        )
        if base_assault_blocked:
            belief.base_assault_blocked_ticks += 1
        else:
            if not belief.converting:
                belief.converting = True
                belief.convert_events += 1
            return Intent(
                kind="navigate_to",
                point=hunt_point,
                reason="convert_hunt",
            ), None
    belief.converting = False

    # Rung 3.9 (v30): the BATTLE-PLAN interpreter — the co-general plan as
    # OBJECTIVES at exactly this altitude. Everything above (carry, intercept,
    # escort, medkit, grenade-clear, convert) preempts the plan; everything
    # below the intent (A* + danger field, peek/duck, cover, combat overlay)
    # still governs HOW we move to a plan target. Goalposts, not a death march.
    if PLAN_NAME and belief.self_xy is not None:
        book = _plan.PlanBook.load(PLAN_NAME)
        if book is not None and book.phases:
            post: posts.Post | None = None
            if POSTS:
                phase_before = belief.plan_phase
                obj = _plan.current_objective(belief, book)
                if obj is not None and (
                    belief.anti_turtle_latched or belief.base_caution_active
                ):
                    _kind, xy, order = obj
                    obj = ("hold", xy, order)
                # With posts enabled, raw-waypoint proximity is never a phase
                # milestone. No acceptable post means the unconditional phase
                # timeout is the escape hatch.
                milestone_ready = False
                if obj is not None:
                    kind, xy, order = obj
                    latched_here = (
                        belief.post_context == "plan"
                        and belief.post_center == xy
                    )
                    if (
                        (kind == order.kind or kind == "hold")
                        and (
                            _dist(belief.self_xy, xy) <= PLAN_ARRIVE_PX
                            or latched_here
                        )
                    ):
                        facing = (
                            poi.resolve(order.facing, team)
                            if order.facing is not None
                            else None
                        )
                        mode: posts.PostMode = "push" if kind == "move" else "hold"
                        post = posts.resolve_post_target(
                            belief,
                            xy,
                            mode=mode,
                            facing=facing,
                            context="plan",
                        )
                        if post is not None:
                            # Arrival at the selected post advances the plan.
                            # POST_MIN_DWELL_TICKS only governs re-selection.
                            milestone_ready = belief.post_settled_ticks > 0
                _plan.advance(belief, book, milestone_ready=milestone_ready)
                if belief.plan_phase != phase_before:
                    belief.post_active = False
                    post = None
                    obj = _plan.current_objective(belief, book)
            else:
                # Preserve the original call order exactly with the feature off.
                _plan.advance(belief, book)
                obj = _plan.current_objective(belief, book)

            if obj is not None:
                kind, xy, order = obj
                if post is not None:
                    reason = (
                        "anti_turtle_post"
                        if belief.anti_turtle_latched
                        else "base_caution_post"
                        if belief.base_caution_active
                        else "plan_post"
                    )
                    return _post_objective(belief, post, reason)
                if POSTS and _dist(belief.self_xy, xy) <= PLAN_ARRIVE_PX:
                    # Formation spreading remains the floor when no post clears
                    # the geometry and danger thresholds.
                    xy = squads.spread_point(belief.seat, xy)
                if kind == "hold" or _dist(belief.self_xy, xy) <= HOLD_ARRIVE_PX:
                    if _dist(belief.self_xy, xy) <= HOLD_ARRIVE_PX * 2:
                        reason = (
                            "anti_turtle_hold"
                            if belief.anti_turtle_latched
                            else "base_caution_hold"
                            if belief.base_caution_active
                            else "plan_hold"
                        )
                        return Intent(kind="hold", reason=reason), None
                    return Intent(kind="navigate_to", point=xy, reason="plan_to_hold"), None
                return Intent(kind="navigate_to", point=xy, reason="plan_move"), None
            # No order for my seat this phase: fall through to the static split.

    # Rung 4 fallback (no live order / SQUAD_COMMAND off): the static role split.
    if belief.role == "defender" and belief.hold_point is not None:
        # Hold cover on our turf: the enemy dies attacking us (we respawn close),
        # and our flag stops being undefended. Once at the hold point, stop
        # advancing (A* returns ~self) and let the combat overlay work the lane.
        if (
            POSTS
            and belief.self_xy is not None
            and (
                _dist(belief.self_xy, belief.hold_point) <= HOLD_ARRIVE_PX
                or (
                    belief.post_context == "static_hold"
                    and belief.post_center == belief.hold_point
                )
            )
        ):
            post = posts.resolve_post_target(
                belief,
                belief.hold_point,
                mode="hold",
                context="static_hold",
            )
            if post is not None:
                return _post_objective(belief, post, "hold_post")
        if belief.self_xy is not None and _dist(belief.self_xy, belief.hold_point) <= HOLD_ARRIVE_PX:
            return Intent(kind="hold", reason="hold_line"), None
        return Intent(kind="navigate_to", point=belief.hold_point, reason="to_hold"), None

    # Attackers (and defenders with no hold point): push the enemy flag — in a
    # WAVE (v19): hold at the rally line until enough squadmates are near, so the
    # push isn't a dribble of solo attackers (h006's blitz and focusfire's turtle
    # both farm those). Timeout-capped; carriers/intercepts never reach here.
    if SQUADS and squads.should_wait_for_squad(belief):
        belief.squad_wait_ticks += 1
        return Intent(kind="hold", reason="squad_rally"), None
    return Intent(kind="navigate_to", point=PEDESTAL[enemy], reason="steal"), "steal"


__all__ = ["decide_objective"]
