"""Tunable constants for Cady's deterministic v1 policy."""

GATHER_CUTOFF_MINUTES = 540
"""Stop gathering at 5:00 PM, nine hours after Heartleaf's 8:00 AM start."""

HOME_RADIUS = 8  # CALIBRATION: how close to home_anchor counts as seated; TODO(calibrate)
HOME_RADIUS_SQ = HOME_RADIUS * HOME_RADIUS
"""Squared home-arrival radius used by HostMode."""
