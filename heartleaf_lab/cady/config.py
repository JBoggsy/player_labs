"""Tunable constants for Cady's deterministic v1 policy."""

GATHER_CUTOFF_MINUTES = 540
"""Stop gathering at 5:00 PM, nine hours after Heartleaf's 8:00 AM start."""

WAYPOINT_RADIUS = 6
"""Distance in pixels at which a cached navigation waypoint counts as reached."""

WAYPOINT_RADIUS_SQ = WAYPOINT_RADIUS * WAYPOINT_RADIUS
"""Squared waypoint-arrival radius for cheap tests."""

HARVEST_RADIUS = 40
"""Distance in pixels from a garden rect at which an A press can harvest.

Matches the game's ``InteractionRadius`` (heartleaf ``common.nim``): the server
harvests when the player's foot is within this distance of the garden rect and A
is pressed."""

MARKER_SIGHT_RADIUS = 60
"""Distance in pixels within which a visible garden marker counts as "food to
harvest here." A bit larger than HARVEST_RADIUS so we don't skip a real garden
whose marker position sits at the edge of range; the game's own 40px check still
gates whether the A press actually collects."""

A_PRESS_PERIOD = 4
"""Frames to wait (releasing A) after each A press before pressing again. The
game acts on a fresh A *edge*; we press once, then observe for this many frames
whether the result we want happened (a pickup, a door transition) before pressing
again — a deliberate press-and-verify cadence, never a per-frame button-spam. A
successful action lands within 1-2 frames, so the mode stops requesting A before
the next press fires."""

MAX_GATHER_TICKS = 12
"""Frames to keep pressing A at one garden before giving up and moving on. One
successful press harvests all of a garden's food, so this only needs to cover
the 1-2 frame perception lag for the pickup to register; if nothing is collected
in this window the garden is empty (already harvested) or out of true range."""

EXIT_RADIUS = 40
"""Distance in pixels from the home exit rect at which an A press can leave."""

HOME_RADIUS = 8  # CALIBRATION: how close to home_anchor counts as seated; TODO(calibrate)
HOME_RADIUS_SQ = HOME_RADIUS * HOME_RADIUS
"""Squared home-arrival radius used by HostMode."""

DIAG_EVERY_TICKS = 24
"""CADY_DIAG cadence while temporary frame diagnostics are enabled."""
