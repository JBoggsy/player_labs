#!/usr/bin/env python3
"""Paintbot PW movement diagrams, heatmaps and timelines (lab tool T9). matplotlib only.

Reads traced episodes (pw_episodes tables) and the release's terrain raster (pw_mapdata).
Every command writes a PNG and a JSON of exactly the data it plotted, side by side.

  movement   trails for a tick window over the terrain, one panel per episode (small multiples)
  heatmap    batch position density or death locations for one policy (hexbin)
  occupancy  per-policy occupancy side by side, with a Bhattacharyya overlap score
  timeline   meter and glory per team, capture/kill ticks, heart ownership strip
  gif        animated movement over a window (Pillow)

Times: `1500` = tick 1500, `62.5s` = seconds, `1:10` = m:ss (24 ticks per second).
Positions come from `states` rows, sampled every `state_every` ticks (default 6); pass
`--fine` to re-trace with every-tick states for the window (this replaces the episode's
cache options). Contract: paintbot_pw_lab/docs/tools/pw_viz.md.

  uv run python paintbot_pw_lab/tools/pw_viz.py movement EPISODE_DIR --from 0:40 --to 1:05 --team 0
  uv run python paintbot_pw_lab/tools/pw_viz.py timeline EPISODE_DIR --out /tmp/tl.png

Selectors are checked: an unknown --policy or seat, or a --from at/after the end of every
match, is a usage error (exit 2) that lists the valid values; a --to past a match's end is
clamped to its last tick and reported. Default output: paintbot_pw_lab/analysis/pw_viz/<episode
or batch>/<command>[-selectors].png (+ .json), so a re-run overwrites the same file.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as path_effects  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, ListedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
import pw_episodes  # noqa: E402
import pw_mapdata  # noqa: E402

# ---------------------------------------------------------------- Ink & Print palette
# Softmax house style (metta agent-plugins/ux/skills/ux.ify/references/design-system.md).
# The two team hues pass the dataviz palette validator (CVD, contrast) on the paper and
# on the terrain's lightest tone.
PAPER = "#fffdf4"
INK = "#111827"
INK_SUBTLE = "#555555"
INK_MUTED = "#6b6560"
RULE = "#e4dac8"
TEAM_COLORS = {0: "#b4532a", 1: "#1f4c9a"}   # Ember (terracotta), Azure (ink blue)
NEUTRAL = "#8a8a8a"                          # unowned hearts, the map as killer
TERRAIN_LOW, TERRAIN_HIGH = "#f6f1e3", "#d8ccb0"
WATER = "#cdd9df"
COVER = "#a89a7e"
TRENCH = "#8f7b55"
# magnitude (density, occupancy): one hue, light to dark, independent of team colour
SEQUENTIAL = LinearSegmentedColormap.from_list("ink_seq", ["#e8e4d8", "#5573a0", "#1a3875", "#0a1c42"])

# ---------------------------------------------------------------- named constants
TICK_RATE = 24
ARROW_EVERY_TICKS = 48       # a direction arrowhead on each trail every 2 s (and at its end)
SHOT_MISS_DRAW_UNITS = 600   # misses are drawn as short rays from the shooter; hits to the victim
CAPTURE_RADIUS = 140         # engine capture reach (pw_map meta capture_radius)
OCCUPANCY_CELL = 250         # world units per occupancy bin (10 cells per 2,500 units)
GIF_STEP_TICKS = 6           # one frame per state sample
GIF_TAIL_TICKS = 72          # trail length shown behind each cog in the GIF (3 s)
GIF_MAX_FRAMES = 240


def grenade_blast_radius(rules: int) -> int:
    """mechanics.nim grenadeBlastRadius(): 360 from rules 40, else 270 (cogs within + Radius 55 are hit)."""
    return 360 if rules >= 40 else 270


# ---------------------------------------------------------------- selection helpers

def parse_time(text: str | int | None, tick_rate: int = TICK_RATE) -> int | None:
    """`1500` -> tick 1500; `62.5s` -> seconds; `1:10` -> minutes:seconds. None stays None."""
    if text is None:
        return None
    text = str(text).strip()
    if re.fullmatch(r"\d+", text):
        return int(text)
    if match := re.fullmatch(r"(\d+(?:\.\d+)?)s", text):
        return round(float(match[1]) * tick_rate)
    if match := re.fullmatch(r"(\d+):(\d{1,2}(?:\.\d+)?)", text):
        return round((int(match[1]) * 60 + float(match[2])) * tick_rate)
    raise ValueError(f"bad time {text!r}: use ticks (1500), seconds (62.5s) or m:ss (1:10)")


def clock(tick: float, tick_rate: int = TICK_RATE) -> str:
    seconds = tick / tick_rate
    return f"{int(seconds // 60)}:{seconds % 60:04.1f}"


def select_seats(ep, seats=None, team=None, policy=None) -> list[int]:
    """Seats matching every given filter; `policy` matches policy_key or policy_name."""
    rows = ep["seats"]
    keep = pd.Series(True, index=rows.index)
    if seats:
        keep &= rows.seat.isin(list(seats))
    if team is not None:
        keep &= rows.team == team
    if policy:
        keep &= (rows.policy_key == policy) | (rows.policy_name == policy)
    return sorted(int(s) for s in rows[keep].seat)


def policy_label(episodes: list, policy: str | None) -> str | None:
    """A readable name for a policy_key or policy_name (the key's policy_name when known)."""
    for ep in episodes:
        rows = ep["seats"][ep["seats"].policy_key == policy]
        if len(rows) and pd.notna(rows.iloc[0].policy_name):
            version = rows.iloc[0].policy_version
            return f"{rows.iloc[0].policy_name}" + (f" v{version}" if pd.notna(version) else "")
    return policy


def team_of(ep) -> dict[int, int]:
    return {int(r.seat): int(r.team) for r in ep["seats"].itertuples()}


def heart_owners_at(ep, tick: int) -> dict[int, int]:
    """Exact owner of each heart after tick `tick`: t=0 owners, then capture_complete events."""
    hs = ep["heart_states"]
    owners = {int(r.heart): int(r.owner) for r in hs[hs.t == 0].itertuples()}
    caps = ep["captures"]
    for row in caps[(caps.kind == "capture_complete") & (caps.t <= tick)].sort_values("t").itertuples():
        owners[int(row.heart)] = int(row.team)
    return owners


def trail_segments(states: pd.DataFrame, spawn_ticks: list[int]) -> list[pd.DataFrame]:
    """Split one seat's state samples into continuous alive stretches.

    A trail breaks at every sample where the cog is dead and at every respawn between two
    samples, so a line never joins a death spot to the next spawn point."""
    rows = states.sort_values("t")
    alive = rows.alive.astype(bool).to_numpy()
    ticks = rows.t.to_numpy()
    breaks = np.zeros(len(rows), dtype=bool)
    breaks[1:] = ~alive[:-1]  # every alive row after a dead row starts a new stretch
    for spawn in spawn_ticks:
        breaks[1:] |= (ticks[:-1] < spawn) & (ticks[1:] >= spawn)
    segment_ids = np.cumsum(breaks)
    return [group for _, group in rows[alive].groupby(segment_ids[alive])]


def window_events(ep, t0: int, t1: int, seats: list[int]) -> dict[str, list[dict]]:
    """Events in [t0, t1] that involve the selected seats, with their plotting positions."""
    selected = set(seats)
    team = team_of(ep)
    kills = ep["kills"]
    kills = kills[(kills.t >= t0) & (kills.t <= t1)]
    damage = ep["damage"]
    fatal = damage[damage.killed.astype(bool)]
    out: dict[str, list[dict]] = {"kills": [], "deaths": [], "captures": [], "pickups": [], "blasts": [], "shots": []}
    for row in kills.itertuples():
        killer = None if pd.isna(row.seat) else int(row.seat)
        victim = int(row.victim)
        if victim in selected:
            out["deaths"].append({"t": int(row.t), "seat": victim, "team": team[victim], "killer": killer,
                                  "weapon": row.weapon, "x": int(row.victim_x), "z": int(row.victim_z)})
        if killer is not None and killer in selected and not row.self:
            blow = fatal[(fatal.t == row.t) & (fatal.victim == victim) & (fatal.seat == killer)]
            if len(blow) and pd.notna(blow.iloc[0].attacker_x):
                out["kills"].append({"t": int(row.t), "seat": killer, "team": team[killer], "victim": victim,
                                     "weapon": row.weapon, "friendly": bool(row.friendly),
                                     "x": int(blow.iloc[0].attacker_x), "z": int(blow.iloc[0].attacker_z)})
    hearts = {h["idx"]: h["pos"] for h in ep.meta["hearts"]}
    caps = ep["captures"]
    for row in caps[(caps.kind == "capture_complete") & (caps.t >= t0) & (caps.t <= t1)].itertuples():
        out["captures"].append({"t": int(row.t), "heart": int(row.heart), "team": int(row.team),
                                "seat": None if pd.isna(row.seat) else int(row.seat),
                                "previous_owner": None if pd.isna(row.previous_owner) else int(row.previous_owner),
                                "x": hearts[int(row.heart)][0], "z": hearts[int(row.heart)][1]})
    pickups = ep["pickups"]
    for row in pickups[(pickups.t >= t0) & (pickups.t <= t1)].itertuples():
        if pd.notna(row.seat) and int(row.seat) in selected:
            out["pickups"].append({"t": int(row.t), "seat": int(row.seat), "team": int(row.team),
                                   "kind": row.pickup_kind, "x": int(row.x), "z": int(row.z)})
    events = ep["events"]
    blasts = events[(events.kind == "grenade_blast") & (events.t >= t0) & (events.t <= t1)]
    radius = grenade_blast_radius(int(ep.meta["rules"]))
    for row in blasts.itertuples():
        if pd.notna(row.seat) and int(row.seat) in selected:
            data = json.loads(row.data)
            out["blasts"].append({"t": int(row.t), "seat": int(row.seat), "team": team[int(row.seat)],
                                  "x": data["pos"][0], "z": data["pos"][1], "radius": radius,
                                  "victims": data.get("victims", [])})
    shots = ep["shots"]
    for row in shots[(shots.t >= t0) & (shots.t <= t1) & shots.seat.isin(list(selected))].itertuples():
        x0, z0, x1, z1 = int(row.origin_x), int(row.origin_z), int(row.end_x), int(row.end_z)
        hit = bool(row.hit)
        if not hit:  # draw a miss as a short ray in the fired direction
            length = math.hypot(x1 - x0, z1 - z0) or 1.0
            scale = min(1.0, SHOT_MISS_DRAW_UNITS / length)
            x1, z1 = round(x0 + (x1 - x0) * scale), round(z0 + (z1 - z0) * scale)
        out["shots"].append({"t": int(row.t), "seat": int(row.seat), "team": int(row.team), "hit": hit,
                             "victim": None if pd.isna(row.victim) else int(row.victim),
                             "x0": x0, "z0": z0, "x1": x1, "z1": z1})
    return out


# ---------------------------------------------------------------- drawing

def _style(ax) -> None:
    ax.set_facecolor(PAPER)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=INK_MUTED, labelsize=7, length=0)


