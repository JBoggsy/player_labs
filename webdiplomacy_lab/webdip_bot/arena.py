"""LOCAL-ONLY arena dispatcher: picks this seat's policy from argv by slot.

    python -m webdip_bot.arena CANDIDATE FIELD          # slot 0 = candidate, others = field
    python -m webdip_bot.arena P0 P1 P2 P3 P4 P5 P6     # one policy per slot (tourney)

The launcher sets WEBDIP_SEED = episode_seed * 7 + slot, so slot = WEBDIP_SEED % 7.
Country assignment is random per episode, so a fixed slot still samples all powers.
"""

import os
import sys

from webdip_bot.bot import main

if __name__ == "__main__":
    slot = int(os.environ.get("WEBDIP_SEED", "0")) % 7
    args = sys.argv[1:]
    if len(args) == 7:
        main(args[slot])
    else:
        main(args[0] if slot == 0 else args[1])
