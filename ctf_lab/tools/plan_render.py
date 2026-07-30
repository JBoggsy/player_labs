"""Render a battle plan (battle_plans/<name>.json) to one PNG per phase.

The agent-side visualizer for the co-general loop: the browser plan editor is
the human's surface; this gives the agent (or a doc/report) the same picture —
walls, faint POI underlay, group arrows with waypoints, hold/watch markers,
enemy-belief rings — matching the editor's drawing conventions.

Usage:
    uv run python ctf_lab/tools/plan_render.py battle_plans/staged_push_top.json \
        [-o out_dir] [--scale 1.0]

Writes <out_dir>/<plan>_p<N>_<phase>.png (out_dir defaults next to the plan).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

LAB = Path(__file__).resolve().parent.parent
MAP_W, MAP_H = 1235, 659
SPAWN = (110, 329)

INK = (26, 24, 21)
PAPER = (245, 242, 236)
WALL = (201, 193, 178)
POI_FAINT = (170, 163, 150)
BLUE = (46, 92, 179)
GROUP_COLORS = [(179, 64, 46), (138, 109, 31), (63, 125, 58), (91, 74, 138),
                (163, 91, 44), (44, 122, 138)]


def load_font(size: int):
    for cand in ("/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"):
        try:
            return ImageFont.truetype(cand, size)
        except OSError:
            continue
    return ImageFont.load_default()


class Poi:
    def __init__(self):
        d = json.loads((LAB / "ctf/beacon/mapdata/points_of_interest.json").read_text())
        self.points = d.get("points", [])
        self.areas = d.get("areas", [])

    def resolve(self, loc):
        if loc is None:
            return None
        if isinstance(loc, dict):
            return (loc["x"], loc["y"])
        for p in self.points:
            if p["name"] == loc:
                return (p["x"], p["y"])
        for a in self.areas:
            if a["name"] == loc:
                return (a["cx"], a["cy"])
        return None


def active_groups(plan: dict, upto: int) -> dict[str, list[int]]:
    g = {k: list(v) for k, v in (plan.get("groups") or {}).items()}
    for i in range(upto + 1):
        for parent, kids in (plan["phases"][i].get("splits") or {}).items():
            if parent in g:
                del g[parent]
                for k, seats in kids.items():
                    g[k] = list(seats)
    return g


def group_starts(plan: dict, poi: Poi, upto: int) -> dict[str, tuple[int, int]]:
    loc = {k: SPAWN for k in (plan.get("groups") or {})}
    for i in range(upto):
        ph = plan["phases"][i]
        for parent, kids in (ph.get("splits") or {}).items():
            frm = loc.pop(parent, SPAWN)
            for k in kids:
                loc[k] = frm
        for o in ph.get("orders") or []:
            if o.get("kind") == "watch":
                continue
            t = poi.resolve(o.get("to") or o.get("at"))
            if t:
                loc[o["group"]] = t
    for parent, kids in (plan["phases"][upto].get("splits") or {}).items():
        frm = loc.pop(parent, SPAWN)
        for k in kids:
            loc[k] = frm
    return loc


def draw_arrowhead(d: ImageDraw.ImageDraw, x0, y0, x1, y1, col, size=11):
    a = math.atan2(y1 - y0, x1 - x0)
    pts = [(x1, y1),
           (x1 - size * math.cos(a - 0.45), y1 - size * math.sin(a - 0.45)),
           (x1 - size * math.cos(a + 0.45), y1 - size * math.sin(a + 0.45))]
    d.polygon(pts, fill=col)


def text_outlined(d, xy, s, font, fill):
    x, y = xy
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        d.text((x + dx, y + dy), s, font=font, fill=(250, 249, 246))
    d.text((x, y), s, font=font, fill=fill)


def render_phase(plan: dict, poi: Poi, wall: np.ndarray, idx: int, scale: float) -> Image.Image:
    ph = plan["phases"][idx]
    img = Image.new("RGB", (MAP_W, MAP_H), PAPER)
    px = np.array(img)
    px[wall] = WALL
    img = Image.fromarray(px)
    d = ImageDraw.Draw(img)
    f9, f10, f11, f13 = load_font(9), load_font(10), load_font(11), load_font(13)

    # Faint POI underlay.
    for a in poi.areas:
        x0, y0 = a["cx"] - a["w"] / 2, a["cy"] - a["h"] / 2
        d.rectangle([x0, y0, x0 + a["w"], y0 + a["h"]], outline=POI_FAINT)
        d.text((x0 + 3, y0 + 2), a["name"], font=f9, fill=POI_FAINT)
    for p in poi.points:
        d.ellipse([p["x"] - 2, p["y"] - 2, p["x"] + 2, p["y"] + 2], fill=POI_FAINT)

    groups = active_groups(plan, idx)
    names = sorted(groups)
    color = {n: GROUP_COLORS[i % len(GROUP_COLORS)] for i, n in enumerate(names)}
    starts = group_starts(plan, poi, idx)

    for e in ph.get("enemy_belief") or []:
        t = poi.resolve(e.get("at"))
        if not t:
            continue
        d.ellipse([t[0] - 13, t[1] - 13, t[0] + 13, t[1] + 13], outline=BLUE, width=2)
        d.ellipse([t[0] - 19, t[1] - 19, t[0] + 19, t[1] + 19], outline=BLUE)
        d.text((t[0] - 4, t[1] - 7), str(e.get("count", "?")), font=f13, fill=BLUE)
        if e.get("note"):
            text_outlined(d, (t[0] + 23, t[1] - 6), e["note"], f10, BLUE)

    for o in ph.get("orders") or []:
        col = color.get(o["group"], INK)
        target = poi.resolve(o.get("to") or o.get("at"))
        if not target:
            continue
        n = len(groups.get(o["group"], [])) or "?"
        kind = o.get("kind")
        if kind == "move":
            frm = starts.get(o["group"], SPAWN)
            pts = [frm] + [poi.resolve(v) for v in (o.get("via") or []) if poi.resolve(v)] + [target]
            for s in range(len(pts) - 1):
                d.line([pts[s], pts[s + 1]], fill=col, width=3)
            draw_arrowhead(d, *pts[-2], *pts[-1], col)
            for vx, vy in pts[1:-1]:
                d.ellipse([vx - 5, vy - 5, vx + 5, vy + 5], fill=(250, 249, 246), outline=col)
            d.ellipse([frm[0] - 8, frm[1] - 8, frm[0] + 8, frm[1] + 8], fill=col)
            d.text((frm[0] - 3, frm[1] - 6), str(n), font=f10, fill=(250, 249, 246))
        elif kind == "hold":
            d.rectangle([target[0] - 8, target[1] - 8, target[0] + 8, target[1] + 8], fill=col)
            d.text((target[0] - 3, target[1] - 6), str(n), font=f10, fill=(250, 249, 246))
            fc = poi.resolve(o.get("facing"))
            if fc:
                a = math.atan2(fc[1] - target[1], fc[0] - target[0])
                end = (target[0] + 46 * math.cos(a), target[1] + 46 * math.sin(a))
                d.line([target, end], fill=col, width=2)
        elif kind == "watch":
            d.ellipse([target[0] - 11, target[1] - 11, target[0] + 11, target[1] + 11], outline=col, width=2)
            text_outlined(d, (target[0] - 12, target[1] - 26), "watch", f9, col)
        loc = o.get("to") or o.get("at")
        lbl = o["group"] + (f" @ {loc}" if isinstance(loc, str) else "")
        text_outlined(d, (target[0] + 12, target[1] + 8), lbl, f10, col)

    # Header strip.
    hdr = f"{plan['name']} — phase {idx + 1}/{len(plan['phases'])}: {ph['name']}"
    entry = ph.get("entry", {}).get("prose", "")
    text_outlined(d, (10, 8), hdr, f13, INK)
    if entry:
        text_outlined(d, (10, 26), f"entry: {entry}", f11, (95, 90, 82))
    intent = ph.get("intent", "")
    if intent:
        words, line, lines = intent.split(), "", []
        for w in words:
            if len(line) + len(w) > 95:
                lines.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        lines.append(line)
        for i, ln in enumerate(lines[:3]):
            text_outlined(d, (10, MAP_H - 14 * (min(len(lines), 3) - i) - 8), ln, f11, (95, 90, 82))

    if scale != 1.0:
        img = img.resize((int(MAP_W * scale), int(MAP_H * scale)), Image.LANCZOS)
    return img


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("--scale", type=float, default=1.0)
    args = ap.parse_args()

    plan = json.loads(args.plan.read_text())
    poi = Poi()
    wall = np.load(LAB / "ctf/beacon/mapdata/nav.npz")["wall"]
    out_dir = args.out or args.plan.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, ph in enumerate(plan["phases"]):
        img = render_phase(plan, poi, wall, i, args.scale)
        path = out_dir / f"{plan['name']}_p{i + 1}_{ph['name']}.png"
        img.save(path)
        print(path, file=sys.stderr)


if __name__ == "__main__":
    main()
