#!/usr/bin/env python3
"""Score path predictions against ground truth at visible→obscured transitions.

The moment a crewmate leaves crewborg's view is exactly when prediction matters:
"where were they going?" This tool finds every such transition across one or many
episodes in a built crewrift-event-warehouse, captures the prediction *at the
instant they vanish*, then uses the replay's ground-truth ``player_state`` to see
where they actually went — and reports whether the predicted **destination room**
matched the room they actually reached.

Outputs:
- **Raw metrics** to stdout + a CSV (one row per occlusion instance) and an
  aggregate destination-room match rate.
- **Sampled overlay images** (one PNG per sampled instance): the map with the
  actual path (orange) vs the predicted top-k paths (blue, weighted by
  probability), the occlusion-start dot, and the predicted vs actual destination
  rooms — so each prediction's accuracy is legible at a glance.

Run (matplotlib is pulled in for images; duckdb is a warehouse dep):
    uv run --with matplotlib --with duckdb python \\
      crewrift_lab/crewrift/crewborg/tools/path_prediction_eval.py \\
      --warehouse /tmp/xp_imp_warehouse --episodes 20 --images 40 --out /tmp/pred_eval

Definitions / knobs:
- ``--min-occlusion`` (default 24 ticks): ignore blink-length occlusions.
- ``--horizon`` (default 240 ticks): a prediction made at onset is scored against
  the room reached by re-acquisition OR onset+horizon, whichever comes first — a
  long wander shouldn't be blamed on the onset prediction.
- Match is **destination ROOM only** (predicted top candidate's room == actual
  room reached). The actual room comes straight from ``player_state.room``.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import replay_frames as rf  # noqa: E402
from path_prediction_ui import build_nav, run_predictions  # noqa: E402


@dataclass
class Instance:
    episode_id: str
    slot: int
    policy: str
    onset_tick: int
    reacquire_tick: int | None
    horizon_tick: int
    onset_room: str | None
    pred_room: str | None
    pred_prob: float
    actual_room: str | None
    match: bool
    changed_rooms: bool
    endpoint_err: float | None
    pred_path: list
    actual_path: list
    pred_dest: list | None
    actual_pos: list | None


def _task_rooms(map_dict: dict) -> dict[int, str]:
    return {int(t["id"]): t.get("room", "") for t in map_dict.get("tasks", [])}


def _dest_room(label: str, task_rooms: dict[int, str]) -> str | None:
    """The room a candidate's destination sits in. ``room:Name`` -> Name;
    ``task:i:..`` -> the task's room."""

    if label.startswith("room:"):
        return label.split("room:", 1)[1]
    if label.startswith("task:"):
        parts = label.split(":")
        try:
            return task_rooms.get(int(parts[1]))
        except (ValueError, IndexError):
            return None
    return None


def _room_at(positions, tick: int, slot: int) -> str | None:
    p = positions.get(tick, {}).get(slot)
    return p[3] if p else None


def _pos_at(positions, tick: int, slot: int):
    p = positions.get(tick, {}).get(slot)
    return (p[0], p[1]) if p else None


def occlusion_instances(fr: rf.ReplayFrames, frames: list[dict], slot: int,
                        min_occlusion: int, horizon: int) -> list[Instance]:
    """Find visible→obscured transitions for ``slot`` and score each."""

    task_rooms = _task_rooms(fr.map)
    by_tick = {f["tick"]: f for f in frames}
    seen = fr.visible.get(slot, set())
    ticks = fr.ticks
    policy = fr.players.get(slot, {}).get("policy") or "?"

    out: list[Instance] = []
    prev_seen = False
    onset = None
    for t in ticks:
        s = t in seen and (fr.positions.get(t, {}).get(slot, (0, 0, False, ""))[2])
        if prev_seen and not s:
            onset = t  # they just left view (last visible was the prior tick)
        elif not prev_seen and s and onset is not None:
            # re-acquired at t; close the occlusion that began at `onset`
            self_close(out, fr, by_tick, slot, policy, onset, t, min_occlusion, horizon, task_rooms)
            onset = None
        prev_seen = s
    if onset is not None:  # occluded through end of episode
        self_close(out, fr, by_tick, slot, policy, onset, None, min_occlusion, horizon, task_rooms)
    return out


