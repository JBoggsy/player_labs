"""Tunable DumbBot weights. Defaults are the original DumbBot / MIT-port values."""

PROXIMITY_DEPTHS = 10

# Power size = a*n^2 + b*n + c, n = supply centres owned.
SIZE_SQUARE = 1.0
SIZE_LINEAR = 4.0
SIZE_CONSTANT = 16.0

# "uno": unowned centres count as one pseudo-power sized by how many remain (DAIDE UNO).
# "zero": the MIT port's behaviour (neutral centres have no attack value).
NEUTRAL_SIZE_MODE = "uno"

SPRING_ATTACK_WEIGHT = 700
SPRING_DEFENSE_WEIGHT = 300
FALL_ATTACK_WEIGHT = 600
FALL_DEFENSE_WEIGHT = 400

SPRING_PROXIMITY_WEIGHTS = [100, 1000, 30, 10, 6, 5, 4, 3, 2, 1]
FALL_PROXIMITY_WEIGHTS = [1000, 100, 30, 10, 6, 5, 4, 3, 2, 1]

STRENGTH_WEIGHT = 1000
COMPETITION_WEIGHT = 1000
BUILD_DEFENSE_WEIGHT = 1000

ALTERNATIVE_DIFF_MODIFIER = 5
PLAY_ALTERNATIVE = 0.5

# --- SearchBot (search.py) ---
SEARCH_OPPONENT_SAMPLES = 16
SEARCH_SEEDS = 12
SEARCH_PASSES = 6
# Wall-clock search budget per movement phase. Hosted phases are 1 minute and pods get
# ~0.25 CPU, so the hosted default is generous; the local arena passes 8 s via env.
SEARCH_TIME_BUDGET_S = float(__import__("os").environ.get("WEBDIP_SEARCH_BUDGET_S", "20"))
SEARCH_SC_WEIGHT = 10.0
SEARCH_POS_WEIGHT = 1.0
SEARCH_DISLODGED_WEIGHT = 3.0
SEARCH_PAIRS = 1  # joint move+support alternatives
SEARCH_CONVOYS = 1  # joint convoyed-move + convoy alternatives
# Opponent model: "dumbbot" (always DumbBot samples) or "adaptive" (per-power Bayesian mix of
# DumbBot vs uniform-random legal orders, learned from each power's past orders).
OPP_MODEL = "adaptive"
OPP_PRIOR_LOGODDS = 0.0
OPP_LOGODDS_CLIP = 8.0
# Search objective: "sc" (our projected centres) or "share" (projected SC^2 share x34).
SEARCH_OBJECTIVE = "sc"
SEARCH_FAST_ADJ = 1  # use fastadj (no-convoy turns); package fallback otherwise