def _halo(width: float = 2.5):
    return [path_effects.withStroke(linewidth=width, foreground=PAPER)]


def draw_terrain(ax, mapdata: pw_mapdata.MapData, bbox=None) -> None:
    """Light warm height shading, water, cover and trenches; off-island stays paper."""
    heights = np.where(mapdata.off_island, np.nan, mapdata.heights.astype(float))
    terrain = LinearSegmentedColormap.from_list("pw_terrain", [TERRAIN_LOW, TERRAIN_HIGH])
    terrain.set_bad(PAPER)
    ax.imshow(heights, extent=mapdata.extent, cmap=terrain, interpolation="bilinear", zorder=0)
    cover = mapdata.blocked & ~mapdata.off_island & ~mapdata.water
    for mask, color, alpha in ((mapdata.water, WATER, 1.0), (cover, COVER, 0.9), (mapdata.trench, TRENCH, 0.55)):
        ax.imshow(np.ma.masked_where(~mask, mask), extent=mapdata.extent, cmap=ListedColormap([color]),
                  alpha=alpha, interpolation="nearest", zorder=1)
    x0, x1, z1, z0 = mapdata.extent
    if bbox:
        x0, z0, x1, z1 = bbox
    ax.set_xlim(x0, x1)
    ax.set_ylim(z1, z0)  # world z grows downward, as in the viewer
    ax.set_aspect("equal")
    _style(ax)


