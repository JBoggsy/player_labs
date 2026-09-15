"""Render the scaling report figures as SVG, following the dataviz palette/marks."""
import os, math, sys
import numpy as np
import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from model import *

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'figures')
os.makedirs(OUT, exist_ok=True)

# --- palette (dataviz reference instance, light mode) ---
SURFACE = '#fcfcfb'; INK = '#0b0b0b'; INK2 = '#52514e'; MUTED = '#898781'
GRID = '#e1e0d9'; AXIS = '#c3c2b7'; DEEMPH = '#c3c2b7'
S1, S2, S3, S4 = '#2a78d6', '#eb6834', '#1baf7a', '#eda100'
SEQ = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5', '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']
CMAP = LinearSegmentedColormap.from_list('seqblue', SEQ)

plt.rcParams.update({
    'font.family': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'],
    'font.size': 9, 'axes.titlesize': 10, 'axes.titleweight': 'semibold', 'axes.titlecolor': INK,
    'axes.labelsize': 9, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED,
    'xtick.labelsize': 8, 'ytick.labelsize': 8, 'axes.edgecolor': AXIS, 'axes.linewidth': 0.8,
    'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6, 'grid.linestyle': '-',
    'axes.spines.top': False, 'axes.spines.right': False, 'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE,
    'lines.linewidth': 2, 'lines.solid_capstyle': 'round', 'lines.solid_joinstyle': 'round',
    'legend.frameon': False, 'legend.fontsize': 8, 'svg.fonttype': 'none',
})
W = 6.8  # inches, ~650px column


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + '.svg'), bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)


def short(h):
    return h['name'].replace('Vanguard Knight', 'V. Knight').replace('Druid Warden', 'D. Warden').replace('Demon Hunter', 'D. Hunter').replace('Death Knight', 'Death Kn.')


def heatmap(matrix, rows, cols, title, fmt='{:.0f}', name='hm', xlabel='', cbar_label='', vmin=None, vmax=None, figsize=(W, 4.2), note=None, rotate=0):
    m = np.array(matrix, dtype=float)
    fig, ax = plt.subplots(figsize=figsize)
    ax.grid(False)
    vmin = np.nanmin(m) if vmin is None else vmin; vmax = np.nanmax(m) if vmax is None else vmax
    im = ax.imshow(m, cmap=CMAP, vmin=vmin, vmax=vmax, aspect='auto')
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=rotate, ha='right' if rotate else 'center')
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows)
    ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m[i, j]
            if np.isnan(v):
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, color=SURFACE)); continue
            frac = (v - vmin) / (vmax - vmin) if vmax > vmin else 0
            ax.text(j, i, fmt.format(v), ha='center', va='center', fontsize=7.5, color='white' if frac > 0.55 else INK)
    # 2px surface gap between cells
    for j in range(1, m.shape[1]): ax.axvline(j - .5, color=SURFACE, lw=1.5)
    for i in range(1, m.shape[0]): ax.axhline(i - .5, color=SURFACE, lw=1.5)
    ax.set_title(title, loc='left'); ax.set_xlabel(xlabel)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.outline.set_visible(False); cb.ax.tick_params(length=0, labelsize=7, colors=MUTED)
    if cbar_label: cb.set_label(cbar_label, color=INK2, fontsize=8)
    if note: fig.text(0.01, -0.06 if rotate else -0.02, note, fontsize=7.5, color=MUTED)
    save(fig, name)


def small_multiples(fn, title, ylabel, name, ylim=None, fmt='{:.0f}'):
    """One panel per hero; this hero in blue, the other nine in gray."""
    fig, axes = plt.subplots(2, 5, figsize=(W, 3.9), sharex=True, sharey=True)
    for ax, h in zip(axes.flat, HEROES):
        for o in HEROES:
            if o is not h: ax.plot(LEVELS, [fn(o, L) for L in LEVELS], color=DEEMPH, lw=1, zorder=1)
        ys = [fn(h, L) for L in LEVELS]
        ax.plot(LEVELS, ys, color=S1, zorder=3)
        ax.plot([20], [ys[-1]], 'o', ms=5, color=S1, mec=SURFACE, mew=1.5, zorder=4)
        ax.set_title(short(h), fontsize=8.5)
        ax.text(19.5, ys[-1], fmt.format(ys[-1]), fontsize=7, color=INK2, va='bottom', ha='right')
        ax.set_xticks([1, 10, 20]); ax.set_xlim(1, 21)
        if ylim: ax.set_ylim(*ylim)
    for ax in axes[1]: ax.set_xlabel('level')
    for ax in axes[:, 0]: ax.set_ylabel(ylabel)
    fig.suptitle(title, x=0.01, y=0.995, ha='left', fontsize=10, fontweight='semibold', color=INK)
    fig.text(0.01, 0.925, 'blue: this hero · gray: the other nine, for context', fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save(fig, name)


def label_end(ax, x, y, text, color=INK2, dx=0.3):
    ax.text(x + dx, y, text, fontsize=7.5, color=color, va='center', ha='left', clip_on=False)


# ---------------- Figure 1: growth multiples heatmap ----------------
stats = [('HP', hp), ('Mana', mana), ('Basic dmg', dmg), ('Move', move_tiles_per_s), ('Basic DPS', basic_dps)]
mat = [[fn(h, 20) / fn(h, 1) for _, fn in stats] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], [s for s, _ in stats], 'Level 20 value as a multiple of level 1', fmt='{:.1f}×', name='fig-01-growth', cbar_label='multiple', figsize=(W, 4.0), vmin=1, note='Attack speed, attack range, and every ability number are 1.0× (unchanged) and are not shown.')

