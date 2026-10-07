# webdip_bot — DumbBot on webDiplomacy

The launcher's child process (`python -m webdip_bot.bot`) in an image built `FROM` the
published webdiplomacy 0.7.7 player image (pinned by digest in the `Dockerfile`).

- `dumbbot.py`: DumbBot's algorithm over webDip's `variant.json` graph. It follows
  the MIT-licensed Python port in
  [diplomacy/research](https://github.com/diplomacy/research/blob/master/diplomacy_research/players/rulesets/dumbbot_ruleset.py)
  (Paquette, 2019). Steps:
  1. Province values from power sizes (`n² + 4n + 16`).
  2. Ten-step proximity spreading.
  3. Strength/competition adjustments.
  4. Randomized descent over ranked destinations, with the move/support/defer rules.
  5. Wasted holds converted to supports.
  6. Value-ranked retreats, builds and disbands.
- `config.py`: every weight. Defaults are the original values. Deliberate deviation
  from the port: `NEUTRAL_SIZE_MODE = "uno"` sizes unowned centres as one pseudo-power
  (DAIDE's UNO owner) instead of giving them zero value.
- `bot.py`: phase loop. Reads context and public files, chooses, saves with Ready,
  diffs the saved orders, and prints one `decision` JSON line per phase:
  `{turn, phase, country, units, centers, compute_ms, trace, rejected, difference}`.
  `trace` counts activations (`Move`, `Support move`, `Support hold`, `Hold`,
  `deferred`, `alternative_picked`, `wasted_hold_to_support`,
  `deferral_cycle_broken`, `illegal_fallback_hold`, builds/retreats). Exceptions are
  logged with a traceback, and the bot keeps playing.

Every movement order is checked against the bundled `LegalOrders` generator. An order
that is not legal becomes a Hold and counts as `illegal_fallback_hold`. No convoys yet.