def draw_hearts(ax, ep, owners: dict[int, int], fontsize: float = 7) -> list[dict]:
    plotted = []
    for heart in ep.meta["hearts"]:
        owner = owners.get(heart["idx"], -1)
        color = TEAM_COLORS.get(owner, NEUTRAL)
        x, z = heart["pos"]
        ax.add_patch(plt.Circle((x, z), CAPTURE_RADIUS, facecolor=color, alpha=0.24, edgecolor="none", zorder=2))
        ax.plot(x, z, marker="h", markersize=11, color=color, markeredgecolor=PAPER, markeredgewidth=1.2, zorder=6)
        ax.annotate(f"H{heart['idx']}", (x, z), xytext=(7, 6), textcoords="offset points", fontsize=fontsize,
                    color=INK_SUBTLE, path_effects=_halo(), zorder=9, clip_on=True)
        plotted.append({"heart": heart["idx"], "x": x, "z": z, "owner": owner})
    return plotted


def _arrow(ax, start, end, color) -> None:
    ax.annotate("", xy=end, xytext=start, zorder=5, annotation_clip=True,
                arrowprops={"arrowstyle": "-|>,head_length=0.55,head_width=0.3", "color": color, "lw": 0,
                            "shrinkA": 0, "shrinkB": 0})


def draw_trails(ax, ep, t0: int, t1: int, seats: list[int], label_size: float = 7) -> list[dict]:
    states = ep["states"]
    states = states[(states.t >= t0) & (states.t <= t1) & states.seat.isin(seats)]
    spawns = ep["spawns"]
    team = team_of(ep)
    plotted = []
    for seat in seats:
        color = TEAM_COLORS[team[seat]]
        spawn_ticks = [int(t) for t in spawns[(spawns.seat == seat) & (spawns.t > t0) & (spawns.t <= t1)].t]
        segments = trail_segments(states[states.seat == seat], spawn_ticks)
        for number, segment in enumerate(segments):
            xs, zs, ts = segment.x.to_numpy(float), segment.z.to_numpy(float), segment.t.to_numpy()
            ax.plot(xs, zs, color=color, lw=1.6, alpha=0.9, solid_capstyle="round", zorder=4)
            ax.plot(xs[0], zs[0], marker="o", markersize=3, color=color, zorder=5)
            for i in range(1, len(ts)):
                is_end = i == len(ts) - 1
                if is_end or (ts[i] - ts[0]) // ARROW_EVERY_TICKS != (ts[i - 1] - ts[0]) // ARROW_EVERY_TICKS:
                    if (xs[i], zs[i]) != (xs[i - 1], zs[i - 1]):
                        _arrow(ax, (xs[i - 1], zs[i - 1]), (xs[i], zs[i]), color)
            plotted.append({"seat": seat, "team": team[seat], "segment": number,
                            "points": [[int(t), int(x), int(z)] for t, x, z in zip(ts, xs, zs)]})
        _label_seat(ax, seat, segments, label_size)
    return plotted


def _label_seat(ax, seat: int, segments: list[pd.DataFrame], size: float) -> None:
    """Seat number at the last trail point that is inside the visible area."""
    (x0, x1), (z1, z0) = ax.get_xlim(), ax.get_ylim()
    for segment in reversed(segments):
        inside = segment[(segment.x >= x0) & (segment.x <= x1) & (segment.z >= z0) & (segment.z <= z1)]
        if len(inside):
            ax.annotate(str(seat), (inside.x.iloc[-1], inside.z.iloc[-1]), xytext=(4, -9), textcoords="offset points",
                        fontsize=size, color=INK, fontweight="bold", path_effects=_halo(), zorder=9, clip_on=True)
            return


def draw_events(ax, events: dict[str, list[dict]], shots: bool = True) -> None:
    if shots:
        for s in events["shots"]:
            ax.plot([s["x0"], s["x1"]], [s["z0"], s["z1"]], color=TEAM_COLORS[s["team"]],
                    lw=0.7 if s["hit"] else 0.6, alpha=0.6 if s["hit"] else 0.45,
                    ls="-" if s["hit"] else (0, (2, 2)), zorder=3)
    for b in events["blasts"]:
        ax.add_patch(plt.Circle((b["x"], b["z"]), b["radius"], fill=False, lw=1.1, ls="--",
                                edgecolor=TEAM_COLORS[b["team"]], zorder=6))
    for p in events["pickups"]:
        ax.plot(p["x"], p["z"], marker="^", markersize=7, color=TEAM_COLORS[p["team"]],
                markeredgecolor=PAPER, markeredgewidth=0.8, zorder=7)
    for c in events["captures"]:
        ax.plot(c["x"], c["z"], marker="D", markersize=9, color=TEAM_COLORS[c["team"]],
                markeredgecolor=INK, markeredgewidth=0.9, zorder=7)
    for d in events["deaths"]:
        ax.plot(d["x"], d["z"], marker="o", markersize=8, markerfacecolor="none",
                markeredgecolor=TEAM_COLORS[d["team"]], markeredgewidth=1.6, zorder=8)
    for k in events["kills"]:
        ax.plot(k["x"], k["z"], marker="x", markersize=8, color=TEAM_COLORS[k["team"]],
                markeredgewidth=2.0, zorder=8)


def legend_handles(shots: bool = True) -> list:
    handles = [Line2D([], [], color=TEAM_COLORS[0], lw=1.6, label="Ember trail"),
               Line2D([], [], color=TEAM_COLORS[1], lw=1.6, label="Azure trail"),
               Line2D([], [], ls="none", marker="x", color=INK, markeredgewidth=2, label="kill (killer's spot)"),
               Line2D([], [], ls="none", marker="o", markerfacecolor="none", markeredgecolor=INK, label="death"),
               Line2D([], [], ls="none", marker="D", color=INK_SUBTLE, markeredgecolor=INK, label="capture"),
               Line2D([], [], ls="none", marker="^", color=INK_SUBTLE, label="pickup"),
               Line2D([], [], ls="--", color=INK_SUBTLE, lw=1.1, label="grenade blast"),
               Line2D([], [], ls="none", marker="h", color=NEUTRAL, markersize=9, label="heart (owner at end)")]
    if shots:
        handles += [Line2D([], [], color=INK_SUBTLE, lw=0.8, label="shot, hit"),
                    Line2D([], [], color=INK_SUBTLE, lw=0.6, ls=(0, (2, 2)), label="shot, miss (short)")]
    return handles