# ---------------- Figure 2/3: HP and basic DPS small multiples ----------------
small_multiples(hp, 'Max HP by level', 'HP', 'fig-02-hp')
small_multiples(basic_dps, 'Basic-attack damage per second by level', 'DPS', 'fig-03-dps', fmt='{:.0f}')

# ---------------- Figure 4: time to kill heatmaps ----------------
def ttk_matrix(L):
    m = []
    for a in HEROES:
        row = []
        for d in HEROES:
            if (a['id'] <= 4) == (d['id'] <= 4): row.append(np.nan)
            else: row.append(seconds_to_kill(a, hp(d, L), L))
        m.append(row)
    return m
for L in (1, 10, 20):
    heatmap(ttk_matrix(L), [short(h) for h in HEROES], [short(h) for h in HEROES], f'Seconds of basic attacks to kill an enemy hero, both at level {L}', fmt='{:.0f}', name=f'fig-04-ttk-L{L}', xlabel='defender', figsize=(W, 4.8), vmin=0, vmax=40, rotate=30, note='Rows: attacker. Blank: same team. Basic attacks only, no abilities, no items, no healing.')

# ---------------- Figure 5: strike ability as share of enemy HP ----------------
fig, axes = plt.subplots(2, 5, figsize=(W, 4.2), sharex=True, sharey=True)
cols = [S1, S2, S3, S4]
for ax, h in zip(axes.flat, HEROES):
    for k, a in enumerate(strikes(h)):
        ys = [100 * a['damage'] / mean_enemy_hp(h, L) for L in LEVELS]
        ax.plot(LEVELS, ys, color=cols[k], label=a['name'])
    ax.legend(loc='upper right', fontsize=5.8, handlelength=1.0, borderpad=0.2, labelspacing=0.2)
    ax.set_title(short(h), fontsize=8.5); ax.set_xticks([1, 10, 20]); ax.set_ylim(0, 70)
for ax in axes[1]: ax.set_xlabel('level (both sides)')
for ax in axes[:, 0]: ax.set_ylabel('% of enemy HP')
fig.suptitle('One cast of each strike ability as a share of the average enemy hero HP at the same level', x=0.01, y=0.995, ha='left', fontsize=10, fontweight='semibold', color=INK)
fig.text(0.01, 0.925, 'Ability damage is fixed, so the share only falls.', fontsize=7.5, color=MUTED)
fig.tight_layout(rect=(0, 0, 1, 0.9)); save(fig, 'fig-05-strike-share')

# ---------------- Figure 6: heals as share of own HP ----------------
healers = [h for h in HEROES if any(a['kind'] == 'Heal' for a in h['abilities'])]
fig, axes = plt.subplots(1, len(healers), figsize=(W, 2.6), sharey=True)
for ax, h in zip(axes, healers):
    for k, a in enumerate([a for a in h['abilities'] if a['kind'] == 'Heal']):
        ys = [100 * a['heal'] / hp(h, L) for L in LEVELS]
        ax.plot(LEVELS, ys, color=cols[k], label=a['name'])
    ax.legend(loc='upper right', fontsize=6, handlelength=1.0, borderpad=0.2, labelspacing=0.2)
    ax.set_title(short(h), fontsize=8.5); ax.set_xticks([1, 10, 20]); ax.set_xlabel('level')
axes[0].set_ylabel('% of own max HP')
fig.suptitle('One cast of each heal as a share of the caster\'s own max HP', x=0.01, y=0.995, ha='left', fontsize=10, fontweight='semibold', color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.92)); save(fig, 'fig-06-heal-share')

