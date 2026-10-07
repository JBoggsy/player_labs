"""LOCAL-ONLY arena dispatcher: slot 0 plays the candidate policy, every other slot the field.

    python -m webdip_bot.arena CANDIDATE FIELD

The launcher sets WEBDIP_SEED = episode_seed * 7 + slot, so slot = WEBDIP_SEED % 7.
Country assignment is random per episode, so a fixed candidate slot still samples all
powers.
"""

import os
import sys

from webdip_bot.bot import main

if __name__ == "__main__":
    candidate, field = sys.argv[1], sys.argv[2]
    slot = int(os.environ.get("WEBDIP_SEED", "0")) % 7
    main(candidate if slot == 0 else field)
