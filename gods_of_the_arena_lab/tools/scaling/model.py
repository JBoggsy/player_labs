"""Scaling model for Gods of the Arena: every number as a function of level.

Reads the engine dump (specs.json, produced by a Nim program linked against
polyworld content.nim) and computes derived quantities used by charts.py.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL = os.path.join(HERE, 'specs.json')
SPECS = json.load(open(_LOCAL if os.path.exists(_LOCAL) else os.path.join(HERE, '..', 'dump', 'specs.json')))
TICK = SPECS['tickRate']            # 24
TILE = 60_000
LEVELS = list(range(1, 21))
MAX_LEVEL = 20
MANA_REGEN_PER_S = TICK / 6         # 1 mana every 6 ticks
FOOTMAN_HP, FOOTMAN_DMG = 60, 12
TOWER_HP = [1200, 2400, 4800]
TOWER_DMG = [28, 56, 112]           # once per second
TOWER_RANGE = [5.0, 5.5, 6.0]
FORT_HP = 400
REWARDS = {'footman': (25, 15), 'hero': (150, 100), 'tower': (100, 75)}
START_GOLD = 150
RESPAWN_TICKS = 24 + 192

HEROES = SPECS['heroes']
ITEMS = {i['name']: i for i in SPECS['items']}
BLUE = [h for h in HEROES if h['id'] <= 4]
RED = [h for h in HEROES if h['id'] >= 5]


def hp(h, L): return h['baseHp'] + (L - 1) * h['hpPerLevel']
def mana(h, L): return h['baseMana'] + (L - 1) * h['manaPerLevel']
def dmg(h, L): return h['baseDamage'] + (L - 1) * h['damagePerLevel']
def move_tiles_per_s(h, L): return (h['baseMove'] + (L - 1) * h['movePerLevel']) * TICK / TILE
def attacks_per_s(h): return TICK / h['attackTicks']
def basic_dps(h, L): return dmg(h, L) * attacks_per_s(h)
def attack_range(h): return h['attackRange'] / TILE


def enemies_of(h):
    return RED if h['id'] <= 4 else BLUE


def mean_enemy_hp(h, L):
    return sum(hp(e, L) for e in enemies_of(h)) / 5


def xp_to_next(L): return 100 + (L - 1) * 75
def cum_xp(L):
    """XP needed to reach level L from level 1."""
    return sum(xp_to_next(l) for l in range(1, L))


def level_at_xp(x):
    L = 1
    while L < MAX_LEVEL and x >= xp_to_next(L):
        x -= xp_to_next(L); L += 1
    return L


def strikes(h):
    return [a for a in h['abilities'] if a['kind'] == 'Strike']


def heals(h):
    return [a for a in h['abilities'] if a['kind'] in ('Heal', 'Restore')]


def sustained_rate_per_s(a):
    """Casts per second once charges are exhausted: one charge per rechargeTicks."""
    return TICK / a['rechargeTicks']


def spell_dps_sustained(h):
    return sum(a['damage'] * sustained_rate_per_s(a) for a in strikes(h))


def spell_mana_per_s_sustained(h):
    return sum(a['manaCost'] * sustained_rate_per_s(a) for a in strikes(h))


def spell_dps_mana_limited(h, L):
    """Sustained spell DPS when mana regen (4/s) is the binding constraint.

    Assumes the hero spends regen on the best damage-per-mana strikes first;
    free (0 mana) strikes are always available. Pool is ignored (long run).
    """
    budget = MANA_REGEN_PER_S
    total = 0.0
    ranked = sorted(strikes(h), key=lambda a: (a['damage'] / a['manaCost']) if a['manaCost'] else float('inf'), reverse=True)
    for a in ranked:
        rate = sustained_rate_per_s(a)
        if a['manaCost'] == 0:
            total += a['damage'] * rate
            continue
        affordable = min(rate, budget / a['manaCost'])
        total += a['damage'] * affordable
        budget -= affordable * a['manaCost']
        if budget <= 0:
            break
    return total


def burst_10s(h):
    """Damage available in the first 10 s of a fight with full charges, ignoring mana."""
    total = 0
    for a in strikes(h):
        casts = a['charges'] + int((10 * TICK - 1) // a['cooldownTicks']) if a['charges'] > 1 else 1
        casts = min(casts, a['charges'] + (10 * TICK) // a['rechargeTicks'])
        total += a['damage'] * casts
    return total


def rotation_mana(h):
    """Mana to cast every strike once (one full rotation)."""
    return sum(a['manaCost'] for a in strikes(h))


def hits_to_kill(att_dmg, target_hp):
    return math.ceil(target_hp / att_dmg)


def seconds_to_kill(att, target_hp, L):
    return hits_to_kill(dmg(att, L), target_hp) * att['attackTicks'] / TICK


def seconds_to_die_under_tower(h, L, tier):
    return math.ceil(hp(h, L) / TOWER_DMG[tier])  # one tower hit per second


def item_dmg_share(h, L, bonus): return bonus / dmg(h, L)
def item_hp_share(h, L, bonus): return bonus / hp(h, L)


def level_over_time(xp_per_s, minutes=20, step_s=10):
    t, x, out = 0, 0, []
    while t <= minutes * 60:
        out.append((t / 60, level_at_xp(x)))
        x += xp_per_s * step_s; t += step_s
    return out


if __name__ == '__main__':
    for h in HEROES:
        print(h['name'], 'L1 dps', round(basic_dps(h, 1), 1), 'L20 dps', round(basic_dps(h, 20), 1),
              'spell sustained', round(spell_dps_sustained(h), 1), 'mana-limited', round(spell_dps_mana_limited(h, 1), 1),
              'rotation mana', rotation_mana(h), 'pool L1', mana(h, 1), 'pool L20', mana(h, 20))
