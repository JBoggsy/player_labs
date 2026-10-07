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