def self_close(out, fr, by_tick, slot, policy, onset, reacquire, min_occlusion, horizon, task_rooms):
    end = reacquire if reacquire is not None else fr.ticks[-1]
    if end - onset < min_occlusion:
        return
    # The prediction we held the instant they vanished: the frame at `onset-?` —
    # use the last frame at/just-before onset (onset is the first occluded tick, so
    # the prediction from the previous visible tick is what we carry in).
    onset_frame = by_tick.get(onset)
    if onset_frame is None or not onset_frame.get("candidates"):
        return
    top = onset_frame["candidates"][0]
    pred_room = _dest_room(top["label"], task_rooms)
    pred_prob = top["prob"]

    horizon_tick = min(end, onset + horizon)
    actual_room = _room_at(fr.positions, horizon_tick, slot)
    actual_pos = _pos_at(fr.positions, horizon_tick, slot)

    # actual path: ground-truth positions through the occlusion (to horizon)
    actual_path = [(_pos_at(fr.positions, t, slot)) for t in fr.ticks
                   if onset <= t <= horizon_tick and _pos_at(fr.positions, t, slot)]

    # predicted coasted endpoint at the horizon tick (where the predictor thinks
    # they are then) — for the endpoint-error readout.
    horizon_frame = by_tick.get(horizon_tick)
    endpoint_err = None
    if horizon_frame and horizon_frame.get("candidates") and actual_pos:
        pp = horizon_frame["candidates"][0]["pred"]
        endpoint_err = ((pp[0] - actual_pos[0]) ** 2 + (pp[1] - actual_pos[1]) ** 2) ** 0.5

    onset_room = _room_at(fr.positions, onset, slot)
    out.append(Instance(
        episode_id=fr.episode_id, slot=slot, policy=policy,
        onset_tick=onset, reacquire_tick=reacquire, horizon_tick=horizon_tick,
        onset_room=onset_room, pred_room=pred_room, pred_prob=pred_prob, actual_room=actual_room,
        match=(pred_room is not None and pred_room == actual_room),
        changed_rooms=(onset_room is not None and actual_room is not None and onset_room != actual_room),
        endpoint_err=endpoint_err,
        pred_path=top["path"], actual_path=actual_path,
        pred_dest=top["path"][-1] if top["path"] else None, actual_pos=actual_pos,
    ))


