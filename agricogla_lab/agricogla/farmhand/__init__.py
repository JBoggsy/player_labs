"""farmhand — agricogla (cogweb.player.v1) player on the Player SDK.

The decision logic is a PARAMS-weighted scorer (``brain.Brain``); the wire
envelope is handled by the SDK's ``run_cogweb_bridge``. Build variants by baking a
candidate params.json (or setting AGRICOGLA_PARAMS) — that's the beam-search surface.
"""

from agricogla.farmhand.brain import Brain
from agricogla.farmhand.params import DEFAULT_PARAMS, load_params

__all__ = ["Brain", "DEFAULT_PARAMS", "load_params"]
