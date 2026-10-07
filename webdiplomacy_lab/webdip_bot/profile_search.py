"""Profile one SearchBot movement decision on a real mid-game position (inside the image).

    docker run --rm --platform linux/amd64 -v $PWD/webdiplomacy_lab/local_runs:/runs:ro \
      --entrypoint /opt/.venv/bin/python webdip-bot:TAG -m webdip_bot.profile_search /runs [POLICY]
"""

import cProfile
import glob
import json
import pstats
import random
import sys
import time

from webdip_bot.bot import policy_class
from webdip_bot.check_fastadj import board_from


def main():
    root = sys.argv[1]
    policy = sys.argv[2] if len(sys.argv) > 2 else "kissinger"
    path = sorted(glob.glob(f"{root}/*/*/replay"))[0]
    frames = json.load(open(path))
    variant = frames[-1]["variant"]
    ph = [p for p in frames[-1]["history"]["phases"] if p["phase"] == "Diplomacy" and p["turn"] == 8][0]
    board = board_from(variant, ph)
    board["territories"] = [dict(t, ownerCountryID=t["ownerCountryID"] or 0) for t in board["territories"]]
    cls = policy_class(policy)
    counts = {}
    for u in board["units"]:
        counts[int(u["countryID"])] = counts.get(int(u["countryID"]), 0) + 1
    country = max(counts, key=counts.get)
    slots = [{"unitID": u["id"]} for u in board["units"] if int(u["countryID"]) == country]
    bot = cls(variant, board, country, "Diplomacy", 8, random.Random(0))
    pr = cProfile.Profile()
    t = time.time()
    pr.enable()
    bot.choose(slots)
    pr.disable()
    print(json.dumps({"policy": policy, "units": len(slots), "seconds": round(time.time() - t, 2),
                      "trace": dict(bot.trace)}))
    pstats.Stats(pr).sort_stats("tottime").print_stats(18)


if __name__ == "__main__":
    main()