def render_image(inst: Instance, map_dict: dict, onset_candidates: list, out_path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.set_facecolor("#0e1116")
    fig.patch.set_facecolor("#0e1116")
    for r in map_dict.get("rooms", []):
        ax.add_patch(plt.Rectangle((r["x"], r["y"]), r["w"], r["h"], fill=False, edgecolor="#39424f", lw=0.7))
        ax.text(r["x"] + 3, r["y"] + 12, r["name"], color="#55606b", fontsize=6)

    # predicted top-k paths, weighted by prob
    for c in onset_candidates[:6]:
        p = c["path"]
        if len(p) >= 2:
            xs, ys = zip(*p)
            ax.plot(xs, ys, color="#58a6ff", alpha=max(0.08, c["prob"]), lw=1 + 3 * c["prob"])
    # actual path
    if len(inst.actual_path) >= 2:
        xs, ys = zip(*inst.actual_path)
        ax.plot(xs, ys, color="#f0883e", lw=2.0, label="actual")
    # markers
    if inst.actual_path:
        ax.scatter(*inst.actual_path[0], c="#ffffff", s=40, zorder=5, label="onset (left view)")
    if inst.pred_dest:
        ax.scatter(*inst.pred_dest, c="#58a6ff", marker="D", s=55, zorder=5, label=f"pred dest [{inst.pred_room}]")
    if inst.actual_pos:
        ax.scatter(*inst.actual_pos, c="#f0883e", marker="*", s=120, zorder=5, label=f"actual end [{inst.actual_room}]")

    ok = "MATCH" if inst.match else "miss"
    ax.set_title(f"{inst.episode_id[:14]} slot{inst.slot}({inst.policy}) "
                 f"t{inst.onset_tick}→{inst.horizon_tick}  pred={inst.pred_room}({inst.pred_prob:.2f}) "
                 f"actual={inst.actual_room}  [{ok}]",
                 color="#e6edf3", fontsize=8)
    ax.set_xlim(0, map_dict["width"]); ax.set_ylim(map_dict["height"], 0)
    ax.set_aspect("equal"); ax.axis("off")
    ax.legend(loc="upper right", fontsize=6, facecolor="#161b22", labelcolor="#e6edf3", framealpha=0.8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, facecolor="#0e1116")
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--warehouse", required=True)
    ap.add_argument("--episode", help="A single episode_id; omit to sweep --episodes from the warehouse.")
    ap.add_argument("--episodes", type=int, default=10, help="How many episodes to sweep when --episode is absent.")
    ap.add_argument("--min-occlusion", type=int, default=24)
    ap.add_argument("--horizon", type=int, default=240)
    ap.add_argument("--images", type=int, default=30, help="Number of instances to render as PNGs (sampled).")
    ap.add_argument("--out", default="/tmp/pred_eval")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    import duckdb
    con = duckdb.connect()
    if args.episode:
        episode_ids = [args.episode]
    else:
        rows = con.execute(
            "SELECT DISTINCT episode_id FROM "
            f"read_parquet('{args.warehouse}/episode_players.parquet') LIMIT {args.episodes}"
        ).fetchall()
        episode_ids = [r[0] for r in rows]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_instances: list[Instance] = []
    onset_cands: dict[int, list] = {}  # id(instance) -> onset candidate list (for images)
    maps: dict[str, dict] = {}
    for eid in episode_ids:
        try:
            fr = rf.load(args.warehouse, eid)
        except SystemExit:
            continue
        nav, md = build_nav(fr)
        maps[eid] = fr.map
        # predict for every non-crewborg crew target (skip slot 0 = us, skip imposters)
        for slot, info in fr.players.items():
            if slot == 0 or info.get("role") != "crew":
                continue
            frames = run_predictions(fr, nav, md, slot)
            by_tick = {f["tick"]: f for f in frames}
            insts = occlusion_instances(fr, frames, slot, args.min_occlusion, args.horizon)
            for inst in insts:
                onset_cands[id(inst)] = by_tick.get(inst.onset_tick, {}).get("candidates", [])
            all_instances.extend(insts)
        print(f"  {eid[:18]}…: {len([i for i in all_instances if i.episode_id==eid])} instances", file=sys.stderr)

    scored = [i for i in all_instances if i.pred_room is not None]
    changed = [i for i in scored if i.changed_rooms]
    n = len(scored)

    def rate(items):
        m = sum(1 for i in items if i.match)
        return m, len(items), (100 * m / len(items) if items else 0.0)

    overall = rate(scored)
    changed_rate = rate(changed)
    buckets = []
    for lo, hi in [(0.0, 0.4), (0.4, 0.7), (0.7, 1.01)]:
        buckets.append(((lo, hi), rate([i for i in scored if lo <= i.pred_prob < hi])))
    errs = sorted(i.endpoint_err for i in scored if i.endpoint_err is not None)
    med_err = errs[len(errs) // 2] if errs else None

    print("\n===== path-prediction accuracy at visible→obscured transitions =====")
    print(f"episodes: {len(episode_ids)}  occlusion instances (scored): {n}")
    if n:
        print(f"DESTINATION-ROOM MATCH (all):           {overall[0]}/{overall[1]} = {overall[2]:.1f}%")
        print(f"DESTINATION-ROOM MATCH (changed rooms): {changed_rate[0]}/{changed_rate[1]} = {changed_rate[2]:.1f}%  "
              "(the cases that matter — they actually left the room)")
        if med_err is not None:
            print(f"endpoint error px: median {med_err:.0f}  p90 {errs[int(len(errs)*0.9)]:.0f}")
        for (lo, hi), (m, b, r) in buckets:
            if b:
                print(f"  pred_prob [{lo:.1f},{hi:.1f}): {m}/{b} = {r:.0f}%")

    # CSV
    csv_path = out_dir / "instances.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["episode_id", "slot", "policy", "onset_tick", "horizon_tick", "occlusion_len",
                    "onset_room", "pred_room", "pred_prob", "actual_room", "changed_rooms", "match", "endpoint_err"])
        for i in scored:
            w.writerow([i.episode_id, i.slot, i.policy, i.onset_tick, i.horizon_tick,
                        i.horizon_tick - i.onset_tick, i.onset_room, i.pred_room, round(i.pred_prob, 3),
                        i.actual_room, int(i.changed_rooms), int(i.match),
                        round(i.endpoint_err) if i.endpoint_err else ""])
    print(f"\nraw rows -> {csv_path}")

    # sampled images (balance matches and misses among room-changers where possible)
    image_files: list[tuple[str, Instance]] = []
    if args.images and scored:
        rng = random.Random(args.seed)
        pool = changed if len(changed) >= args.images else scored
        sample = rng.sample(pool, min(args.images, len(pool)))
        img_dir = out_dir / "images"
        img_dir.mkdir(exist_ok=True)
        for k, inst in enumerate(sorted(sample, key=lambda i: (not i.match, i.onset_tick))):
            tag = "match" if inst.match else "MISS"
            fname = f"{k:03d}_{tag}_{inst.episode_id[:10]}_s{inst.slot}_t{inst.onset_tick}.png"
            render_image(inst, maps[inst.episode_id], onset_cands.get(id(inst), []), img_dir / fname)
            image_files.append((fname, inst))
        print(f"{len(image_files)} overlay images -> {img_dir}")

    # self-contained HTML report
    report_path = out_dir / "report.html"
    write_report(report_path, out_dir, len(episode_ids), n, overall, changed_rate, buckets,
                 med_err, scored, image_files, args)
    print(f"report -> {report_path}")
    return 0


