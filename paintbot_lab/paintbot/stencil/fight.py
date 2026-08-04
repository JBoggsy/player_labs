"""Intentional gun target selection and local focus-fire claims.

Firefight is a combat overlay, never a movement mode: strategy.py still chooses
where stencil moves, while this module chooses which *visible* enemy the gun
watches. The score favors finishable wounds, the effective 220-300px gun band,
clear firing geometry, and low traverse cost.

Beacon ranked bullet-line clearance off the baked 32-direction sightline field;
with procgen maps there is no bake, so candidate shootability uses the
WorldMap's exact wall-mask ray (at most eight candidates per tick — cheap).
"""

from __future__ import annotations

import math
from dataclasses import replace

from paintbot.stencil import squads
from paintbot.stencil.config import (
    FF_AIM_COST_WEIGHT,
    FF_CLAIM_LOCALITY_PX,
    FF_CLAIM_MATCH_PX,
    FF_CLAIM_REBROADCAST_TICKS,
    FF_CLAIM_TTL_TICKS,
    FF_CLAIM_WEIGHT,
    FF_DEATH_MISSING_TICKS,
    FF_DWELL_TICKS,
    FF_RADIUS_PX,
    FF_RANGE_CLOSE_PX,
    FF_RANGE_IDEAL_MAX_PX,
    FF_RANGE_IDEAL_MIN_PX,
    FF_RANGE_SCORE_FALLOFF_PX,
    FF_RANGE_WEIGHT,
    FF_SHIELD_WEIGHT,
    FF_SHOOTABILITY_WEIGHT,
    FF_TARGET_MIN_DWELL_TICKS,
    FF_TARGET_MISSING_TICKS,
    FF_TARGET_SWITCH_MARGIN,
    FF_WOUND_UNKNOWN,
    FF_WOUND_WEIGHT,
    FIREFIGHT,
    FOCUS_CLAIMS,
    MAX_SPEED_PX_TICK,
    NAV_CELL,
    TRACK_MATCH_SLACK_PX,
)
from paintbot.stencil.types import (
    Belief,
    Enemy,
    FocusClaim,
    TargetCandidate,
    TargetRef,
    TargetScore,
)


