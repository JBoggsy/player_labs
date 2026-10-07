"""Direct native/reference parity over exhaustive tiny boards and seeded larger plans.

Run inside the built player image: python -m webdip_bot.check_native_adjudicator.
This compares moved/dislodged flags before any floating scoring. The Python
Adjudicator remains the reference; production adjudicate must be the native entry.
"""

import itertools
import json
import random

from webdip_bot.fastadj import Adjudicator, adjudicate


def check(units, orders):
    reference = Adjudicator(units, orders).run()
    result = adjudicate(units, orders)
    assert result == reference, (units, orders, reference, result)
    assert all(type(v) is bool for flags in result for v in flags)


def main():
    assert adjudicate.__module__ == 'webdip_bot.adjudicator_native'
    count = 0
    options = [('H',)] + [('M', p) for p in range(1, 5)] + [('SH', p) for p in range(1, 5)]
    options += [('SM', a, b) for a in range(1, 4) for b in range(1, 5)]
    for countries in itertools.product((1, 2), repeat=3):
        units = [(c, i + 1, 'Army') for i, c in enumerate(countries)]
        for orders in itertools.product(options, repeat=3):
            check(units, orders)
            count += 1
    rng = random.Random(4821)
    for _ in range(100000):
        n = rng.randrange(1, 35)
        provinces = rng.sample(range(1, 82), n)
        units = [(rng.randrange(1, 8), p, rng.choice(('Army', 'Fleet'))) for p in provinces]
        orders = []
        for _ in units:
            kind = rng.choice(('H', 'M', 'M', 'SH', 'SM'))
            dest = rng.choice(provinces + [83])
            orders.append((kind, rng.choice(provinces), dest) if kind == 'SM' else
                          (kind, dest) if kind != 'H' else (kind,))
        check(units, orders)
        count += 1
    check([], [])
    print(json.dumps({'checked': count + 1, 'mismatches': 0}))


if __name__ == '__main__':
    main()