def write_report(path, out_dir, n_episodes, n, overall, changed_rate, buckets, med_err,
                 scored, image_files, args) -> None:
    import base64

    def pct_bar(r):
        return f'<div class="bar"><i style="width:{r:.0f}%"></i></div>'

    rows = "".join(
        f"<tr class='{'m' if i.match else 'x'}'><td>{i.episode_id[:12]}…</td><td>{i.slot}</td>"
        f"<td>{i.policy}</td><td>{i.onset_room or '—'}</td><td>{i.pred_room or '—'}</td>"
        f"<td>{i.pred_prob:.2f}</td><td>{i.actual_room or '—'}</td>"
        f"<td>{'yes' if i.changed_rooms else 'no'}</td><td>{'✓' if i.match else '✗'}</td></tr>"
        for i in sorted(scored, key=lambda i: (i.episode_id, i.onset_tick))
    )
    bucket_rows = "".join(
        f"<tr><td>pred_prob [{lo:.1f},{hi:.1f})</td><td>{m}/{b}</td><td>{pct_bar(r)}</td><td class='p'>{r:.0f}%</td></tr>"
        for (lo, hi), (m, b, r) in buckets if b
    )
    imgs = ""
    for fname, inst in image_files:
        b64 = base64.b64encode((out_dir / "images" / fname).read_bytes()).decode()
        cls = "match" if inst.match else "miss"
        imgs += (f"<figure class='{cls}'><img src='data:image/png;base64,{b64}'>"
                 f"<figcaption>{'MATCH' if inst.match else 'MISS'} · {inst.policy} · "
                 f"{inst.onset_room}→{inst.actual_room} · pred {inst.pred_room} ({inst.pred_prob:.2f})</figcaption></figure>")

    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Path-prediction eval</title>