def movement_panel(ax, ep, mapdata, t0: int, t1: int, seats: list[int], *, bbox=None, shots: bool = True,
                   title: str | None = None, label_size: float = 7) -> dict:
    """Draw one movement diagram; return the plotted data."""
    draw_terrain(ax, mapdata, bbox)
    hearts = draw_hearts(ax, ep, heart_owners_at(ep, t1), fontsize=label_size)
    events = window_events(ep, t0, t1, seats)
    draw_events(ax, events, shots)
    trails = draw_trails(ax, ep, t0, t1, seats, label_size)
    if title:
        ax.set_title(title, fontsize=9, color=INK, loc="left", fontfamily="serif", fontweight="bold")
    return {"episode_id": ep.episode_id, "from_tick": t0, "to_tick": t1, "seats": seats, "bbox": bbox,
            "state_every": int(ep["episodes"].iloc[0].state_every), "hearts_at_end": hearts,
            "trails": trails, "events": events}


def bbox_around(x: float, z: float, half: float, mapdata) -> tuple[float, float, float, float]:
    x0, x1, z1, z0 = mapdata.extent
    return (max(x0, x - half), max(z0, z - half), min(x1, x + half), min(z1, z + half))


def _save(fig, out: Path, data: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=130, facecolor=PAPER, bbox_inches="tight")
    plt.close(fig)
    out.with_suffix(".json").write_text(json.dumps(data, indent=1, default=_json_default) + "\n")


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if value is pd.NA:
        return None
    raise TypeError(type(value))


def plot_movement(episodes: list, out: Path, t0: int | None, t1: int | None, *, seats=None, team=None,
                  policy=None, bbox=None, shots: bool = True, panel_titles: list[str] | None = None) -> dict:
    """Small multiples: the same window on each episode (one panel per episode)."""
    columns = 1 if len(episodes) == 1 else 2
    rows = math.ceil(len(episodes) / columns)
    width = 12 if columns == 1 else 16
    fig, axes = plt.subplots(rows, columns, figsize=(width, rows * (7.6 if columns == 1 else 5.2)),
                             squeeze=False, facecolor=PAPER)
    panels = []
    for i, ep in enumerate(episodes):
        ax = axes.flat[i]
        end = int(ep["episodes"].iloc[0].ticks)
        a, b = (t0 or 0), min(t1 if t1 is not None else end, end)
        chosen = select_seats(ep, seats, team, policy)
        mapdata = pw_mapdata.map_for_episode(ep.meta)
        title = (panel_titles[i] if panel_titles else _short_id(ep.episode_id)) + f"   {clock(a)}–{clock(b)}"
        if a >= end:
            title += f"   (window starts after this match ended at {clock(end)}: nothing to draw)"
            chosen = []
        elif not chosen:
            title += "   (no seats match the filter)"
        elif policy:
            teams = {int(t) for t in ep["seats"][ep["seats"].seat.isin(chosen)].team}
            others = ep["seats"][~ep["seats"].team.isin(teams)].policy_name.dropna().unique()
            side = "/".join(pw_episodes.TEAM_NAMES[t].capitalize() for t in sorted(teams))
            title += f"   as {side}" + (f" vs {', '.join(sorted(others))}" if len(others) else "")
        panels.append(movement_panel(ax, ep, mapdata, a, b, chosen, bbox=bbox, shots=shots, title=title))
    for ax in axes.flat[len(episodes):]:
        ax.set_visible(False)
    fig.legend(handles=legend_handles(shots), loc="lower center", ncol=5, frameon=False, fontsize=8,
               labelcolor=INK_SUBTLE, bbox_to_anchor=(0.5, -0.02 if rows == 1 else 0.0))
    fig.text(0.01, 1.0, "Movement", fontsize=13, color=INK, fontfamily="serif", fontweight="bold", va="bottom")
    fig.text(0.01, 0.985, "Trails from state samples; seat number at each trail's end. Terrain: pale = low, "
             "dark tan = high, grey-blue = water, brown = cover and trenches.", fontsize=8, color=INK_MUTED, va="top")
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    data = {"kind": "movement", "panels": panels}
    _save(fig, out, data)
    return data


def _short_id(episode_id: str) -> str:
    return episode_id.replace("ereq_", "")[:13]


# ---------------------------------------------------------------- batch heatmaps

def symmetry_center(meta: dict) -> tuple[float, float]:
    """Centre of the map's 180-degree symmetry (midpoint of the two homes).

    Raises ValueError unless every heart rotates onto a heart about that point, so side
    normalization is never applied to an asymmetric (e.g. generated) map."""
    (ax_, az), (bx, bz) = meta["homes"][:2]
    cx, cz = (ax_ + bx) / 2, (az + bz) / 2
    hearts = {tuple(h["pos"]) for h in meta["hearts"]}
    for x, z in hearts:
        if not any(abs(2 * cx - x - hx) <= 1 and abs(2 * cz - z - hz) <= 1 for hx, hz in hearts):
            raise ValueError(f"map {meta['map'] or 'heartwick'} is not point-symmetric: cannot normalize sides")
    return cx, cz


def to_ember_side(frame: pd.DataFrame, meta: dict, xcol: str = "x", zcol: str = "z", team_col: str = "team") -> pd.DataFrame:
    """Rotate Azure (team 1) positions 180 degrees so both teams read as if they started on Ember's side."""
    cx, cz = symmetry_center(meta)
    out = frame.copy()
    azure = out[team_col] == 1
    out.loc[azure, xcol] = 2 * cx - out.loc[azure, xcol]
    out.loc[azure, zcol] = 2 * cz - out.loc[azure, zcol]
    return out


def policy_positions(episodes: list, policy: str | None, team: int | None = None,
                     normalize_side: bool = False) -> pd.DataFrame:
    """Alive state samples of the policy's seats across episodes (x, z, t, episode_id, seat, team)."""
    frames = []
    for ep in episodes:
        seats = select_seats(ep, team=team, policy=policy)
        st = ep["states"]
        rows = st[st.seat.isin(seats) & st.alive.astype(bool)][["episode_id", "t", "seat", "team", "x", "z"]]
        frames.append(to_ember_side(rows, ep.meta) if normalize_side else rows)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["episode_id", "t", "seat", "team", "x", "z"])


