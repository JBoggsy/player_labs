"""Sprite bridge decide adapter for Cady."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
import sys
from typing import Any

from cady import mapdata
from cady.config import DIAG_EVERY_TICKS
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
    """Temporary frame diagnostics for calibrating Cady's live coordinate frames."""

    def __init__(self) -> None:
        self._world: SpriteWorld | None = None
        self._frame: int | None = None
        self._logged_ready = False
        self._last_context: str | None = None

    def capture_world(self, world: SpriteWorld, frame: int) -> None:
        self._world = world
        self._frame = frame

    def on_step_complete(self, step: StepContext[Belief, ActionState, Intent, Command]) -> None:
        belief = step.belief
        context = belief.map_context
        first_ready = belief.self_xy is not None and not self._logged_ready
        context_changed = self._last_context is not None and context != self._last_context
        cadence = step.tick % DIAG_EVERY_TICKS == 0

        if first_ready:
            self._logged_ready = True
        self._last_context = context

        if not (first_ready or context_changed or cadence):
            return

        print("CADY_DIAG " + json.dumps(self._payload(step), separators=(",", ":"), sort_keys=True), file=sys.stderr)

    def _payload(self, step: StepContext[Belief, ActionState, Intent, Command]) -> dict[str, Any]:
        world = self._world
        map_obj = None if world is None else world.objects.get(MAP_OBJECT_ID)
        intent = step.intent
        return {
            "tick": step.tick,
            "frame": self._frame,
            "map_context": step.belief.map_context,
            "self_xy": _point(step.belief.self_xy),
            "map_object": _map_object_payload(map_obj),
            "camera": None if map_obj is None else [-map_obj.x, -map_obj.y],
            "mode": step.active_mode_name,
            "intent": intent.kind,
            "intent_point": _point(intent.point),
            "held_mask": step.command.held_mask,
            "inventory_count": step.belief.inventory_count,
            "garden_marker_count": _garden_marker_count(world),
            "grid": _grid_dims(step.belief.map_context),
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