<style>
 body{{font:14px/1.5 ui-sans-serif,system-ui,sans-serif;background:#0e1116;color:#e6edf3;margin:0;padding:24px;max-width:1100px;}}
 h1{{font-size:20px;}} h2{{font-size:15px;color:#8b96a5;border-bottom:1px solid #283040;padding-bottom:4px;margin-top:28px;}}
 .big{{font-size:30px;font-weight:700;color:#58a6ff;}} .sub{{color:#8b96a5;}}
 .cards{{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0;}}
 .card{{background:#161b22;border:1px solid #283040;border-radius:8px;padding:14px 18px;min-width:200px;}}
 table{{border-collapse:collapse;width:100%;font-size:12px;margin-top:8px;}}
 th,td{{padding:4px 8px;border-bottom:1px solid #21262d;text-align:left;}} th{{color:#8b96a5;}}
 td.p{{text-align:right;color:#58a6ff;font-weight:600;}}
 tr.x td{{background:#1c1416;}} tr.m td{{background:#13201a;}}
 .bar{{height:7px;background:#0b0f14;border-radius:4px;width:90px;}} .bar>i{{display:block;height:100%;background:#58a6ff;border-radius:4px;}}
 figure{{margin:0 0 18px;background:#161b22;border:1px solid #283040;border-radius:8px;padding:8px;}}
 figure.miss{{border-color:#5a2a2a;}} figure.match{{border-color:#2a5a3a;}}
 figure img{{width:100%;border-radius:4px;}} figcaption{{font-size:12px;color:#8b96a5;padding:6px 4px 2px;}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;}}
 details summary{{cursor:pointer;color:#58a6ff;}}
</style></head><body>
<h1>Path-prediction accuracy — visible→obscured transitions</h1>
<p class="sub">{n_episodes} episode(s) · {n} scored occlusions · min-occlusion {args.min_occlusion}t · horizon {args.horizon}t ·
 warehouse <code>{args.warehouse}</code></p>

<h2>Results</h2>
<div class="cards">
  <div class="card"><div class="big">{overall[2]:.0f}%</div><div class="sub">destination-room match (all {overall[1]})</div></div>
  <div class="card"><div class="big">{changed_rate[2]:.0f}%</div><div class="sub">match when they CHANGED rooms ({changed_rate[1]})<br>— the cases that matter for "follow to next room"</div></div>
  <div class="card"><div class="big">{('%.0f'%med_err) if med_err is not None else '—'}px</div><div class="sub">median endpoint error</div></div>
</div>
<p>The headline metric is whether the predicted top destination's <b>room</b> equals the room the crewmate
actually reached (by re-acquisition or a {args.horizon}-tick horizon). The <b>changed-rooms</b> figure
isolates the occlusions where the target genuinely left the room — the predictions we'll rely on to follow a
crewmate to their next room (the "stayed put" cases are trivially correct and inflate the overall number).</p>

<h2>Calibration — match rate by prediction confidence</h2>
<p class="sub">A useful predictor is right more often when it is confident. Watch this stay monotonic as the module is tuned.</p>
<table><tr><th>confidence</th><th>n</th><th></th><th></th></tr>{bucket_rows}</table>

<h2>Representative instances</h2>
<p class="sub">Orange = actual path · blue = predicted routes (opacity ∝ probability) · white dot = left view · ◇ predicted dest · ★ actual end.</p>
<div class="grid">{imgs}</div>

<h2>All scored instances</h2>
<details><summary>show table ({n} rows)</summary>
<table><tr><th>episode</th><th>slot</th><th>policy</th><th>onset room</th><th>pred room</th><th>prob</th><th>actual room</th><th>changed</th><th>match</th></tr>{rows}</table>
</details>
</body></html>"""
    path.write_text(html)


if __name__ == "__main__":
    raise SystemExit(main())
