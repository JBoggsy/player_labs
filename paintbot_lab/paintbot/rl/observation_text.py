"""Serialize semantic Sprite-v1 observations for a language-model policy."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable

from actions import action_text


NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?")
HUMAN_VISUAL_LABELS = frozenset({"fog"})
HUMAN_VISUAL_LABEL_PREFIXES = ("splatter ", "hit splat ", "damage pop ")
MAX_TEMPORAL_CHANGES_PER_TICK = 4


@dataclass(frozen=True)
class EntitySnapshot:
    object_id: int
    label: str
    x: int
    y: int
    z: int
    layer: int
    width: int
    height: int

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EntitySnapshot:
        return cls(**{field: value[field] for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class ObservationSnapshot:
    game_version: str
    frame: int
    map_width: int
    map_height: int
    entities: tuple[EntitySnapshot, ...]
    source: str | None = None
    tick: int | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ObservationSnapshot:
        return cls(
            game_version=str(value["game_version"]),
            frame=int(value["frame"]),
            map_width=int(value["map_width"]),
            map_height=int(value["map_height"]),
            entities=tuple(EntitySnapshot.from_dict(entity) for entity in value["entities"]),
            source=value.get("source"),
            tick=int(value["tick"]) if value.get("tick") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def split_label_numbers(label: str) -> tuple[str, tuple[str, ...]]:
    """Replace numeric spans with ordered placeholders and return their values."""
    values: list[str] = []

    def replace(match: re.Match[str]) -> str:
        placeholder = f"{{number_{len(values)}}}"
        values.append(match.group())
        return placeholder

    return NUMBER_PATTERN.sub(replace, label), tuple(values)


def is_bot_semantic_label(label: str) -> bool:
    """Keep labels a sprites-off bot receives, including unknown future labels."""
    return label not in HUMAN_VISUAL_LABELS and not label.startswith(
        HUMAN_VISUAL_LABEL_PREFIXES
    )


def bot_semantic_observation(snapshot: ObservationSnapshot) -> ObservationSnapshot:
    """Remove only renderer families explicitly excluded by Sprite-v1 bots."""
    return replace(
        snapshot,
        entities=tuple(
            entity for entity in snapshot.entities if is_bot_semantic_label(entity.label)
        ),
    )


def serialize_observation(
    snapshot: ObservationSnapshot, *, include_human_visuals: bool = False
) -> str:
    """Render one deterministic, map-scale-normalized observation as text."""
    if snapshot.map_width <= 0 or snapshot.map_height <= 0:
        raise ValueError("map dimensions must be positive")
    if not include_human_visuals:
        snapshot = bot_semantic_observation(snapshot)

    resolved = [(_center(entity), entity) for entity in snapshot.entities]
    self_center = next(
        (center for center, entity in resolved if entity.label.startswith("self ")),
        None,
    )
    resolved.sort(key=lambda item: _entity_sort_key(item[0], item[1], self_center))

    lines = [
        "observation"
        f" game_version={json.dumps(snapshot.game_version)}"
        f" frame={snapshot.frame}"
        f" map_width={snapshot.map_width}"
        f" map_height={snapshot.map_height}"
    ]
    for center, entity in resolved:
        semantic_label, label_values = split_label_numbers(entity.label)
        fields = [
            "entity",
            f"semantic={json.dumps(semantic_label, ensure_ascii=False)}",
        ]
        if label_values:
            fields.append(f"label_numbers={json.dumps(label_values)}")
        fields.extend(
            (
                f"x_permille={_permille(center[0], snapshot.map_width)}",
                f"y_permille={_permille(center[1], snapshot.map_height)}",
                f"width_permille={_permille(entity.width, snapshot.map_width)}",
                f"height_permille={_permille(entity.height, snapshot.map_height)}",
                f"z={entity.z}",
                f"layer={entity.layer}",
            )
        )
        if self_center is not None:
            fields.extend(
                (
                    f"dx_permille={_permille(center[0] - self_center[0], snapshot.map_width)}",
                    f"dy_permille={_permille(center[1] - self_center[1], snapshot.map_height)}",
                )
            )
        lines.append(" ".join(fields))
    return "\n".join(lines)


def temporal_delta(
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    *,
    action_mask: int,
    target_tick: int,
) -> dict[str, Any]:
    """Build one compact, causal entity-change record for temporal context."""
    before = bot_semantic_observation(before)
    after = bot_semantic_observation(after)
    previous_entities = {entity.object_id: entity for entity in before.entities}
    current_entities = {entity.object_id: entity for entity in after.entities}
    changes = []
    for object_id in sorted(previous_entities.keys() | current_entities.keys()):
        previous = previous_entities.get(object_id)
        current = current_entities.get(object_id)
        if current is None:
            changes.append(_temporal_entity("removed", previous, None, after))
        elif previous is None:
            changes.append(_temporal_entity("appeared", None, current, after))
        elif current != previous or current.label.startswith("self "):
            changes.append(_temporal_entity("updated", previous, current, after))
    changes.sort(key=_temporal_priority)
    changes = changes[:MAX_TEMPORAL_CHANGES_PER_TICK]
    for change in changes:
        change.pop("_distance_squared", None)
        change.pop("_label_changed", None)
    return {
        "tick_offset": int(after.tick or 0) - target_tick,
        "action_mask": action_mask,
        "changes": changes,
    }


def serialize_temporal_history(history: Iterable[dict[str, Any]]) -> str:
    lines = ["history"]
    for step in history:
        lines.append(
            f"history_step tick_offset={int(step['tick_offset'])} "
            f"action={action_text(int(step['action_mask']))}"
        )
        for change in step["changes"]:
            fields = [
                "history_entity",
                f"status={change['status']}",
                f"semantic={json.dumps(change['semantic'], ensure_ascii=False)}",
            ]
            if change.get("label_numbers"):
                fields.append(f"label_numbers={json.dumps(change['label_numbers'])}")
            for name in (
                "x_permille",
                "y_permille",
                "dx_permille",
                "dy_permille",
            ):
                if name in change:
                    fields.append(f"{name}={change[name]}")
            lines.append(" ".join(fields))
    return "\n".join(lines)


def self_center(snapshot: ObservationSnapshot) -> tuple[float, float]:
    """Return the current agent center in map pixels."""
    for entity in snapshot.entities:
        if entity.label.startswith("self "):
            return _center(entity)
    raise ValueError("observation has no self entity")


def snapshots_from_jsonl(lines: Iterable[str]) -> Iterable[ObservationSnapshot]:
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            yield ObservationSnapshot.from_dict(json.loads(line))
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid snapshot on line {line_number}: {error}") from error


def _center(entity: EntitySnapshot) -> tuple[float, float]:
    return entity.x + entity.width / 2, entity.y + entity.height / 2


def _entity_sort_key(
    center: tuple[float, float],
    entity: EntitySnapshot,
    self_center: tuple[float, float] | None,
) -> tuple[object, ...]:
    is_not_self = not entity.label.startswith("self ")
    if self_center is None:
        distance_squared = 0.0
    else:
        distance_squared = (center[0] - self_center[0]) ** 2 + (
            center[1] - self_center[1]
        ) ** 2
    semantic_label, _ = split_label_numbers(entity.label)
    return is_not_self, distance_squared, semantic_label, entity.label, center, entity.object_id


def _temporal_entity(
    status: str,
    previous: EntitySnapshot | None,
    current: EntitySnapshot | None,
    snapshot: ObservationSnapshot,
) -> dict[str, Any]:
    entity = current or previous
    assert entity is not None
    semantic, numbers = split_label_numbers(entity.label)
    result: dict[str, Any] = {"status": status, "semantic": semantic}
    if numbers:
        result["label_numbers"] = numbers
    if current is not None:
        center = _center(current)
        result.update(
            x_permille=_permille(center[0], snapshot.map_width),
            y_permille=_permille(center[1], snapshot.map_height),
            z=current.z,
            layer=current.layer,
        )
        if previous is not None:
            previous_center = _center(previous)
            result.update(
                dx_permille=_permille(center[0] - previous_center[0], snapshot.map_width),
                dy_permille=_permille(center[1] - previous_center[1], snapshot.map_height),
            )
    self_position = next(
        (_center(item) for item in snapshot.entities if item.label.startswith("self ")),
        None,
    )
    entity_position = _center(current or previous)
    result["_distance_squared"] = (
        0
        if self_position is None
        else (entity_position[0] - self_position[0]) ** 2
        + (entity_position[1] - self_position[1]) ** 2
    )
    result["_label_changed"] = previous is None or current is None or previous.label != current.label
    return result


def _temporal_priority(change: dict[str, Any]) -> tuple[object, ...]:
    semantic = str(change["semantic"])
    if semantic.startswith("self "):
        kind = 0
    elif semantic.startswith("own aim "):
        kind = 1
    elif semantic.startswith("player "):
        kind = 2
    elif "flag" in semantic or "heart" in semantic:
        kind = 3
    elif change["_label_changed"]:
        kind = 4
    else:
        kind = 5
    return kind, change["_distance_squared"], semantic


def _permille(value: float, extent: int) -> int:
    return round(1000 * value / extent)
