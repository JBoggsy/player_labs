"""Tunable constants for Cady's deterministic v1 policy."""

GATHER_CUTOFF_MINUTES = 540
"""Stop gathering at 5:00 PM, nine hours after Heartleaf's 8:00 AM start."""

WAYPOINT_RADIUS = 6
"""Distance in pixels at which a cached navigation waypoint counts as reached."""

WAYPOINT_RADIUS_SQ = WAYPOINT_RADIUS * WAYPOINT_RADIUS
"""Squared waypoint-arrival radius for cheap tests."""

HARVEST_RADIUS = 40
"""Distance in pixels from a garden rect at which an A press can harvest."""

EXIT_RADIUS = 40
"""Distance in pixels from the home exit rect at which an A press can leave."""

HOME_RADIUS = 8  # CALIBRATION: how close to home_anchor counts as seated; TODO(calibrate)
HOME_RADIUS_SQ = HOME_RADIUS * HOME_RADIUS
"""Squared home-arrival radius used by HostMode."""

DIAG_EVERY_TICKS = 24
"""CADY_DIAG cadence while temporary frame diagnostics are enabled."""
