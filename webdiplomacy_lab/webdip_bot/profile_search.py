"""Profile or time a decision inside the player image.

Legacy replay selection: profile_search /runs [POLICY] (first replay, turn 8).
Frozen fixture: profile_search /lab/webdip_bot/tests/golden.json kissinger --case 56.
Add --no-profile --warmup 1 for unprofiled timings. Interleave images externally;
compare the behavior digest and reject budget-hit runs before comparing times.
"""

import argparse
import cProfile
import glob
import hashlib
import json
from pathlib import Path
import platform
import pstats
import random
import time

from webdip_bot import config
from webdip_bot.bot import policy_class
from webdip_bot.check_fastadj import board_from
from webdip_bot.golden import BELIEFS, _board


def fixture(root, index):
    if index is not None:
        raw = Path(root).read_bytes()
        data = json.loads(raw)
        case = data['cases'][index]
        return data['variant'], _board(data['variant'], case['units'], case['centers']), case, hashlib.sha256(raw).hexdigest()
    path = sorted(glob.glob(f"{root}/*/*/replay"))[0]
    raw = Path(path).read_bytes()
    frames = json.loads(raw)
    variant = frames[-1]['variant']
    ph = next(p for p in frames[-1]['history']['phases'] if p['phase'] == 'Diplomacy' and p['turn'] == 8)
    board = board_from(variant, ph)
    board['territories'] = [dict(t, ownerCountryID=t['ownerCountryID'] or 0) for t in board['territories']]
    counts = {}
    for u in board['units']:
        counts[int(u['countryID'])] = counts.get(int(u['countryID']), 0) + 1
    country = max(counts, key=counts.get)
    case = dict(country=country, phase='Diplomacy', turn=8, seed=0, belief='prior',
                slots=[{'unitID': u['id']} for u in board['units'] if int(u['countryID']) == country])
    return variant, board, case, hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    parser.add_argument('policy', nargs='?', default='kissinger')
    parser.add_argument('--case', type=int)
    parser.add_argument('--no-profile', action='store_true')
    parser.add_argument('--warmup', type=int, default=0)
    args = parser.parse_args()
    variant, board, case, fixture_hash = fixture(args.root, args.case)
    cls = policy_class(args.policy)

    def decision(profile=None):
        started = time.perf_counter()
        rng = random.Random(case['seed'])
        bot = cls(variant, board, case['country'], case['phase'], case['turn'], rng)
        lo = BELIEFS[case['belief']]
        bot.memory = {'logodds': {str(c): lo for c in range(1, 8)} if lo is not None else {}, 'pending': None}
        choose_started = time.perf_counter()
        if profile is not None:
            profile.enable()
        orders = bot.choose(case['slots'])
        if profile is not None:
            profile.disable()
        stopped = time.perf_counter()
        behavior = dict(orders=orders, rng_state=rng.getstate(), memory=bot.memory,
                        trace={k: v for k, v in bot.trace.items() if not k.endswith('_ms')})
        return dict(seconds=stopped-started, choose_seconds=stopped-choose_started,
                    behavior_digest=hashlib.sha256(json.dumps(behavior, sort_keys=True).encode()).hexdigest(),
                    trace=behavior['trace'])

    for _ in range(args.warmup):
        decision()
    profile = None if args.no_profile else cProfile.Profile()
    result = decision(profile)
    result.update(policy=args.policy, case=args.case, fixture_sha256=fixture_hash,
                  turn=case['turn'], country=case['country'], seed=case['seed'], belief=case['belief'],
                  units=len(case['slots']), python=platform.python_version(), machine=platform.machine(),
                  config={k: v for k, v in vars(config).items() if k.isupper()})
    if profile is not None:
        stats = pstats.Stats(profile)
        result['profile_total'] = stats.total_tt
        result['profile'] = [dict(file=Path(file).name, line=line, function=name, primitive_calls=v[0],
                                  calls=v[1], self_seconds=v[2], cumulative_seconds=v[3])
                             for (file, line, name), v in stats.stats.items()]
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
