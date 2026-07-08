"""Sprite bridge decide adapter for Cady."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
import sys
from typing import Any

from cady import mapdata
from cady.config import DIAG_EVERY_TICKS, INVITE_VIEW_HALF_H, INVITE_VIEW_HALF_W
from cady.runtime import build_runtime
from cady.types import ActionState, Belief, Command, Intent, Observation
from players.player_sdk import MetricsSink, SpriteContext, SpriteWorld, StepContext, TraceSink

MAP_OBJECT_ID = 1
GARDEN_MARKER_LABEL = "garden marker"


def build_decide(
    *,
    trace_sink: TraceSink | None = None,
    metrics_sink: MetricsSink | None = None,
) -> Callable[[SpriteWorld, SpriteContext], int | tuple[int, str | None]]:
    """Build a stateful bridge callback backed by one runtime instance."""

    diagnostics = _DiagnosticLogger() if _diagnostics_enabled() else None
    runtime = build_runtime(
        trace_sink=trace_sink,
        metrics_sink=metrics_sink,
        on_step_complete=diagnostics.on_step_complete if diagnostics is not None else None,
    )

    def _decide(world: SpriteWorld, ctx: SpriteContext) -> int | tuple[int, str | None]:
        if diagnostics is not None:
            diagnostics.capture_world(world, ctx.frame)
        command = runtime.step(Observation(world=world, frame=ctx.frame))
        # Return (mask, chat) only when speaking this frame; the SDK bridge packs
        # the chat packet and caps it. A bare mask on silent frames.
        if command.chat:
            return int(command.held_mask), command.chat
        return int(command.held_mask)

    return _decide

def decide(world: SpriteWorld, ctx: SpriteContext) -> int:
    """Default module-level callback for ``run_sprite_bridge`` convenience."""

    return _DEFAULT_DECIDE(world, ctx)


class _DiagnosticLogger:
    """Robust per-tick + transition diagnostics for Cady.

    Emits two kinds of ``CADY_DIAG`` lines to stderr (folded into the episode's
    policy log): a periodic full-state snapshot (belief + nav + social + scene),
    and immediate transition lines whenever the mode, strategy directive, map
    context, or a social fact (invite target/broadcast, house entry, inventory
    step, guest scored) changes — so nothing important fires silently between
    snapshots. Everything a post-mortem needs to reconstruct what Cady believed
    and why she acted is here."""

    def __init__(self) -> None:
        self._world: SpriteWorld | None = None
        self._frame: int | None = None
        self._logged_ready = False
        # last-seen values for change detection (transition logging).
        self._last_context: str | None = None
        self._last_mode: str | None = None
        self._last_directive: tuple[str, str] | None = None  # (mode, reason)
        self._last_inventory = 0
        self._last_invited: frozenset[int] = frozenset()
        self._last_committed: int | None = None
        self._last_chat: str | None = None

    def capture_world(self, world: SpriteWorld, frame: int) -> None:
        self._world = world
        self._frame = frame

    def on_step_complete(self, step: StepContext[Belief, ActionState, Intent, Command]) -> None:
        belief = step.belief
        self._log_transitions(step)

        context = belief.map_context
        first_ready = belief.self_xy is not None and not self._logged_ready
        context_changed = self._last_context is not None and context != self._last_context
        cadence = step.tick % DIAG_EVERY_TICKS == 0
        if first_ready:
            self._logged_ready = True
        self._last_context = context

        if first_ready or context_changed or cadence:
            self._emit("snapshot", self._payload(step))

    def _log_transitions(self, step: StepContext[Belief, ActionState, Intent, Command]) -> None:
        """Emit an immediate line on any decision/mode/strategy/social change."""
        belief = step.belief

        if step.active_mode_name != self._last_mode:
            self._emit("mode_change", {
                "tick": step.tick, "from": self._last_mode, "to": step.active_mode_name,
                "time_minutes": belief.last_time_minutes,
            })
            self._last_mode = step.active_mode_name

        directive = (step.active_directive.mode, step.active_directive.reason)
        if directive != self._last_directive:
            self._emit("strategy_directive", {
                "tick": step.tick, "mode": directive[0], "reason": directive[1],
                "source": step.active_directive.source, "time_minutes": belief.last_time_minutes,
            })
            self._last_directive = directive

        if belief.inventory_count != self._last_inventory:
            self._emit("inventory", {
                "tick": step.tick, "from": self._last_inventory, "to": belief.inventory_count,
                "circuit_index": belief.circuit_index,
            })
            self._last_inventory = belief.inventory_count

        invited = frozenset(belief.invited_houses)
        if invited != self._last_invited:
            self._emit("invite_tour", {
                "tick": step.tick, "doors_reached": sorted(invited),
                "own_house": belief.own_house_index, "time_minutes": belief.last_time_minutes,
            })
            self._last_invited = invited

        if belief.committed_party_house != self._last_committed:
            self._emit("party_commit", {
                "tick": step.tick, "house": belief.committed_party_house,
            })
            self._last_committed = belief.committed_party_house

        chat = step.command.chat
        if chat and chat != self._last_chat:
            self._emit("chat_sent", {
                "tick": step.tick, "text": chat, "self_xy": _point(belief.self_xy),
                "villagers_in_view": _in_view_count(belief),
                "time_minutes": belief.last_time_minutes,
            })
        self._last_chat = chat

    def _emit(self, kind: str, payload: dict[str, Any]) -> None:
        print(f"CADY_DIAG {kind} " + json.dumps(payload, separators=(",", ":"), sort_keys=True),
              file=sys.stderr)

    def _payload(self, step: StepContext[Belief, ActionState, Intent, Command]) -> dict[str, Any]:
        world = self._world
        map_obj = None if world is None else world.objects.get(MAP_OBJECT_ID)
        intent = step.intent
        belief = step.belief
        return {
            "tick": step.tick,
            "frame": self._frame,
            "map_context": belief.map_context,
            "self_xy": _point(belief.self_xy),
            "own_house_index": belief.own_house_index,
            "map_object": _map_object_payload(map_obj),
            "camera": None if map_obj is None else [-map_obj.x, -map_obj.y],
            "mode": step.active_mode_name,
            "directive_reason": step.active_directive.reason,
            "intent": intent.kind,
            "intent_point": _point(intent.point),
            "intent_chat": intent.chat,
            "held_mask": step.command.held_mask,
            "chat": step.command.chat,
            "time_minutes": belief.last_time_minutes,
            "inventory_count": belief.inventory_count,
            "garden_marker_count": _garden_marker_count(world),
            # nav
            "circuit_index": belief.circuit_index,
            "nav_goal": _point(belief.nav_goal),
            "nav_cursor": belief.nav_cursor,
            "nav_path_len": None if belief.nav_path is None else len(belief.nav_path),
            "nav_stuck_ticks": belief.nav_stuck_ticks,
            # social
            "invited_houses": sorted(belief.invited_houses),
            "committed_party_house": belief.committed_party_house,
            "villagers_in_view": _in_view_count(belief),
            "n_gnomes_visible": len(belief.gnomes),
            "grid": _grid_dims(belief.map_context),
            "scene": _scene_probe(world),
        }


def _scene_probe(world: SpriteWorld | None) -> dict[str, Any] | None:
    """Raw scene coords for calibrating the frame: gnomes, walk-sprite dims,
    gardens, and the self-candidate (gnome nearest the 320x200 viewport center)."""
    if world is None:
        return None
    gnomes = []  # objects 1000..1099 -> (id, x, y, label)
    gardens = []  # objects 4000..4999 -> (id, x, y)
    for obj in world.objects.values():
        oid = obj.object_id
        if 1000 <= oid < 1100:
            sp = world.sprite_for(obj)
            gnomes.append([oid, int(obj.x), int(obj.y), (sp.label if sp else "")])
        elif 4000 <= oid < 5000:
            gardens.append([oid, int(obj.x), int(obj.y)])
    walk = None
    for sp in world.sprites.values():
        if sp.label in ("heartleaf main walkability", "heartleaf home walkability"):
            walk = {"id": sp.sprite_id, "w": sp.width, "h": sp.height, "label": sp.label}
            break
    # self = gnome nearest viewport center (320/2, 200/2) by foot ~ (x,y)
    self_cand = None
    if gnomes:
        cx, cy = 160, 100
        best = min(gnomes, key=lambda g: (g[1] - cx) ** 2 + (g[2] - cy) ** 2)
        self_cand = {"index": best[0] - 1000, "x": best[1], "y": best[2], "label": best[3]}
    return {"gnomes": gnomes, "walk_sprite": walk, "gardens": gardens[:5],
            "n_gardens": len(gardens), "self_candidate": self_cand}


def _in_view_count(belief: Belief) -> int:
    """Other gnomes within Cady's viewport box (would hear a chat) — mirrors the
    invite audience test, for social diagnosis."""
    if belief.self_xy is None:
        return 0
    sx, sy = belief.self_xy
    return sum(
        1
        for g in belief.gnomes
        if g.index != belief.own_house_index
        and abs(g.pos[0] - sx) <= INVITE_VIEW_HALF_W
        and abs(g.pos[1] - sy) <= INVITE_VIEW_HALF_H
    )


def _diagnostics_enabled() -> bool:
    return os.getenv("CADY_DIAG", "1").strip().lower() not in {"0", "false", "off", "no"}


def _point(point: tuple[int, int] | None) -> list[int] | None:
    return None if point is None else [point[0], point[1]]


def _map_object_payload(obj: Any) -> dict[str, int] | None:
    if obj is None:
        return None
    return {"x": int(obj.x), "y": int(obj.y), "sprite_id": int(obj.sprite_id)}


def _garden_marker_count(world: SpriteWorld | None) -> int:
    if world is None:
        return 0
    count = 0
    for obj in world.objects.values():
        sprite = world.sprite_for(obj)
        if sprite is not None and sprite.label == GARDEN_MARKER_LABEL:
            count += 1
    return count


def _grid_dims(map_context: str) -> list[int] | None:
    if map_context == "home":
        return [mapdata.HOME_GRID_W, mapdata.HOME_GRID_H]
    if map_context == "main":
        return [mapdata.GRID_W, mapdata.GRID_H]
    return None


_DEFAULT_DECIDE = build_decide()


__all__ = ["build_decide", "decide"]