# ---------------- Figure 7: DPS mix ----------------
fig, axes = plt.subplots(2, 5, figsize=(W, 4.0), sharex=True, sharey=True)
for ax, h in zip(axes.flat, HEROES):
    ax.plot(LEVELS, [basic_dps(h, L) for L in LEVELS], color=S1)
    ax.plot(LEVELS, [spell_dps_sustained(h)] * 20, color=S2)
    ax.plot(LEVELS, [spell_dps_mana_limited(h, L) for L in LEVELS], color=S3)
    ax.set_title(short(h), fontsize=8.5); ax.set_xticks([1, 10, 20])
for ax in axes[1]: ax.set_xlabel('level')
for ax in axes[:, 0]: ax.set_ylabel('damage / s')
fig.legend(axes[0, 0].lines, ['basic attacks', 'abilities, cooldown-bound', 'abilities, mana-regen-bound'], loc='upper left', ncol=3, fontsize=7, handlelength=1.2, bbox_to_anchor=(0.005, 0.95))
fig.suptitle('Sustained damage per second: basic attacks versus abilities', x=0.01, y=0.995, ha='left', fontsize=10, fontweight='semibold', color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.88)); save(fig, 'fig-07-dps-mix')

# ---------------- Figure 8: burst share heatmap ----------------
mat = [[100 * burst_10s(h) / mean_enemy_hp(h, L) for L in LEVELS] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], LEVELS, 'Ten-second ability burst (full charges, mana ignored) as % of average enemy hero HP', fmt='{:.0f}', name='fig-08-burst', xlabel='level (both sides)', cbar_label='% of enemy HP', vmin=0, figsize=(W, 4.2))

# ---------------- Figure 9: footmen and towers ----------------
mat = [[hits_to_kill(dmg(h, L), FOOTMAN_HP) for L in LEVELS] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], LEVELS, 'Basic attacks needed to kill one footman (60 HP)', fmt='{:.0f}', name='fig-09-footman-hits', xlabel='level', cbar_label='hits', vmin=1, vmax=3, figsize=(W, 4.0))
mat = [[seconds_to_die_under_tower(h, L, 2) for L in LEVELS] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], LEVELS, 'Seconds a hero survives under a gate tower (112 damage/s), no healing', fmt='{:.0f}', name='fig-10-tower-survival', xlabel='level', cbar_label='seconds', figsize=(W, 4.0))
fig, ax = plt.subplots(figsize=(W, 2.8))
for k, (tier, name) in enumerate([(0, 'outer 1,200 HP'), (1, 'inner 2,400 HP'), (2, 'gate 4,800 HP')]):
    ys = [np.mean([TOWER_HP[tier] / basic_dps(h, L) for h in HEROES]) for L in LEVELS]
    ax.plot(LEVELS, ys, color=cols[k]); label_end(ax, 20, ys[-1], name)
ax.set_xlabel('level'); ax.set_ylabel('seconds'); ax.set_xticks([1, 5, 10, 15, 20])
ax.set_title('Seconds for one hero alone to destroy a tower with basic attacks (average over the ten classes)', loc='left')
fig.tight_layout(); save(fig, 'fig-11-tower-time')

# ---------------- Figure 12: items ----------------
mat = [[100 * item_dmg_share(h, L, 14) for L in LEVELS] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], LEVELS, 'Battle Axe / Rune Crossbow (+14 damage) as % of basic-attack damage', fmt='{:.0f}', name='fig-12-item-dmg', xlabel='level', cbar_label='% of damage', vmin=0)
mat = [[100 * item_hp_share(h, L, 120) for L in LEVELS] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], LEVELS, 'Knight Armor (+120 max HP) as % of max HP', fmt='{:.0f}', name='fig-13-item-hp', xlabel='level', cbar_label='% of HP', vmin=0)

# ---------------- Figure 14: consumables ----------------
mat = [[100 * 90 / hp(h, L) for L in LEVELS] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], LEVELS, 'Vitality Elixir (+90 HP, 50 gold) as % of max HP', fmt='{:.0f}', name='fig-14-elixir', xlabel='level', cbar_label='% of HP', vmin=0)
fig, ax = plt.subplots(figsize=(W, 2.8))
ys = [100 * 35 / np.mean([hp(h, L) for h in HEROES]) for L in LEVELS]
ax.plot(LEVELS, ys, color=S1); label_end(ax, 20, ys[-1], 'vs average hero')
ax.plot(LEVELS, [100 * 35 / FOOTMAN_HP] * 20, color=S2); label_end(ax, 20, 100 * 35 / 60, 'vs footman (60 HP)')
ax.set_xlabel('level'); ax.set_ylabel('% of target HP'); ax.set_xticks([1, 5, 10, 15, 20])
ax.set_title('Poison Potion (35 damage, 40 gold) as a share of target HP', loc='left')
fig.tight_layout(); save(fig, 'fig-15-poison')

