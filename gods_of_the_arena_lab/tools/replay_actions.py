#!/usr/bin/env python3
"""Decode GotA action tapes without the simulator; acceptance is unknown (null).

Supports the verified Flatty64 layout: container 1, payload 5, game 33/40/41.
Outputs meta/action/cpu JSONL. This reads recorded hashes but cannot verify them.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import gzip
import io
import json
from pathlib import Path
import struct
import sys

MAX_BYTES = 64 * 1024 * 1024


class ReplayError(ValueError):
    """Malformed or unsupported replay input."""


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, size: int) -> bytes:
        if size < 0 or size > len(self.data) - self.offset:
            raise ReplayError(f'truncated or invalid field at byte {self.offset}')
        start = self.offset
        self.offset += size
        return self.data[start:self.offset]

    def unpack(self, fmt: str) -> tuple:
        return struct.unpack('<' + fmt, self.take(struct.calcsize('<' + fmt)))

    def count(self, minimum_size: int = 1) -> int:
        count, = self.unpack('q')
        if count < 0 or count > (len(self.data) - self.offset) // minimum_size:
            raise ReplayError(f'invalid sequence length at byte {self.offset - 8}')
        return count

    def string(self) -> str:
        return self.take(self.count()).decode('utf-8')


@dataclass
class ReplayTape:
    meta: dict
    actions: list[dict]
    hashes: list[int]
    cpu: list[dict]


def decode(data: bytes) -> ReplayTape:
    """Decode and structurally validate a raw or gzip-wrapped tape."""
    if len(data) > MAX_BYTES:
        raise ReplayError('replay exceeds 64 MiB')
    if data.startswith(b'\x1f\x8b'):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as source:
            data = source.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ReplayError('decompressed replay exceeds 64 MiB')
    r = Reader(data)
    if r.take(15) != b'POLYWORLDREPLAY':
        raise ReplayError('not a POLYWORLDREPLAY file')
    container, game_version, name_len = r.unpack('HHH')
    name = r.take(name_len).decode('utf-8')
    if container != 1 or name != 'gods_of_the_arena':
        raise ReplayError('unsupported replay container or game')
    payload, inner_version, created = r.unpack('HHq')
    if payload != 5 or inner_version != game_version or game_version not in (33, 40, 41):
        raise ReplayError(f'unsupported replay layout: {payload=}, {game_version=}')
    seed, map_hash, tick_rate, grid, spawn, maximum = r.unpack('iQHHII')
    heroes = []
    for slot in range(r.count(8)):
        hero_id, team, team_slot, lane, hero_class = r.unpack('iBBBB')
        heroes.append(dict(slot=slot, hero_id=hero_id, team=team, team_slot=team_slot,
                           lane=lane, **{'class': hero_class}))
    ids = {h['hero_id']: h['slot'] for h in heroes}
    if not heroes or len(ids) != len(heroes):
        raise ReplayError('empty or duplicate hero roster')
    players = [r.string() for _ in range(r.count(8))]
    config_seed, max_ticks, interval, player_slot, days = r.unpack('iiiii')
    map_size, map_seed, crossings, roads = r.unpack('qqqq')
    controls = r.unpack('9f')
    touches, = r.unpack('B')
    if (config_seed, max_ticks, interval, map_size) != (seed, maximum, spawn, grid):
        raise ReplayError('config/setup mismatch')
    actions = []
    previous_tick = 0
    for index in range(r.count(20)):
        tick, hero_id, kind, first, second = r.unpack('IiB3xii')
        if tick < previous_tick or tick > maximum or hero_id not in ids or not 1 <= kind <= 14:
            raise ReplayError(f'invalid action {index}')
        actions.append(dict(type='action', tick=tick, slot=ids[hero_id], hero_id=hero_id,
                            kind=kind, args=[first, second], accepted=None, action_index=index))
        previous_tick = tick
    hashes = [r.unpack('Q')[0] for _ in range(r.count(8))]
    if len(hashes) > maximum or (actions and actions[-1]['tick'] > len(hashes)):
        raise ReplayError('actions/hashes exceed recorded duration')
    metric_rate, metric_interval = r.unpack('ii')
    cpu = []
    for _ in range(r.count(12)):
        tick, = r.unpack('i')
        values = [r.unpack('i')[0] for _ in range(r.count(4))]
        cpu.append(dict(type='cpu', tick=tick, final=False, values=values))
    final = [r.unpack('i')[0] for _ in range(r.count(4))]
    cpu.append(dict(type='cpu', tick=len(hashes), final=True, values=final))
    if r.offset != len(data):
        raise ReplayError(f'{len(data) - r.offset} trailing bytes after replay')
    meta = dict(type='meta', tick=0, game=name, game_version=game_version,
                payload_version=payload, created_unix_ms=created, seed=seed,
                map_hash=map_hash, tick_rate=tick_rate, grid_tiles=grid,
                spawn_interval_ticks=spawn, maximum_ticks=maximum, ticks_recorded=len(hashes),
                heroes=heroes, players=players, metric_tick_rate=metric_rate,
                metric_interval=metric_interval, hash_verified=False,
                acceptance_available=False, config=dict(player_slot=player_slot, day_count=days,
                map_seed=map_seed, lake_crossings=crossings, jungle_roads=roads,
                controls=controls, camps_touch_roads=bool(touches)))
    return ReplayTape(meta, actions, hashes, cpu)


def read_replay(path: Path) -> ReplayTape:
    with path.open('rb') as source:
        return decode(source.read(MAX_BYTES + 1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('replay', type=Path)
    parser.add_argument('--out', type=Path, help='JSONL output (default stdout)')
    args = parser.parse_args()
    tape = read_replay(args.replay)
    output = args.out.open('w') if args.out else sys.stdout
    try:
        for row in (tape.meta, *tape.actions, *tape.cpu):
            print(json.dumps(row, separators=(',', ':')), file=output)
    finally:
        if args.out:
            output.close()
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, EOFError) as error:
        print(f'replay_actions: {error}', file=sys.stderr)
        raise SystemExit(1)
