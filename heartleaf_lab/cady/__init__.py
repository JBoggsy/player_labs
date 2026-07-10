"""cady — Heartleaf's first player policy (a deterministic cyborg Player-SDK policy).

Rides the SDK's SpriteV1 bridge (``players.player_sdk.run_sprite_bridge``): the bridge
owns transport + raw decode into a ``SpriteWorld``; ``cady`` is pure game logic
(perception -> belief -> clock-driven Gather/Host/Idle modes -> Button-mask action),
glued to the bridge by ``cady.decide``.

Design:  heartleaf_lab/docs/designs/cady-player-design.md
Plan:    heartleaf_lab/docs/plans/2026-07-06-cady-player.md
"""