# ---------------- Figure 16: XP curve and time to level ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 3.0))
a1.plot(LEVELS, [cum_xp(L) for L in LEVELS], color=S1); a1.plot([20], [cum_xp(20)], 'o', ms=5, color=S1, mec=SURFACE, mew=1.5)
label_end(a1, 20, cum_xp(20), f'{cum_xp(20):,}', dx=-3.5)
a1.set_xlabel('level'); a1.set_ylabel('cumulative XP'); a1.set_title('XP needed to reach each level', loc='left'); a1.set_xticks([1, 5, 10, 15, 20])
scen = [(3.0, '1/5 of team creeps (3 XP/s)', S1), (5.0, 'one full lane (5 XP/s)', S2), (6.25, 'one lane + a hero kill every 2 min', S3), (15.0, 'every creep on the map (15 XP/s)', S4)]
for rate, lab, c in scen:
    pts = level_over_time(rate); a2.plot([p[0] for p in pts], [p[1] for p in pts], color=c)
a2.set_xlabel('match minute'); a2.set_ylabel('level'); a2.set_title('Level over a 20-minute match by income', loc='left'); a2.set_ylim(1, 20.5)
a2.legend([s[1] for s in scen], loc='upper left', fontsize=6.5, handlelength=1.2)
fig.tight_layout(); save(fig, 'fig-16-xp')

# ---------------- Figure 17: value of a hero kill ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, 2.8))
a1.plot(LEVELS, [100 * 150 / xp_to_next(L) for L in LEVELS], color=S1); label_end(a1, 20, 100 * 150 / xp_to_next(20), '10%', dx=0.2)
a1.plot(LEVELS, [100 * 25 / xp_to_next(L) for L in LEVELS], color=S2); label_end(a1, 20, 100 * 25 / xp_to_next(20), 'footman', dx=0.2)
a1.set_ylim(0, 160); a1.set_xlabel('killer\'s level'); a1.set_ylabel('% of next level'); a1.set_title('XP from one kill as a share of the next level', loc='left'); a1.set_xticks([1, 5, 10, 15, 20])
a1.legend(['hero kill (150 XP)', 'footman (25 XP)'], loc='upper right', fontsize=7)
# gold: seconds of creep farming equivalent
a2.bar(['footman', 'tower', 'hero'], [15, 75, 100], color=S1, width=0.5)
for i, v in enumerate([15, 75, 100]): a2.text(i, v + 2, f'{v} gold', ha='center', fontsize=7.5, color=INK2)
a2.grid(axis='x', visible=False); a2.set_ylim(0, 120); a2.set_title('Gold per kill, fixed for the whole match', loc='left'); a2.set_ylabel('gold')
fig.tight_layout(); save(fig, 'fig-17-kill-value')

# ---------------- Figure 18: mana ----------------
mat = [[mana(h, L) / rotation_mana(h) if rotation_mana(h) else np.nan for L in LEVELS] for h in HEROES]
heatmap(mat, [short(h) for h in HEROES], LEVELS, 'Full strike rotations a full mana pool pays for (one cast of every strike)', fmt='{:.1f}', name='fig-18-mana-rotations', xlabel='level', cbar_label='rotations', vmin=0, note='Berserker\'s rotation costs 36 mana; Molten Fist is free.')
fig, ax = plt.subplots(figsize=(W, 2.9))
ys = sorted([(spell_mana_per_s_sustained(h), short(h)) for h in HEROES], reverse=True)
ax.barh([n for _, n in ys], [v for v, _ in ys], color=S1, height=0.55)
ax.axvline(MANA_REGEN_PER_S, color=S2, lw=2); ax.text(MANA_REGEN_PER_S + 0.1, 9.3, 'regen 4 mana/s', fontsize=7.5, color=INK2)
ax.invert_yaxis(); ax.grid(axis='y', visible=False); ax.set_xlabel('mana per second at the cooldown-bound cast rate')
ax.set_title('Mana needed to cast every strike as soon as it recharges, versus regeneration', loc='left')
fig.tight_layout(); save(fig, 'fig-19-mana-rate')

print('figures written to', OUT, len(os.listdir(OUT)))