def policy_deaths(episodes: list, policy: str | None, team: int | None = None, normalize_side: bool = False) -> pd.DataFrame:
    frames = []
    for ep in episodes:
        seats = select_seats(ep, team=team, policy=policy)
        kills = ep["kills"]
        rows = kills[kills.victim.isin(seats)][["episode_id", "t", "victim", "victim_team", "seat", "weapon", "victim_x", "victim_z"]]
        frames.append(to_ember_side(rows, ep.meta, "victim_x", "victim_z", "victim_team") if normalize_side else rows)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def plot_heatmap(episodes: list, out: Path, *, policy=None, team=None, kind: str = "density",
                 normalize_side: bool = False) -> dict:
    mapdata = pw_mapdata.map_for_episode(episodes[0].meta)
    fig, ax = plt.subplots(figsize=(12, 7.6), facecolor=PAPER)
    draw_terrain(ax, mapdata)
    x0, x1, z1, z0 = mapdata.extent
    if kind == "density":
        points = policy_positions(episodes, policy, team, normalize_side)
        xs, zs = points.x.to_numpy(float), points.z.to_numpy(float)
        unit, what = "state samples", "Where the cogs were (alive)"
    else:
        points = policy_deaths(episodes, policy, team, normalize_side)
        xs, zs = points.victim_x.to_numpy(float), points.victim_z.to_numpy(float)
        unit, what = "deaths", "Where the cogs died"
    if len(xs):
        hb = ax.hexbin(xs, zs, gridsize=(48 if kind == "density" else 32), extent=(x0, x1, z0, z1), mincnt=1,
                       cmap=SEQUENTIAL, alpha=0.85, linewidths=0.2, edgecolors=PAPER, zorder=3)
        bar = fig.colorbar(hb, ax=ax, fraction=0.025, pad=0.01)
        bar.set_label(f"{unit} per hexagon", color=INK_MUTED, fontsize=8)
        bar.ax.tick_params(labelsize=7, colors=INK_MUTED)
        bar.outline.set_visible(False)
    draw_hearts(ax, episodes[0], {h["idx"]: h["owner"] for h in episodes[0].meta["hearts"]})
    who = policy_label(episodes, policy) or (pw_episodes.TEAM_NAMES[team] if team is not None else "all seats")
    side = "   (Azure rotated onto Ember's side)" if normalize_side else ""
    ax.set_title(f"{what}: {who}   {len(xs)} {unit}, {len(episodes)} episodes{side}", fontsize=10, color=INK,
                 loc="left", fontfamily="serif", fontweight="bold")
    data = {"kind": f"heatmap_{kind}", "policy": policy, "team": team, "episodes": [e.episode_id for e in episodes],
            "count": int(len(xs)), "points": [[float(x), float(z)] for x, z in zip(xs, zs)],
            "normalize_side": normalize_side, "note": "hearts drawn with their t=0 owners"}
    _save(fig, out, data)
    return data


def occupancy_grid(xs, zs, mapdata, cell: int = OCCUPANCY_CELL) -> tuple[np.ndarray, tuple]:
    x0, x1, z1, z0 = mapdata.extent
    edges_x = np.arange(x0, x1 + cell, cell)
    edges_z = np.arange(z0, z1 + cell, cell)
    grid, _, _ = np.histogram2d(np.asarray(zs, float), np.asarray(xs, float), bins=(edges_z, edges_x))
    return grid, (edges_x[0], edges_x[-1], edges_z[-1], edges_z[0])


def bhattacharyya(a: np.ndarray, b: np.ndarray) -> float | None:
    """Overlap of two occupancy histograms: sum(sqrt(p * q)) of the normalized grids.

    1 = identical distributions, 0 = never in the same cell. None when either is empty
    (same definition as crewrift heat_compare.py, but empty is unknown, not 0)."""
    if a.sum() == 0 or b.sum() == 0:
        return None
    return float(np.sqrt((a / a.sum()) * (b / b.sum())).sum())


