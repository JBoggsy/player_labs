#!/usr/bin/env python3
"""Sprite-v1 inference entrypoint for a trained semantic policy checkpoint."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import torch
from players.player_sdk import env_ws_url, run_sprite_bridge

from actions import ActionDecoder, action_text
from capture_wire_observations import snapshot_world
from episode_map import episode_map_from_world
from modeling import load_policy
from observation_text import self_center, serialize_observation


class PolicyRuntime:
    def __init__(self, checkpoint: Path) -> None:
        self.device = _device()
        self.tokenizer, self.model = load_policy(checkpoint, device=self.device)
        self.decoder = ActionDecoder()
        self.map_cache = None
        self.trace = os.environ.get("PAINTBOT_RL_TRACE", "0") == "1"
        self.game_version = os.environ.get("PAINTBOT_GAME_VERSION", "unknown")
        self.include_spatial_semantics = (
            os.environ.get("PAINTBOT_SPATIAL_SEMANTICS", "0") == "1"
        )

    def decide(self, world, _context) -> int:
        started = time.perf_counter()
        if self.map_cache is None:
            episode_map = episode_map_from_world(world)
            if episode_map is None:
                return 0
            map_tensor = torch.from_numpy(episode_map.mask()).to(self.device, dtype=torch.float32)
            with torch.no_grad():
                self.map_cache = self.model.map_encoder.encode_static(map_tensor)

        try:
            snapshot = snapshot_world(
                world, game_version=self.game_version, source="live-sprite-v1"
            )
            position = self_center(snapshot)
        except ValueError:
            return 0
        prompt = (
            serialize_observation(
                snapshot,
                include_spatial_semantics=self.include_spatial_semantics,
            )
            + "\nprevious_action "
            + action_text(self.decoder.previous_mask)
            + "\naction"
        )
        prompt_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
        if self.model.action_encoding == "events":
            tokens = self.model.greedy_event_action(
                self.tokenizer,
                prompt_ids,
                self.map_cache,
                position,
                self.decoder.previous_mask,
            )
            decoded = self.decoder.decode_events(tokens)
        else:
            tokens = self.model.greedy_action(
                self.tokenizer, prompt_ids, self.map_cache, position
            )
            decoded = self.decoder.decode(tokens)
        if self.trace:
            print(
                json.dumps(
                    {
                        "event": "rl_action",
                        "frame": world.frame,
                        "tokens": tokens,
                        "mask": decoded.mask,
                        "pressed_mask": decoded.pressed_mask,
                        "released_mask": decoded.released_mask,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    }
                ),
                file=sys.stderr,
                flush=True,
            )
        return decoded.mask


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def main() -> int:
    checkpoint = os.environ.get("PAINTBOT_RL_CHECKPOINT")
    if not checkpoint:
        raise SystemExit("PAINTBOT_RL_CHECKPOINT is required")
    runtime = PolicyRuntime(Path(checkpoint))
    # The bridge is async-only; policy inference itself intentionally remains synchronous.
    asyncio.run(run_sprite_bridge(env_ws_url(), runtime.decide, max_size=None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
