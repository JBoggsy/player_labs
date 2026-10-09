"""Live tunables for DumbBot, search components and Nash; policy overrides use these names."""

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

# --- SearchBot components (ownership and extension points: README.md) ---
SEARCH_OPPONENT_SAMPLES = 16
SEARCH_SEEDS = 12
SEARCH_PASSES = 6
# Shared wall-clock budget for movement, lookahead and Nash search.
# WEBDIP_SEARCH_BUDGET_S supplies the default at import; policy overrides can replace it.
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
SEARCH_FAST_ADJ = 1  # evaluation.py: fastadj after conversion; 0 forces package scoring
SEARCH_RESTARTS = 1  # championship-1: restarts=3 versions lost to 1 (optimizer's curse)
# Spring re-ranking of the top ascent results by a simulated DumbBot autumn (0 = off).
SEARCH_ROLLOUT = 0
SEARCH_ROLLOUT_POOL = 3
SEARCH_ROLLOUT_SAMPLES = 8
SEARCH_ROLLOUT_STATIC_WEIGHT = 0.5
# Winter builds/disbands chosen by a reduced search of the following spring (0 = DumbBot).
SEARCH_BUILDS = 0
SEARCH_BUILD_CANDIDATES = 12
# Opponent sophistication: 0 = DumbBot samples; 1 = each DumbBot sample improved by one pass
# of that power's own best response; 2 = best response to level-1 plans.
OPP_MODEL_LEVEL = 0
# Static evaluation of a search outcome: "projected" (centres held if it were autumn) or
# "learned" (valuefn.py ridge model: predicted centres two years ahead).
SEARCH_EVAL = "projected"
SEARCH_LEARNED_WEIGHT = 1.0  # with SEARCH_EVAL="learned": blend of predicted vs projected centres
SEARCH_RISK = 0.0  # 0 = mean over opponent samples; 1 = worst case
# NashBot (nash.py): regret matching over candidate plans for all powers.
NASH_CANDIDATES = 6
NASH_ITERS = 60
NASH_EVAL_SAMPLES = 24
# Opponent-belief likelihood: "competent" (sensible orders count as competent) or "dumbbot"
# (only DumbBot-matching orders do; mislabels strong non-DumbBot players as random).
OPP_LIKELIHOOD = "competent"
# With OPP_MODEL_LEVEL=1: probability that a given opponent sample is the improved (level-1)
# plan rather than the raw DumbBot plan (a mixed opponent model).
OPP_LEVEL1_SHARE = 1.0
SEARCH_TRIPLES = 0  # joint move + two supports alternatives
SEARCH_CONVOY_APPROX = 1  # evaluate convoys inside fastadj (approximation) instead of the package
# Mixed strategy over the top plans: temperature (0 = always the best plan) and pool size.
SEARCH_SOFTMAX_T = 0.0
SEARCH_SOFTMAX_POOL = 4
# Implicit diplomacy (no-press): hostility memory from public history.
DIPLO = 0
DIPLO_DECAY = 0.7      # per movement phase
DIPLO_HOSTILE = 1.0    # decayed attacks at/above this = hostile
DIPLO_GRUDGE = 0.5     # extra centre-value for taking a hostile power's centre
DIPLO_PEACE = 0.6      # centre-value discount for taking a peaceful power's centre
DIPLO_STAB_YEAR = 1905 # peace discount applies before this year

# --- Press player (press/): LLM agent steering SearchBot; see press/player.py ---
PRESS_SOUL = "castlereagh"          # press/souls/<name>/SOUL.md
PRESS_MODEL = "z-ai/glm-5.3-flash"  # local default; hosted uses COWORLD_LLM_MODEL (fixed per upload)
PRESS_REASONING = "low"             # OpenRouter reasoning effort ("" = provider default)
PRESS_TEMPERATURE = 0.4             # None omits it (the sidecar requires every sent parameter be supported)
PRESS_MAX_TOKENS = 2000             # per model call
PRESS_CALL_TIMEOUT_S = 45.0         # per model call (the sidecar's upstream timeout is 60 s)
PRESS_REQUEST_LIMIT = 8             # model calls per wake
PRESS_WAKE_SECONDS = 60.0           # wall-clock limit per wake
PRESS_MAX_WAKES = 5                 # per movement phase, including open and commit
PRESS_WAKE_GAP_S = 20.0             # minimum gap between negotiate wakes
PRESS_COMMIT_MARGIN_S = 75.0        # commit wake starts this long before the deadline
PRESS_FINAL_MARGIN_S = 15.0         # orders saved with Ready this long before the deadline
PRESS_MAX_MESSAGES_PER_PHASE = 8
PRESS_MAX_MESSAGE_CHARS = 600