def plot_occupancy(episodes: list, out: Path, policies: list[str], *, team=None, normalize_side: bool = True) -> dict:
    mapdata = pw_mapdata.map_for_episode(episodes[0].meta)
    grids, counts = [], []
    for policy in policies:
        points = policy_positions(episodes, policy, team, normalize_side)
        grid, extent = occupancy_grid(points.x, points.z, mapdata)
        grids.append(grid)
        counts.append(len(points))
    overlap = bhattacharyya(grids[0], grids[1])
    fig, axes = plt.subplots(1, 2, figsize=(16, 5.6), facecolor=PAPER)
    for ax, policy, grid, count in zip(axes, policies, grids, counts):
        draw_terrain(ax, mapdata)
        share = grid / grid.sum() if grid.sum() else grid
        ax.imshow(np.ma.masked_where(share == 0, np.sqrt(share)), extent=extent, cmap=SEQUENTIAL, alpha=0.8,
                  interpolation="nearest", zorder=3)
        draw_hearts(ax, episodes[0], {h["idx"]: h["owner"] for h in episodes[0].meta["hearts"]})
        ax.set_title(f"{policy_label(episodes, policy)}   {count} alive samples", fontsize=9, color=INK, loc="left",
                     fontfamily="serif", fontweight="bold")
    score = "n/a (a policy has no samples)" if overlap is None else f"{overlap:.3f}"
    fig.text(0.01, 1.0, f"Occupancy overlap (Bhattacharyya) {score}", fontsize=13, color=INK,
             fontfamily="serif", fontweight="bold", va="bottom")
    fig.text(0.01, 0.985, f"Share of alive samples per {OCCUPANCY_CELL}-unit cell (square-root shading). "
             "1.0 = the two policies occupy the map identically; 0 = never the same cell. "
             + ("Azure seats rotated 180° onto Ember's side, so side of the map does not count as a difference."
                if normalize_side else "Raw positions: a policy's side of the map counts as a difference."),
             fontsize=8, color=INK_MUTED, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    data = {"kind": "occupancy", "policies": policies, "team": team, "cell": OCCUPANCY_CELL,
            "normalize_side": normalize_side,
            "episodes": [e.episode_id for e in episodes], "samples": counts, "bhattacharyya": overlap,
            "extent": list(extent), "grids": [g.astype(int).tolist() for g in grids]}
    _save(fig, out, data)
    return data


# ---------------------------------------------------------------- timelines

def heart_intervals(ep) -> dict[int, list[tuple[int, int, int]]]:
    """Exact ownership per heart as (start_tick, end_tick, owner) intervals."""
    end = int(ep["episodes"].iloc[0].ticks)
    owners = heart_owners_at(ep, 0)
    since = {h: 0 for h in owners}
    spans = {h: [] for h in owners}
    caps = ep["captures"]
    for row in caps[caps.kind == "capture_complete"].sort_values("t").itertuples():
        h = int(row.heart)
        spans[h].append((since[h], int(row.t), owners[h]))
        owners[h], since[h] = int(row.team), int(row.t)
    for h in owners:
        spans[h].append((since[h], end, owners[h]))
    return spans


def timeline_axes(fig, ep, axes, moments: list[dict] | None = None) -> dict:
    """Meter, glory, events and heart-ownership strip on four stacked axes sharing x (seconds)."""
    episode = ep["episodes"].iloc[0]
    rate = int(episode.tick_rate)
    ts = ep["team_states"].sort_values("t")
    seconds = ts.t / rate
    meter_ax, glory_ax, event_ax, heart_ax = axes
    target = int(episode.meter_target_ticks) / rate
    for team in (0, 1):
        color = TEAM_COLORS[team]
        name = pw_episodes.TEAM_NAMES[team].capitalize()
        meter_ax.plot(seconds, ts[f"meter_ticks_{team}"] / rate, color=color, lw=2, label=name)
        glory_ax.plot(seconds, ts[f"glory_{team}"], color=color, lw=2, label=name)
        meter_ax.annotate(f"{name} {ts[f'meter_ticks_{team}'].iloc[-1] / rate:.0f}",
                          (seconds.iloc[-1], ts[f"meter_ticks_{team}"].iloc[-1] / rate), xytext=(4, 0),
                          textcoords="offset points", fontsize=8, color=INK, va="center")
        final = int(episode[f"glory_{team}"])
        glory_ax.annotate(f"{name} {ts[f'glory_{team}'].iloc[-1]:.0f} (final {final})",
                          (seconds.iloc[-1], ts[f"glory_{team}"].iloc[-1]), xytext=(4, 0),
                          textcoords="offset points", fontsize=8, color=INK, va="center")
    meter_ax.axhline(target, color=INK_MUTED, lw=0.8, ls=(0, (3, 3)))
    meter_ax.annotate(f"win at {target:.0f}", (0, target), xytext=(2, -10), textcoords="offset points",
                      fontsize=7, color=INK_MUTED)
    meter_ax.set_ylabel("meter (points)", fontsize=8, color=INK_MUTED)
    glory_ax.set_ylabel("glory (unsettled)", fontsize=8, color=INK_MUTED)

    kills = ep["kills"]
    caps = ep["captures"]
    completes = caps[caps.kind == "capture_complete"]
    for team in (0, 1):
        color = TEAM_COLORS[team]
        by_team = kills[(kills.team == team) & ~kills.friendly.astype(bool)]
        event_ax.plot(by_team.t / rate, np.full(len(by_team), 1.0 - team * 0.5 + 0.25), "|", color=color,
                      markersize=9, markeredgewidth=1.4)
        taken = completes[completes.team == team]
        event_ax.plot(taken.t / rate, np.full(len(taken), 1.0 - team * 0.5), "D", color=color,
                      markersize=6, markeredgecolor=INK, markeredgewidth=0.6)
    event_ax.set_yticks([1.25, 1.0, 0.75, 0.5])
    event_ax.set_yticklabels(["Ember kills", "Ember captures", "Azure kills", "Azure captures"], fontsize=7)
    event_ax.set_ylim(0.3, 1.45)

    spans = heart_intervals(ep)
    for row, heart in enumerate(sorted(spans)):
        for start, stop, owner in spans[heart]:
            heart_ax.broken_barh([(start / rate, (stop - start) / rate)], (row - 0.4, 0.8),
                                 facecolors=TEAM_COLORS.get(owner, "#ece5d6"), edgecolor=PAPER, linewidth=0.5)
    heart_ax.set_yticks(range(len(spans)))
    heart_ax.set_yticklabels([f"H{h}" for h in sorted(spans)], fontsize=7)
    heart_ax.invert_yaxis()
    heart_ax.set_xlabel("match time (m:ss)", fontsize=8, color=INK_MUTED)
    end_s = int(episode.ticks) / rate
    for ax in axes:
        _style(ax)
        ax.set_xlim(0, end_s * 1.08)
        ax.grid(axis="x", color=RULE, lw=0.6)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda s, _: f"{int(s // 60)}:{int(s % 60):02d}"))
    for ax in (meter_ax, glory_ax):
        ax.grid(axis="y", color=RULE, lw=0.6)
    for moment in moments or []:
        for ax in axes:
            ax.axvline(moment["t"] / rate, color=INK_MUTED, lw=0.7, ls=(0, (1, 2)), zorder=0)
        meter_ax.annotate(str(moment["rank"]), (moment["t"] / rate, 1.0), xycoords=("data", "axes fraction"),
                          xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=7,
                          color=INK, fontweight="bold", annotation_clip=False)
    return {"t": ts.t.tolist(), "meter_ticks": {t: ts[f"meter_ticks_{t}"].tolist() for t in (0, 1)},
            "glory": {t: ts[f"glory_{t}"].tolist() for t in (0, 1)},
            "kills": kills[["t", "seat", "team", "victim", "friendly"]].to_dict("records"),
            "captures": completes[["t", "heart", "team", "seat", "previous_owner"]].to_dict("records"),
            "heart_ownership": {h: spans[h] for h in spans}}


def plot_timeline(ep, out: Path, moments: list[dict] | None = None) -> dict:
    fig, axes = plt.subplots(4, 1, figsize=(12, 7.2), sharex=True, facecolor=PAPER,
                             gridspec_kw={"height_ratios": [3, 2.2, 1.2, 2.6]})
    data = timeline_axes(fig, ep, axes, moments)
    episode = ep["episodes"].iloc[0]
    fig.text(0.01, 1.0, f"Match timeline   {_short_id(ep.episode_id)}", fontsize=13, color=INK,
             fontfamily="serif", fontweight="bold", va="bottom")
    fig.text(0.01, 0.985, f"Meter and glory from state samples every {int(episode.state_every)} ticks; captures, "
             "kills and heart ownership are exact. The loser's glory is zeroed at the end (final in brackets).",
             fontsize=8, color=INK_MUTED, va="top")
    fig.tight_layout(rect=(0, 0, 0.94, 0.97))
    data = {"kind": "timeline", "episode_id": ep.episode_id, **data}
    _save(fig, out, data)
    return data


# ---------------------------------------------------------------- animation

