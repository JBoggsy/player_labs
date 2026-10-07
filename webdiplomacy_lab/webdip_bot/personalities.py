"""The agent roster: named personalities = a base policy + config overrides.

Each personality is a distinct playing style, uploadable as its own policy
(`docker build --build-arg POLICY=<name>`) and usable in the local arena/tourney by
name. Keep entries small and declarative; new algorithms get their own module and a
base name in bot.policy_class.

Fields: base (policy_class name), overrides (config attrs), motto (flavour, shown in
logs and docs).
"""

PERSONALITIES = {
    "random": {
        "base": "random",
        "overrides": {},
        "motto": "Chaos is a ladder; I just never climb it.",
    },
    "calhamer": {
        "base": "dumbbot_v1",
        "overrides": {},
        "motto": "Classic DumbBot, frozen as it was first uploaded. The honest yardstick.",
    },
    "machiavelli": {
        "base": "search",
        "overrides": {},
        "motto": "Best response to whatever you are, measured on a real adjudicator.",
    },
    "bismarck": {
        "base": "search",
        "overrides": {
            "SPRING_ATTACK_WEIGHT": 900, "SPRING_DEFENSE_WEIGHT": 100,
            "FALL_ATTACK_WEIGHT": 850, "FALL_DEFENSE_WEIGHT": 150,
            "SEARCH_DISLODGED_WEIGHT": 0.5, "SEARCH_POS_WEIGHT": 2.0,
        },
        "motto": "Blood and iron: attack weights up, losses shrugged off.",
    },
    "metternich": {
        "base": "search",
        "overrides": {
            "SPRING_ATTACK_WEIGHT": 400, "SPRING_DEFENSE_WEIGHT": 600,
            "FALL_ATTACK_WEIGHT": 350, "FALL_DEFENSE_WEIGHT": 650,
            "SEARCH_DISLODGED_WEIGHT": 8.0, "SEARCH_OBJECTIVE": "share",
        },
        "motto": "Balance of power: never lose a unit, keep the leader small.",
    },
    "talleyrand": {
        "base": "search",
        "overrides": {"SEARCH_OBJECTIVE": "share"},
        "motto": "Plays the scoreboard, not the map: maximizes its SC-squared share.",
    },
    "napoleon": {
        "base": "search",
        "overrides": {"SEARCH_ROLLOUT": 1},
        "motto": "Thinks one season ahead: spring moves judged by the autumn they set up.",
    },
    "kissinger": {
        "base": "search",
        "overrides": {"OPP_MODEL_LEVEL": 1},
        "motto": "Assumes you are clever too: best-responds to opponents who best-respond.",
    },
    "kutuzov": {
        "base": "search",
        "overrides": {"SEARCH_EVAL": "learned", "SEARCH_RESTARTS": 1},
        "motto": "Patience and time: judges positions by where they lead two years on (learned).",
    },
}


def resolve(name):
    """Return (base policy name, overrides dict) for a personality, or None."""
    p = PERSONALITIES.get(name)
    return (p["base"], dict(p["overrides"])) if p else None