def _distance(a: tuple[int, int], b: tuple[int, int]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _enemy_deaths(belief: Belief) -> int | None:
    """Aggregate deaths of the weakest enemy team (claim-release corroboration)."""
    if belief.worldmap is None:
        return None
    lives = squads.enemy_lives_left(belief)
    if lives is None:
        return None
    return belief.worldmap.team_total_lives() - lives


def range_bucket(distance_px: float) -> str:
    """Stable bins shared by selected-target and actual-shot tracing."""
    if distance_px < 200:
        return "0_199"
    if distance_px < 300:
        return "200_299"
    if distance_px < 400:
        return "300_399"
    return "400_plus"


def line_clear(belief: Belief, origin: tuple[int, int], target: tuple[int, int]) -> bool:
    """Bullet-line clearance from the episode wall mask (glass blocks bullets)."""
    if belief.worldmap is None:
        return True
    return belief.worldmap.ray_clear(origin, target)


def target_ref_for(belief: Belief, enemy: Enemy) -> TargetRef:
    """Current target handle, promoting a track's sticky badge when available."""
    identity = enemy.identity
    if identity is None:
        track = next(
            (
                item
                for item in belief.enemy_tracks
                if item.last_tick == belief.tick and item.pos == enemy.pos
            ),
            None,
        )
        if track is not None:
            identity = track.identity
    return TargetRef(identity=identity, pos=enemy.pos)


def _enemy_matches_ref(belief: Belief, enemy: Enemy, target: TargetRef) -> bool:
    if target.identity is not None:
        if enemy.identity == target.identity:
            return True
        if enemy.identity is not None:
            return False
        return any(
            track.identity == target.identity
            and track.last_tick == belief.tick
            and track.pos == enemy.pos
            for track in belief.enemy_tracks
        )
    if enemy.identity is not None:
        return _distance(enemy.pos, target.pos) <= FF_CLAIM_MATCH_PX
    age = (
        max(0, belief.tick - belief.firefight_target_last_seen_tick)
        if belief.firefight_target_last_seen_tick >= 0
        else 0
    )
    reach = age * MAX_SPEED_PX_TICK + TRACK_MATCH_SLACK_PX
    return _distance(enemy.pos, target.pos) <= max(FF_CLAIM_MATCH_PX, reach)


def _refs_match(belief: Belief, left: TargetRef, right: TargetRef) -> bool:
    if left.identity is not None and right.identity is not None:
        return left.identity == right.identity
    if _distance(left.pos, right.pos) <= FF_CLAIM_MATCH_PX:
        return True
    return any(
        _enemy_matches_ref(belief, enemy, left)
        and _enemy_matches_ref(belief, enemy, right)
        for enemy in belief.enemies
    )


def _visible_target(
    belief: Belief,
    target: TargetRef,
) -> tuple[Enemy, TargetRef] | None:
    matches = [
        enemy for enemy in belief.enemies if _enemy_matches_ref(belief, enemy, target)
    ]
    if not matches:
        return None
    enemy = min(matches, key=lambda item: _distance(item.pos, target.pos))
    return enemy, target_ref_for(belief, enemy)


def _claim_is_local(belief: Belief, claim: FocusClaim) -> bool:
    if belief.self_xy is None:
        return False
    visible = _visible_target(belief, claim.target)
    if visible is not None:
        return _distance(belief.self_xy, visible[0].pos) <= FF_CLAIM_LOCALITY_PX
    fresh_positions = [
        track.pos
        for track in belief.enemy_tracks
        if belief.tick - track.last_tick <= FF_TARGET_MISSING_TICKS
        and (
            (
                claim.target.identity is not None
                and track.identity == claim.target.identity
            )
            or (
                claim.target.identity is None
                and _distance(track.pos, claim.target.pos) <= FF_CLAIM_MATCH_PX
            )
        )
    ]
    if fresh_positions:
        return min(_distance(belief.self_xy, pos) for pos in fresh_positions) <= (
            FF_CLAIM_LOCALITY_PX
        )
    return _distance(belief.self_xy, claim.target.pos) <= FF_CLAIM_LOCALITY_PX


def _range_term(distance_px: float) -> float:
    ideal_min = min(FF_RANGE_IDEAL_MIN_PX, FF_RANGE_SCORE_FALLOFF_PX)
    ideal_max = min(max(FF_RANGE_IDEAL_MAX_PX, ideal_min), FF_RANGE_SCORE_FALLOFF_PX)
    close = min(FF_RANGE_CLOSE_PX, ideal_min)
    if distance_px <= close or distance_px > FF_RANGE_SCORE_FALLOFF_PX:
        return 0.0
    if distance_px < ideal_min:
        return (distance_px - close) / max(ideal_min - close, 1)
    if distance_px <= ideal_max:
        return 1.0
    return (FF_RANGE_SCORE_FALLOFF_PX - distance_px) / max(
        FF_RANGE_SCORE_FALLOFF_PX - ideal_max,
        1,
    )


def _wound_term(enemy: Enemy) -> float:
    if enemy.hp_segments is None:
        return FF_WOUND_UNKNOWN
    return (3 - enemy.hp_segments) / 2


def score_target(candidate: TargetCandidate, *, claimed: bool) -> TargetScore:
    """Pure weighted score for one visible enemy."""
    wound = _wound_term(candidate.enemy)
    range_band = _range_term(candidate.distance_px)
    claim = 1.0 if claimed else 0.0
    shootability = 1.0 if candidate.shootable else -1.0
    shield = 1.0 if candidate.enemy.shielded else 0.0
    score = (
        FF_WOUND_WEIGHT * wound
        + FF_RANGE_WEIGHT * range_band
        + FF_CLAIM_WEIGHT * claim
        + FF_SHOOTABILITY_WEIGHT * shootability
        - FF_AIM_COST_WEIGHT * candidate.aim_cost
        - FF_SHIELD_WEIGHT * shield
    )
    return TargetScore(
        candidate=candidate,
        score=score,
        wound=wound,
        range_band=range_band,
        claim=claim,
        shootability=shootability,
        aim_cost=candidate.aim_cost,
        shield=shield,
    )


def _sort_key(scored: TargetScore) -> tuple[float, int, int, int, int]:
    target = scored.candidate.target
    known = 0 if target.identity is not None else 1
    identity = target.identity if target.identity is not None else 8
    return (
        -scored.score,
        known,
        identity,
        target.pos[1] // NAV_CELL,
        target.pos[0] // NAV_CELL,
    )


def _claimed_target(belief: Belief, target: TargetRef) -> bool:
    claim = belief.focus_claim
    return (
        FOCUS_CLAIMS
        and claim is not None
        and _claim_is_local(belief, claim)
        and _refs_match(belief, claim.target, target)
    )


def _record_selected_target(belief: Belief, selected: TargetScore) -> None:
    target = selected.candidate.target
    changed = belief.firefight_target is not None and not _refs_match(
        belief, belief.firefight_target, target
    )
    if changed:
        belief.firefight_target_switches += 1
        belief.firefight_target_selected_tick = belief.tick
    elif belief.firefight_target is None:
        belief.firefight_target_selected_tick = belief.tick
    belief.firefight_target = target
    belief.firefight_target_score = selected
    belief.firefight_target_last_seen_tick = belief.tick
    bucket = range_bucket(selected.candidate.distance_px)
    belief.firefight_target_range_counts[bucket] = (
        belief.firefight_target_range_counts.get(bucket, 0) + 1
    )


def select_target(
    belief: Belief,
    candidates: tuple[TargetCandidate, ...],
) -> TargetScore | None:
    """Rank visible targets and apply a short target latch."""
    if not FIREFIGHT or not belief.firefight_active or not candidates:
        belief.firefight_target_score = None
        return None

    scored = sorted(
        (
            score_target(candidate, claimed=_claimed_target(belief, candidate.target))
            for candidate in candidates
        ),
        key=_sort_key,
    )
    best = scored[0]
    if belief.firefight_target is None:
        _record_selected_target(belief, best)
        return best

    current_target = belief.firefight_target
    current = next(
        (
            item
            for item in scored
            if _refs_match(belief, current_target, item.candidate.target)
        ),
        None,
    )
    if current is None:
        _record_selected_target(belief, best)
        return best
    if _refs_match(belief, current.candidate.target, best.candidate.target):
        _record_selected_target(belief, current)
        return current

    current_age = belief.tick - belief.firefight_target_selected_tick
    immediate = not current.candidate.shootable and best.candidate.shootable
    materially_better = (
        current_age >= FF_TARGET_MIN_DWELL_TICKS
        and best.score >= current.score + FF_TARGET_SWITCH_MARGIN
    )
    selected = best if immediate or materially_better else current
    _record_selected_target(belief, selected)
    return selected


def release_focus_claim(belief: Belief, reason: str) -> None:
    """Release the active claim and retain a traceable production reason."""
    if belief.focus_claim is None:
        return
    belief.focus_claim = None
    belief.focus_last_release_reason = reason
    belief.focus_claim_release_counts[reason] = (
        belief.focus_claim_release_counts.get(reason, 0) + 1
    )


def receive_focus_claim(
    belief: Belief,
    *,
    claimant_seat: int,
    target_identity: int | None,
    target_cell: tuple[int, int],
) -> None:
    """Accept or refresh the first relevant claim in this local firefight."""
    if not FIREFIGHT or not FOCUS_CLAIMS or claimant_seat == belief.seat:
        return
    belief.focus_claims_heard += 1
    incoming_target = TargetRef(target_identity, target_cell)
    incoming = FocusClaim(
        claimant_seat=claimant_seat,
        target=incoming_target,
        first_tick=belief.tick,
        refreshed_tick=belief.tick,
        last_seen_tick=belief.tick,
        enemy_deaths_at_last_seen=_enemy_deaths(belief),
    )
    if not _claim_is_local(belief, incoming):
        return

    current = belief.focus_claim
    if current is not None and belief.tick - current.refreshed_tick > FF_CLAIM_TTL_TICKS:
        release_focus_claim(belief, "claim_ttl")
        current = None
    if current is None:
        belief.focus_claim = incoming
        return

    same_target = _refs_match(belief, current.target, incoming_target)
    if current.claimant_seat == claimant_seat and same_target:
        identity = incoming_target.identity or current.target.identity
        belief.focus_claim = replace(
            current,
            target=TargetRef(identity, incoming_target.pos),
            refreshed_tick=belief.tick,
            last_seen_tick=belief.tick,
            enemy_deaths_at_last_seen=_enemy_deaths(belief),
        )
        return

    if current.first_tick == belief.tick:
        current_rank = (
            squads.rank_of(belief, current.claimant_seat),
            current.claimant_seat,
        )
        incoming_rank = (squads.rank_of(belief, claimant_seat), claimant_seat)
        if incoming_rank < current_rank:
            belief.focus_claim = incoming
            return
    belief.focus_claims_suppressed += 1


def focus_claim_to_send(belief: Belief) -> TargetRef | None:
    """The selected target this bot may acquire/refresh, else None."""
    if (
        not FIREFIGHT
        or not FOCUS_CLAIMS
        or not belief.firefight_active
        or belief.i_have_arc
        or belief.firefight_target_score is None
        or belief.tick - belief.focus_last_claim_sent_tick < FF_CLAIM_REBROADCAST_TICKS
    ):
        return None
    target = belief.firefight_target_score.candidate.target
    claim = belief.focus_claim
    if claim is None:
        return target
    if claim.claimant_seat == belief.seat and _refs_match(belief, claim.target, target):
        return target
    if _claim_is_local(belief, claim):
        belief.focus_claims_suppressed += 1
        return None
    return target


def note_focus_claim_sent(belief: Belief, target: TargetRef) -> None:
    """Install or refresh our claim only after chat actually emitted F."""
    current = belief.focus_claim
    first_tick = (
        current.first_tick
        if current is not None
        and current.claimant_seat == belief.seat
        and _refs_match(belief, current.target, target)
        else belief.tick
    )
    belief.focus_claim = FocusClaim(
        claimant_seat=belief.seat,
        target=target,
        first_tick=first_tick,
        refreshed_tick=belief.tick,
        last_seen_tick=belief.tick,
        enemy_deaths_at_last_seen=_enemy_deaths(belief),
    )
    belief.focus_last_claim_sent_tick = belief.tick
    belief.focus_claims_sent += 1


def _update_claim_lifecycle(belief: Belief) -> None:
    claim = belief.focus_claim
    if claim is None:
        return
    if belief.tick - claim.refreshed_tick > FF_CLAIM_TTL_TICKS:
        release_focus_claim(belief, "claim_ttl")
        return
    visible = _visible_target(belief, claim.target)
    if visible is not None:
        _enemy, target = visible
        belief.focus_claim = replace(
            claim,
            target=target,
            last_seen_tick=belief.tick,
            enemy_deaths_at_last_seen=_enemy_deaths(belief),
        )
        return

    missing = belief.tick - claim.last_seen_tick
    deaths = _enemy_deaths(belief)
    death_correlated = (
        deaths is not None
        and claim.enemy_deaths_at_last_seen is not None
        and deaths > claim.enemy_deaths_at_last_seen
    )
    if missing >= FF_DEATH_MISSING_TICKS and death_correlated:
        release_focus_claim(belief, "scoreboard_death")
    elif missing >= FF_TARGET_MISSING_TICKS:
        release_focus_claim(belief, "target_missing")


def update_firefight(belief: Belief) -> None:
    """Update firefight hysteresis and claim expiry from this frame's belief."""
    if not FIREFIGHT:
        return
    if not belief.alive or belief.self_xy is None:
        if (
            belief.focus_claim is not None
            and belief.focus_claim.claimant_seat == belief.seat
        ):
            release_focus_claim(belief, "claimant_dead")
        belief.firefight_active = False
        belief.firefight_target = None
        belief.firefight_target_score = None
        belief.firefight_target_selected_tick = -1
        belief.firefight_target_last_seen_tick = -1
        _update_claim_lifecycle(belief)
        return

    trigger = belief.under_fire or any(
        _distance(belief.self_xy, enemy.pos) <= FF_RADIUS_PX
        for enemy in belief.enemies
    )
    if trigger:
        belief.firefight_last_trigger_tick = belief.tick

    would_be_active = trigger or (
        belief.tick - belief.firefight_last_trigger_tick <= FF_DWELL_TICKS
    )
    if belief.i_have_arc:
        if would_be_active:
            belief.firefight_arc_exempt_ticks += 1
        belief.firefight_active = False
        belief.firefight_target = None
        belief.firefight_target_score = None
        _update_claim_lifecycle(belief)
        return

    if not belief.firefight_active and trigger:
        belief.firefight_active = True
        belief.firefight_entered_tick = belief.tick
        belief.firefight_engagements += 1
        belief.firefight_target = None
        belief.firefight_target_score = None
        belief.firefight_target_selected_tick = -1
        belief.firefight_target_last_seen_tick = -1
    elif belief.firefight_active and not would_be_active:
        belief.firefight_active = False
        belief.firefight_target = None
        belief.firefight_target_score = None
        belief.firefight_target_selected_tick = -1
        belief.firefight_target_last_seen_tick = -1

    if belief.firefight_active:
        belief.firefight_ticks_total += 1
    _update_claim_lifecycle(belief)


__all__ = [
    "focus_claim_to_send",
    "line_clear",
    "note_focus_claim_sent",
    "range_bucket",
    "receive_focus_claim",
    "release_focus_claim",
    "score_target",
    "select_target",
    "target_ref_for",
    "update_firefight",
]
