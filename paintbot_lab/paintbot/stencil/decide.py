"""The bridge-facing decide callable, plus structured trace emission.

A slimmed port of beacon's decide.py: the same snapshot/transition scheme
(periodic full-state snapshots + edge-triggered transitions), minus the
plan/post fields that no longer exist. Trace events flow to the SDK trace sink
(``jsonl@artifact`` by default) and feed the future paintbot event warehouse.
"""

from __future__ import annotations

import sys

from paintbot.stencil.config import DANGER_TRACE_DOWNSAMPLE, DIAG_EVERY_TICKS
from paintbot.stencil.runtime import StencilRuntime, StepInfo
from paintbot.stencil.types import Observation
from players.player_sdk import TraceEvent, TraceSink


def _danger_summary(info: StepInfo) -> dict:
    belief = info.belief
    if belief.danger is None:
        return {}
    ds = DANGER_TRACE_DOWNSAMPLE
    coarse = belief.danger[::ds, ::ds]
    return {
        "danger_mean": round(float(coarse.mean()), 4),
        "danger_max": round(float(coarse.max()), 4),
    }


def _snapshot(info: StepInfo) -> dict:
    belief = info.belief
    wm = belief.worldmap
    return {
        "tick": info.tick,
        "team": belief.team,
        "seat": belief.seat,
        "slot": belief.slot,
        "role": belief.role,
        "alive": belief.alive,
        "self_xy": belief.self_xy,
        "aim_brads": belief.aim_brads,
        "intent": info.intent.reason,
        "intent_point": info.intent.point,
        "flow_goal": info.flow_goal,
        "micro": belief.micro,
        "carrying": belief.i_carry_heart_of,
        "steal_target": belief.steal_target,
        "own_heart_stolen": belief.own_heart_stolen,
        "hearts_retired": sorted(belief.hearts_retired),
        "enemies_visible": len(belief.enemies),
        "teammates_visible": len(belief.teammates),
        "enemy_tracks": len(belief.enemy_tracks),
        "hp_pips": belief.hp_pips,
        "have": {
            "grenade": belief.i_have_grenade,
            "shield": belief.i_have_shield,
            "arc": belief.i_have_arc,
        },
        "team_scores": {k: list(v) for k, v in belief.team_scores.items()},
        "firefight_active": belief.firefight_active,
        "converting": belief.converting,
        "under_fire": belief.under_fire,
        "worldmap": (
            {
                "w": wm.width,
                "h": wm.height,
                "teams": wm.teams,
                "seats_per_team": wm.seats_per_team(),
                "grid": [wm.grid_w, wm.grid_h],
            }
            if wm is not None
            else None
        ),
        "mask": info.command.held_mask,
        "chat": info.command.chat,
        **_danger_summary(info),
    }


def _counters(info: StepInfo) -> dict:
    belief = info.belief
    return {
        "friendly_fire_suppressed": belief.friendly_fire_suppressed,
        "aim_resyncs": belief.aim_resyncs,
        "firing_turns": belief.firing_turns,
        "firefight_ticks_total": belief.firefight_ticks_total,
        "firefight_engagements": belief.firefight_engagements,
        "firefight_target_switches": belief.firefight_target_switches,
        "focus_claims_sent": belief.focus_claims_sent,
        "focus_claims_heard": belief.focus_claims_heard,
        "focus_claims_suppressed": belief.focus_claims_suppressed,
        "shots_by_range": dict(belief.firefight_shot_range_counts),
        "targets_by_range": dict(belief.firefight_target_range_counts),
        "grenade_starts": dict(belief.grenade_target_starts),
        "grenade_releases": dict(belief.grenade_target_releases),
        "grenade_safety_vetoes": belief.grenade_safety_vetoes,
        "chat_sent": dict(belief.chat_sent_counts),
        "chat_heard": dict(belief.chat_heard_counts),
        "item_fetch_ticks": belief.item_fetch_ticks,
        "item_yield_ticks": belief.item_yield_ticks,
        "convert_events": belief.convert_events,
        "spray_pursuit_ticks": belief.spray_pursuit_ticks,
    }


class _Tracer:
    """Edge-triggered transitions + periodic snapshots."""

    def __init__(self, sink: TraceSink | None) -> None:
        self.sink = sink
        self._last_alive: bool | None = None
        self._last_intent: str | None = None
        self._last_carrying: str | None = None
        self._last_worldmap_sig: tuple | None = None

    def _emit(self, tick: int, name: str, data: dict) -> None:
        assert self.sink is not None
        self.sink.record(TraceEvent(tick=tick, name=name, data=data))

    def __call__(self, info: StepInfo) -> None:
        if self.sink is None:
            return
        belief = info.belief
        try:
            wm_sig = belief.worldmap.signature() if belief.worldmap is not None else None
            if wm_sig != self._last_worldmap_sig:
                self._last_worldmap_sig = wm_sig
                self._emit(info.tick, "worldmap", _snapshot(info))
            if belief.alive != self._last_alive:
                self._last_alive = belief.alive
                self._emit(info.tick, "alive" if belief.alive else "dead", {})
            if info.intent.reason != self._last_intent:
                self._last_intent = info.intent.reason
                self._emit(
                    info.tick,
                    "objective",
                    {"reason": info.intent.reason, "point": info.intent.point},
                )
            if belief.i_carry_heart_of != self._last_carrying:
                self._last_carrying = belief.i_carry_heart_of
                self._emit(info.tick, "carry", {"color": belief.i_carry_heart_of})
            if DIAG_EVERY_TICKS > 0 and info.tick % DIAG_EVERY_TICKS == 0:
                self._emit(info.tick, "snapshot", {**_snapshot(info), **_counters(info)})
        except Exception as exc:  # tracing must never kill the seat
            print(f"stencil trace error: {exc}", file=sys.stderr, flush=True)


def build_decide(slot: int, *, trace_sink: TraceSink | None = None):
    """Build the bridge ``decide`` callable around a StencilRuntime."""
    tracer = _Tracer(trace_sink)
    runtime = StencilRuntime(slot, on_step=tracer)

    def decide(world, ctx):
        command = runtime.step(Observation(world=world, frame=ctx.frame))
        if command.chat is not None:
            return command.held_mask, command.chat
        return command.held_mask

    return decide


__all__ = ["build_decide"]
