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
    "blucher": {
        "base": "search",
        "overrides": {"SPRING_ATTACK_WEIGHT": 967, "SPRING_DEFENSE_WEIGHT": 100, "FALL_ATTACK_WEIGHT": 850,
                      "FALL_DEFENSE_WEIGHT": 150, "SEARCH_DISLODGED_WEIGHT": 0.5, "SEARCH_POS_WEIGHT": 2.0,
                      "SEARCH_RESTARTS": 1, "OPP_MODEL_LEVEL": 0, "STRENGTH_WEIGHT": 918},
        "motto": "Marshal Forwards. Bred by evolution (g2-0ed5), not designed: always attacking.",
    },
    "nash": {
        "base": "nash",
        "overrides": {"SEARCH_RESTARTS": 1},
        "motto": "No regrets: plays toward an equilibrium of everyone's best plans (SearchBot-style).",
    },
    "kissinger2": {
        "base": "search",
        "overrides": {"OPP_MODEL_LEVEL": 2},
        "motto": "Thinks you think it thinks: opponents best-respond to best-responders (level 2).",
    },
    "fabius": {
        "base": "search",
        "overrides": {"OPP_MODEL_LEVEL": 1, "SEARCH_RISK": 0.8, "SEARCH_DISLODGED_WEIGHT": 6.0,
                      "SPRING_ATTACK_WEIGHT": 500, "SPRING_DEFENSE_WEIGHT": 500,
                      "FALL_ATTACK_WEIGHT": 450, "FALL_DEFENSE_WEIGHT": 550},
        "motto": "Cunctator: wins by not losing. Plans for the worst opponent sample, never gives ground.",
    },
    "garibaldi": {
        "base": "search",
        "overrides": {"OPP_MODEL_LEVEL": 1, "SPRING_ATTACK_WEIGHT": 950, "SPRING_DEFENSE_WEIGHT": 100,
                      "FALL_ATTACK_WEIGHT": 850, "FALL_DEFENSE_WEIGHT": 150, "SEARCH_DISLODGED_WEIGHT": 0.5,
                      "SEARCH_POS_WEIGHT": 2.0},
        "motto": "The Thousand: Kissinger's foresight with a red shirt's appetite for the attack.",
    },
}


def resolve(name):
    """Return (base policy name, overrides dict) for a personality, or None."""
    p = PERSONALITIES.get(name)
    return (p["base"], dict(p["overrides"])) if p else None
