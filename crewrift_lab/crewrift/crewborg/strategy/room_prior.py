"""Empirical room-density prior for the imposter's ready-state search.

``data/room_density.json`` (schema ``crewborg-room-density/v1``, built by
``crewrift_lab/tools/imposter_movement/room_density.py`` from 247 real episodes)
carries per-room live-crew density plus each room's ``share`` of all live crew,
in 600-tick Playing bands. This module loads it once and answers "how likely is
a live crewmate to be in this room *around this point of the game*" as a
band-normalized 0..1 weight — the tie-breaker Search's PICK_ROOM blends with
live occupancy evidence (see ``modes/search.py``).

Failure-tolerant by design (mirrors ``strategy/suspicion.py:_load_weights``): a
missing/malformed file or an unknown room simply disables the prior (weight 0.0)
— never a crash, and Search degrades to its live-evidence-only scoring.
"""

from __future__ import annotations

import importlib.resources
import json
import os
from pathlib import Path

DENSITY_PACKAGE = "crewrift.crewborg.data"
DENSITY_RESOURCE = "room_density.json"
DENSITY_SCHEMA = "crewborg-room-density/v1"


def _load_density() -> dict | None:
    """The vendored density table, or ``None`` (→ prior disabled). Never raises.

    ``CREWBORG_ROOM_DENSITY`` overrides the vendored file with a path, or
    disables the prior entirely when set to ``0``.
    """

    override = os.environ.get("CREWBORG_ROOM_DENSITY", "").strip()
    if override == "0":
        return None
    try:
        if override:
            data = json.loads(Path(override).read_text())
        else:
            resource = importlib.resources.files(DENSITY_PACKAGE).joinpath(DENSITY_RESOURCE)
            data = json.loads(resource.read_text())
        if data.get("schema") != DENSITY_SCHEMA:
            return None
        return _normalize(data)
    except Exception:  # missing asset / bad JSON ⇒ prior disabled, never a crash
        return None


def _normalize(data: dict) -> dict | None:
    """Precompute per-band max-normalized shares: ``share[room][band] / max share
    over rooms in that band`` — the same 0..1 scaling PICK_ROOM applies to live
    occupancy, so the blend weights compare directly. ``None`` on a shape we
    don't understand (treated as a bad file)."""

    bucket_ticks = int(data["bucket_ticks"])
    share: dict[str, list[float]] = data["share"]
    n_bands = len(data["bucket_start_ticks"])
    if bucket_ticks <= 0 or n_bands <= 0 or not share:
        return None
    band_max = [max(shares[band] for shares in share.values()) or 1.0 for band in range(n_bands)]
    normalized = {
        room: [shares[band] / band_max[band] for band in range(n_bands)] for room, shares in share.items()
    }
    return {"bucket_ticks": bucket_ticks, "n_bands": n_bands, "share_norm": normalized}


_DENSITY: dict | None = _load_density()


def set_density(density: dict | None) -> None:
    """Test/ops hook: pin the prior table (``None`` ⇒ prior disabled).

    Accepts the raw ``crewborg-room-density/v1`` dict (normalized here).
    """

    global _DENSITY
    _DENSITY = _normalize(density) if density is not None else None


def room_share_prior(room_name: str, tick: int) -> float:
    """The room's band-normalized empirical crew share in [0, 1] at ``tick``.

    Band = absolute tick // ``bucket_ticks``, clamped to the last band (long
    games keep using the late-game distribution). 0.0 when the prior is
    disabled/unloaded or the room is not in the table.
    """

    if _DENSITY is None:
        return 0.0
    shares = _DENSITY["share_norm"].get(room_name)
    if shares is None:
        return 0.0
    band = min(max(tick, 0) // _DENSITY["bucket_ticks"], _DENSITY["n_bands"] - 1)
    return shares[band]
