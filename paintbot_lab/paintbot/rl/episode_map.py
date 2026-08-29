"""Episode-level storage for the static Sprite-v1 walkability raster."""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Any

import cramjam
import numpy as np


WALKABILITY_LABEL = "walkability map"


@dataclass(frozen=True)
class EpisodeMap:
    width: int
    height: int
    packed_walkability: bytes
    map_hash: str

    @classmethod
    def from_mask(cls, mask: np.ndarray) -> EpisodeMap:
        mask = np.asarray(mask, dtype=np.bool_)
        if mask.ndim != 2 or min(mask.shape) <= 0:
            raise ValueError("walkability mask must be a non-empty 2D array")
        height, width = mask.shape
        packed = np.packbits(mask.reshape(-1), bitorder="little").tobytes()
        digest = hashlib.sha256(
            width.to_bytes(4, "little") + height.to_bytes(4, "little") + packed
        ).hexdigest()
        return cls(width, height, packed, digest)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EpisodeMap:
        item = cls(
            width=int(value["width"]),
            height=int(value["height"]),
            packed_walkability=base64.b64decode(value["packed_walkability"]),
            map_hash=str(value["map_hash"]),
        )
        if item.map_hash != cls.from_mask(item.mask()).map_hash:
            raise ValueError("episode map hash does not match its walkability data")
        return item

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_hash": self.map_hash,
            "width": self.width,
            "height": self.height,
            "packed_walkability": base64.b64encode(self.packed_walkability).decode(),
        }

    def mask(self) -> np.ndarray:
        bits = np.unpackbits(
            np.frombuffer(self.packed_walkability, dtype=np.uint8), bitorder="little"
        )
        return bits[: self.width * self.height].reshape(self.height, self.width).astype(bool)


def decode_walkability_sprite(sprite: Any) -> EpisodeMap:
    """Decode a walkability SpriteDef whose raw RGBA alpha is the collision mask."""
    if sprite.label != WALKABILITY_LABEL:
        raise ValueError(f"expected {WALKABILITY_LABEL!r}, got {sprite.label!r}")
    rgba = bytes(cramjam.snappy.decompress_raw(sprite.data))
    expected = sprite.width * sprite.height * 4
    if len(rgba) != expected:
        raise ValueError(f"walkability sprite has {len(rgba)} bytes; expected {expected}")
    alpha = np.frombuffer(rgba, dtype=np.uint8).reshape(sprite.height, sprite.width, 4)[..., 3]
    return EpisodeMap.from_mask(alpha != 0)


def episode_map_from_world(world: Any) -> EpisodeMap | None:
    for sprite in world.sprites.values():
        if sprite.label == WALKABILITY_LABEL and sprite.data:
            return decode_walkability_sprite(sprite)
    return None