def animate(ep, out: Path, t0: int, t1: int, seats: list[int], *, bbox=None, fps: int = 8) -> dict:
    from matplotlib.animation import FuncAnimation, PillowWriter

    mapdata = pw_mapdata.map_for_episode(ep.meta)
    states = ep["states"]
    states = states[(states.t >= t0) & (states.t <= t1) & states.seat.isin(seats)]
    frames = sorted(states.t.unique())[::max(1, GIF_STEP_TICKS // max(1, int(ep["episodes"].iloc[0].state_every)))]
    if len(frames) > GIF_MAX_FRAMES:
        frames = frames[:: math.ceil(len(frames) / GIF_MAX_FRAMES)]
    fig, ax = plt.subplots(figsize=(10, 6.2), facecolor=PAPER)
    team = team_of(ep)
    spawns = ep["spawns"]

    def draw(frame_tick):
        ax.clear()
        draw_terrain(ax, mapdata, bbox)
        draw_hearts(ax, ep, heart_owners_at(ep, frame_tick))
        recent = window_events(ep, max(t0, frame_tick - TICK_RATE), frame_tick, seats)
        draw_events(ax, recent)
        for seat in seats:
            tail = states[(states.seat == seat) & (states.t <= frame_tick) & (states.t > frame_tick - GIF_TAIL_TICKS)]
            spawn_ticks = [int(t) for t in spawns[(spawns.seat == seat) & (spawns.t > frame_tick - GIF_TAIL_TICKS)].t]
            color = TEAM_COLORS[team[seat]]
            for segment in trail_segments(tail, spawn_ticks):
                ax.plot(segment.x, segment.z, color=color, lw=1.4, alpha=0.8, zorder=4)
            now = tail[tail.t == frame_tick]
            if len(now) and bool(now.alive.iloc[0]):
                ax.plot(now.x.iloc[0], now.z.iloc[0], "o", color=color, markeredgecolor=PAPER, markersize=7, zorder=8)
                ax.annotate(str(seat), (now.x.iloc[0], now.z.iloc[0]), xytext=(4, 4), textcoords="offset points",
                            fontsize=7, color=INK, path_effects=_halo(), zorder=9, clip_on=True)
        ax.set_title(f"{_short_id(ep.episode_id)}   {clock(frame_tick)}  (tick {frame_tick})", fontsize=9,
                     color=INK, loc="left", fontfamily="serif")

    out.parent.mkdir(parents=True, exist_ok=True)
    FuncAnimation(fig, draw, frames=frames).save(out, writer=PillowWriter(fps=fps), dpi=80,
                                                  savefig_kwargs={"facecolor": PAPER})
    plt.close(fig)
    data = {"kind": "gif", "episode_id": ep.episode_id, "from_tick": t0, "to_tick": t1, "seats": seats,
            "frames": [int(f) for f in frames], "fps": fps}
    out.with_suffix(".json").write_text(json.dumps(data, indent=1) + "\n")
    return data


# ---------------------------------------------------------------- CLI

def load(roots: list[Path], tag: str | None, fine_window: tuple[int, int] | None = None):
    """Verified episodes (sorted) and the batch; failures are printed, never dropped silently."""
    options = pw_episodes.TraceOptions(window=fine_window) if fine_window else None
    batch = pw_episodes.load_batch(roots, tag=tag, options=options)
    for path, code, message in batch.failures:
        print(f"FAILED [{code}] {path}: {message}  (not plotted)")
    print(f"loaded {len(batch.episodes)} episodes, {len(batch.failures)} failed")
    return sorted(batch.episodes, key=lambda e: e.episode_id), batch


def _bbox(text: str | None):
    return tuple(float(v) for v in text.split(",")) if text else None


# ---------------------------------------------------------------- CLI

COMMANDS = ("movement", "heatmap", "occupancy", "timeline", "gif")
WINDOW_COMMANDS = ("movement", "gif")


def match_end(ep) -> int:
    return int(ep["episodes"].iloc[0].ticks)


def check_window(episodes: list, t0: int | None, t1: int | None) -> dict:
    """Usage error unless the window overlaps at least one match; reports clamping per episode."""
    ends = {ep.episode_id: match_end(ep) for ep in episodes}
    lengths = [f"{episode_id}: ticks 0-{end} (0:00-{clock(end)})" for episode_id, end in sorted(ends.items())]
    if t0 is not None and t1 is not None and t1 <= t0:
        raise pw_cli.UsageError(f"--to {clock(t1)} (tick {t1}) must be after --from {clock(t0)} (tick {t0})")
    if t0 is not None and all(t0 >= end for end in ends.values()):
        raise pw_cli.UsageError(f"--from {clock(t0)} (tick {t0}) is at or after the end of every match; "
                                "pick a window inside a match", lengths)
    starts_after = sorted(i for i, end in ends.items() if t0 is not None and t0 >= end)
    clamped = sorted(i for i, end in ends.items() if t1 is not None and t1 > end and i not in starts_after)
    for episode_id in clamped:
        print(f"note: --to {clock(t1)} is past the end of {episode_id} ({clock(ends[episode_id])}); "
              "clamped to its last tick")
    for episode_id in starts_after:
        print(f"note: the window starts after {episode_id} ended ({clock(ends[episode_id])}); its panel is empty")
    return {"from_tick": t0, "to_tick": t1, "match_end_ticks": ends, "clamped_to_end": clamped,
            "starts_after_end": starts_after}


def check_seats(episodes: list, seats: list[int] | None, team: int | None, policies: list[str] | None) -> None:
    """Usage error for seats no episode has, a policy no episode has, or filters that match no seat anywhere."""
    valid_seats = sorted({int(s) for ep in episodes for s in ep["seats"].seat})
    unknown = sorted(set(seats or []) - set(valid_seats))
    if unknown:
        raise pw_cli.UsageError(f"--seats {unknown} not in these episodes", valid_seats)
    for policy in policies or []:
        pw_cli.require_policy(episodes, policy)
    for policy in (policies or [None])[:1]:
        if (seats or team is not None or policy) and not any(select_seats(ep, seats, team, policy) for ep in episodes):
            raise pw_cli.UsageError(f"no seat matches --seats {seats} --team {team} --policy {policy} in any episode")


def default_output(command: str, episodes: list, args, t0: int | None, t1: int | None) -> Path:
    """<lab>/analysis/pw_viz/<episode id | batch-hash>/<command>[-selectors].<png|gif>: same inputs, same path."""
    ids = sorted(ep.episode_id for ep in episodes)
    where = (_short_id(ids[0]) if len(ids) == 1
             else "batch-" + hashlib.sha1("\n".join(ids).encode()).hexdigest()[:10]).replace(":", "_")
    parts = [command]
    if command == "heatmap":
        parts.append(args.kind)
    if command in WINDOW_COMMANDS and (t0 is not None or t1 is not None):
        parts.append(f"t{t0 or 0}-{t1 if t1 is not None else 'end'}")
    if args.team is not None:
        parts.append(f"team{args.team}")
    if args.seats:
        parts.append("seats" + args.seats.replace(",", "_"))
    for policy in args.policy or []:
        parts.append(re.sub(r"[^A-Za-z0-9.]+", "_", policy)[:40])
    suffix = ".gif" if command == "gif" else ".png"
    return pw_cli.default_out("pw_viz", where, "-".join(parts) + suffix)


def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("pw_viz", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/pw_viz.py movement EPISODE_DIR --from 0:40 --to 1:05 --seats 5 --json",
        "uv run python paintbot_pw_lab/tools/pw_viz.py timeline EPISODE_DIR --json",
        "uv run python paintbot_pw_lab/tools/pw_viz.py heatmap ROOT --policy james-pw --kind deaths --normalize-side",
        "uv run python paintbot_pw_lab/tools/pw_viz.py occupancy ROOT --policy A --policy B"])
    parser.add_argument("command", choices=COMMANDS, help="what to draw")
    parser.add_argument("roots", nargs="+", type=Path, help="episode dirs, batch dirs or NAME.replay files")
    parser.add_argument("--out", type=Path, help="output PNG/GIF path (the JSON lands beside it); default "
                                                 "paintbot_pw_lab/analysis/pw_viz/<episode or batch>/<command>...")
    parser.add_argument("--from", dest="start", help="window start (movement, gif): ticks 1500, seconds 62.5s or m:ss 1:10")
    parser.add_argument("--to", dest="stop", help="window end (movement, gif); clamped to the match end")
    parser.add_argument("--seats", help="comma-separated seats, e.g. --seats 5,7")
    parser.add_argument("--team", type=int, choices=(0, 1), help="0 = Ember (even seats), 1 = Azure (odd seats)")
    parser.add_argument("--policy", action="append",
                        help="policy_key or policy_name (occupancy: give it twice to compare two policies)")
    parser.add_argument("--kind", choices=("density", "deaths"), default="density", help="heatmap kind")
    parser.add_argument("--bbox", help="zoom to world box x0,z0,x1,z1, e.g. --bbox 0,-2500,4000,1000")
    parser.add_argument("--no-shots", action="store_true", help="leave shot rays off")
    parser.add_argument("--normalize-side", action="store_true",
                        help="heatmap: rotate Azure positions onto Ember's side (point-symmetric maps only)")
    parser.add_argument("--raw-sides", action="store_true", help="occupancy: do not rotate Azure onto Ember's side")
    parser.add_argument("--fine", action="store_true", help="re-trace with every-tick states for the window")
    parser.add_argument("--tag", help="pw_trace build (default: tools/release.env)")
    return parser


def parse_selectors(args) -> tuple[int | None, int | None, list[int] | None, tuple | None]:
    try:
        t0, t1 = parse_time(args.start), parse_time(args.stop)
    except ValueError as error:
        raise pw_cli.UsageError(str(error)) from error
    if args.command not in WINDOW_COMMANDS and (t0 is not None or t1 is not None):
        raise pw_cli.UsageError(f"--from/--to apply to {' and '.join(WINDOW_COMMANDS)} only, not {args.command}")
    try:
        seats = [int(s) for s in args.seats.split(",")] if args.seats else None
        bbox = _bbox(args.bbox)
    except ValueError as error:
        raise pw_cli.UsageError(f"bad --seats or --bbox ({error}); e.g. --seats 5,7 --bbox 0,-2500,4000,1000") from error
    if bbox is not None and len(bbox) != 4:
        raise pw_cli.UsageError(f"--bbox needs 4 numbers x0,z0,x1,z1, got {args.bbox!r}")
    if args.command == "occupancy" and (not args.policy or len(args.policy) != 2):
        raise pw_cli.UsageError("occupancy needs --policy A --policy B")
    return t0, t1, seats, bbox


def run_cli(args, report: pw_cli.Report) -> dict | None:
    t0, t1, seats, bbox = parse_selectors(args)
    fine = (t0 or 0, t1 if t1 is not None else 10**6) if args.fine else None
    episodes, batch = load(args.roots, args.tag, fine)
    report.add_batch(batch)
    if not episodes:
        print("nothing to plot")
        return None
    check_seats(episodes, seats, args.team, args.policy)
    window = check_window(episodes if args.command == "movement" else episodes[:1], t0, t1) \
        if args.command in WINDOW_COMMANDS else None
    policy = args.policy[0] if args.policy else None
    out = args.out or default_output(args.command, episodes, args, t0, t1)
    written = []
    if args.command == "movement":
        plot_movement(episodes, out, t0, t1, seats=seats, team=args.team, policy=policy, bbox=bbox,
                      shots=not args.no_shots)
        written.append(out)
    elif args.command == "heatmap":
        plot_heatmap(episodes, out, policy=policy, team=args.team, kind=args.kind,
                     normalize_side=args.normalize_side)
        written.append(out)
    elif args.command == "occupancy":
        plot_occupancy(episodes, out, args.policy, team=args.team, normalize_side=not args.raw_sides)
        written.append(out)
    elif args.command == "timeline":
        for ep in episodes:
            target = out if len(episodes) == 1 else out.with_name(f"{out.stem}-{_short_id(ep.episode_id)}{out.suffix}")
            plot_timeline(ep, target)
            written.append(target)
    elif args.command == "gif":
        ep = episodes[0]
        if len(episodes) > 1:
            print(f"note: gif draws one episode; using {ep.episode_id} (the first of {len(episodes)})")
        end = match_end(ep)
        animate(ep, out, t0 or 0, min(t1 if t1 is not None else end, end),
                select_seats(ep, seats, args.team, policy), bbox=bbox)
        written.append(out)
    for path in written:
        print(f"wrote {path} and {path.with_suffix('.json')}")
        report.output(path)
        report.output(path.with_suffix(".json"))
    report.suggest(f"Read {written[0]} (look at the image) and check one event against pw_episodes.py --sql")
    return {"images": [str(p) for p in written], "data": [str(p.with_suffix(".json")) for p in written],
            "window": window, "episodes": [ep.episode_id for ep in episodes]}


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), run_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
