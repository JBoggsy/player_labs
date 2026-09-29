#!/usr/bin/env python3
"""Paintbot PW anomaly flags (lab tool T12): rule-based, tick-linked, thresholds printed.

Each flag is one row: (episode_id, flag, seat, team, policy_key, t_start, t_end, evidence,
detail). `evidence` says how far to trust it: exact (read from hash-checked trace events),
sampled (from state rows every `state_every` ticks, so runs are accurate to one sample) or
inferred (a heuristic). Flags:

  stuck               alive and walking (cmd_walk), walk goal unchanged, >= FLAG_STUCK_MIN_GOAL_DISTANCE from it, and
                      moved < FLAG_STUCK_MAX_DISPLACEMENT over >= FLAG_STUCK_WINDOW_TICKS  (sampled)
  oscillating         the walk goal flips back to where it was two changes ago
                      >= FLAG_OSCILLATION_MIN_FLIPS times within FLAG_OSCILLATION_WINDOW_TICKS  (sampled)
  idle_alive          alive with empty commands for >= FLAG_IDLE_MIN_TICKS  (sampled)
  vm_disabled_suspect empty commands from some tick to the end while alive >= pw_metrics.VM_DISABLED_MIN_IDLE_TICKS (inferred;
                      exact for our seats when the log has 'BASIC error:')
  death_alone         killed with no living teammate within FLAG_ALONE_RADIUS; detail says whether an
                      enemy had it in vision (needs --vis-every, else unknown)  (sampled)
  heart_lost_with_allies  a heart the team owned was captured while >= 1 living teammate was within
                      FLAG_HEART_DEFENSE_RADIUS  (sampled positions, exact capture)
  wasted_grenade      a grenade blast that damaged no enemy  (exact)
  friendly_fire       damage to a teammate (hits by one attacker within FLAG_FF_MERGE_TICKS merge)  (exact)
  long_wade           in water for >= FLAG_LONG_WADE_TICKS in one stretch  (exact)
  zero_glory_win      the winner's final glory is 0: the ladder scores it as a draw  (exact)

`losses(batch, policy)` sorts one policy's losses by Elo outcome (worst first) with that
policy's flag counts: the triage order for diagnosis. Contract: docs/tools/pw_flags.md.

CLI: uv run python paintbot_pw_lab/tools/pw_flags.py ROOT [ROOT ...] [--policy KEY] [--flags a,b] [--csv FILE] [--top N]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
import pw_episodes  # noqa: E402
import pw_metrics  # noqa: E402

# ---------------------------------------------------------------- named thresholds (printed with output)

FLAG_STUCK_WINDOW_TICKS = 72           # 3 s
FLAG_STUCK_MAX_DISPLACEMENT = 200      # units moved over the window
FLAG_STUCK_MIN_GOAL_DISTANCE = 200     # goal still this far away (else it arrived and is holding)
FLAG_OSCILLATION_WINDOW_TICKS = 144    # 6 s
FLAG_OSCILLATION_MIN_FLIPS = 3         # A->B->A counts one flip
FLAG_OSCILLATION_GOAL_MATCH = 100      # "back to where it was": within this many units
FLAG_OSCILLATION_MIN_JUMP = 300        # ...and the intermediate goal at least this far from it
FLAG_IDLE_MIN_TICKS = 48               # 2 s of empty commands while alive
FLAG_ALONE_RADIUS = 1000               # no living teammate this close at death = alone
FLAG_HEART_DEFENSE_RADIUS = 700        # teammates this close to a lost heart could have contested it
FLAG_FF_MERGE_TICKS = 48               # friendly hits by one attacker this close in time are one flag
FLAG_LONG_WADE_TICKS = 72              # 3 s in water in one stretch
VM_DISABLED_MIN_IDLE_TICKS = pw_metrics.VM_DISABLED_MIN_IDLE_TICKS

THRESHOLDS = {name: value for name, value in globals().items()
              if (name.startswith("FLAG_") or name.startswith("VM_")) and isinstance(value, int)}
FLAG_NAMES = ("stuck", "oscillating", "idle_alive", "vm_disabled_suspect", "death_alone", "heart_lost_with_allies",
              "wasted_grenade", "friendly_fire", "long_wade", "zero_glory_win")
COLUMNS = ["episode_id", "flag", "seat", "team", "policy_key", "t_start", "t_end", "evidence", "detail"]


def thresholds_line() -> str:
    return "thresholds: " + ", ".join(f"{k}={v}" for k, v in THRESHOLDS.items())


def _row(ep, flag, seat, t_start, t_end, evidence, detail, team=None) -> dict:
    seats = ep["seats"].set_index("seat")
    if seat is not None:
        team = int(seats.team[seat])
    return {"episode_id": ep["episodes"].iloc[0].episode_id, "flag": flag, "seat": seat, "team": team,
            "policy_key": seats.policy_key[seat] if seat is not None else None,
            "t_start": int(t_start), "t_end": int(t_end), "evidence": evidence,
            "detail": json.dumps(detail, sort_keys=True, default=_json_default)}


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    raise TypeError(type(value))


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, end] index pairs of consecutive True values."""
    runs, start = [], None
    for i, value in enumerate(mask):
        if value and start is None:
            start = i
        elif not value and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(mask) - 1))
    return runs


def _seat_states(ep) -> dict[int, pd.DataFrame]:
    states = ep["states"].sort_values(["seat", "t"])
    return {int(seat): group.reset_index(drop=True) for seat, group in states.groupby("seat")}


# ---------------------------------------------------------------- movement flags (sampled)

def stuck_flags(ep) -> list[dict]:
    out = []
    for seat, s in _seat_states(ep).items():
        t = s.t.to_numpy()
        x, z = s.x.to_numpy(float), s.z.to_numpy(float)
        gx, gz = s.goal_x.to_numpy(float), s.goal_z.to_numpy(float)
        alive = (s.hp > 0).to_numpy()
        walking = s.cmd_walk.astype("boolean").fillna(False).to_numpy(bool)
        stuck_until = -1
        flagged: list[list[int]] = []
        for i in range(len(s)):
            # the earliest j with t[j] - t[i] >= window, all alive and the same goal throughout
            j = np.searchsorted(t, t[i] + FLAG_STUCK_WINDOW_TICKS)
            if j >= len(s):
                break
            span = slice(i, j + 1)
            if not (alive[span].all() and walking[span].all()) or np.any(gx[span] != gx[i]) or np.any(gz[span] != gz[i]):
                continue
            moved = np.hypot(x[span] - x[i], z[span] - z[i]).max()
            far = np.hypot(gx[i] - x[j], gz[i] - z[j]) >= FLAG_STUCK_MIN_GOAL_DISTANCE
            if moved < FLAG_STUCK_MAX_DISPLACEMENT and far:
                if flagged and t[i] <= stuck_until:
                    flagged[-1][1] = int(t[j])
                else:
                    flagged.append([int(t[i]), int(t[j]), float(gx[i]), float(gz[i]), float(x[i]), float(z[i])])
                stuck_until = int(t[j])
        for t0, t1, goal_x, goal_z, px, pz in flagged:
            out.append(_row(ep, "stuck", seat, t0, t1, "sampled",
                            {"pos": [px, pz], "goal": [goal_x, goal_z],
                             "goal_distance": round(float(np.hypot(goal_x - px, goal_z - pz)))}))
    return out


def oscillation_flags(ep) -> list[dict]:
    out = []
    for seat, s in _seat_states(ep).items():
        alive = s[s.hp > 0]
        goals = alive[["t", "goal_x", "goal_z"]].to_numpy(float)
        changes = [goals[0]] if len(goals) else []
        for g in goals[1:]:
            if g[1] != changes[-1][1] or g[2] != changes[-1][2]:
                changes.append(g)
        flips = []
        for k in range(2, len(changes)):
            back = np.hypot(*(changes[k][1:] - changes[k - 2][1:])) <= FLAG_OSCILLATION_GOAL_MATCH
            jump = np.hypot(*(changes[k - 1][1:] - changes[k - 2][1:])) >= FLAG_OSCILLATION_MIN_JUMP
            if back and jump:
                flips.append(int(changes[k][0]))
        start = 0
        emitted_until = -1
        for end in range(len(flips)):
            while flips[end] - flips[start] > FLAG_OSCILLATION_WINDOW_TICKS:
                start += 1
            if end - start + 1 >= FLAG_OSCILLATION_MIN_FLIPS:
                if out and out[-1]["seat"] == seat and flips[start] <= emitted_until:
                    out[-1]["t_end"] = flips[end]
                    detail = json.loads(out[-1]["detail"])
                    detail["flips"] += 1
                    out[-1]["detail"] = json.dumps(detail, sort_keys=True)
                else:
                    out.append(_row(ep, "oscillating", seat, flips[start], flips[end], "sampled",
                                    {"flips": end - start + 1}))
                emitted_until = flips[end]
    return out


def _is_idle(s: pd.DataFrame) -> np.ndarray:
    """The state row's command equals the engine's empty Command() (all flags off, zero points)."""
    flags = s[["cmd_walk", "cmd_shoot", "cmd_direct", "cmd_sneak", "cmd_charge"]].astype("boolean").fillna(True)
    points = s[["cmd_goal_x", "cmd_goal_z", "cmd_aim_x", "cmd_aim_z"]].astype("Float64").fillna(1)
    return (~flags.any(axis=1) & (points == 0).all(axis=1)).to_numpy(bool)


def idle_flags(ep) -> list[dict]:
    out = []
    seats = ep["seats"].set_index("seat")
    for seat, s in _seat_states(ep).items():
        # The command in row t ran in the step that produced t. A seat that died inside the
        # sample gap sends empty commands while dead, so require alive at both samples (a
        # respawn takes far longer than one sample gap).
        alive_both = ((s.hp > 0) & (s.hp.shift(1) > 0)).to_numpy(bool)
        idle = _is_idle(s) & alive_both
        for a, b in _runs(idle):
            t0 = int(s.t[a - 1]) + 1 if a > 0 else int(s.t[a])  # idle since just after the previous sample
            t1 = int(s.t[b])
            if t1 - t0 + 1 >= FLAG_IDLE_MIN_TICKS:
                out.append(_row(ep, "idle_alive", seat, t0, t1, "sampled", {"ticks": t1 - t0 + 1}))
        row = seats.loc[seat]
        if row.final_idle_run_ticks >= VM_DISABLED_MIN_IDLE_TICKS:
            out.append(_row(ep, "vm_disabled_suspect", seat, int(row.last_active_command_tick) + 1,
                            int(ep["episodes"].iloc[0].ticks), "inferred",
                            {"final_idle_run_ticks": int(row.final_idle_run_ticks)}))
    log = ep["policy_log"]
    if len(log):
        for row in log[log.line_kind == "vm_error"].itertuples():
            out.append(_row(ep, "vm_disabled_suspect", int(row.seat), int(row.t) if pd.notna(row.t) else 0,
                            int(ep["episodes"].iloc[0].ticks), "exact", {"log": row.raw[:200]}))
    return out


# ---------------------------------------------------------------- positional flags at an event tick

def _positions_at(states: pd.DataFrame, t: int) -> pd.DataFrame:
    """Each seat's last sampled state at or before tick t (one row per seat)."""
    before = states[states.t <= t]
    return before.sort_values("t").groupby("seat").tail(1).set_index("seat")


def death_alone_flags(ep) -> list[dict]:
    out = []
    states = ep["states"]
    visibility = ep["visibility"]
    team_of = ep["seats"].set_index("seat").team.to_dict()
    for k in ep["kills"].itertuples():
        victim = int(k.victim)
        # teammates alive at the sample before death (the victim's own row excluded)
        at = _positions_at(states, int(k.t) - 1)
        mates = at[(at.index != victim) & (at.hp > 0) & (at.index.map(team_of) == team_of[victim])]
        distance = np.hypot(mates.x - k.victim_x, mates.z - k.victim_z)
        if (distance <= FLAG_ALONE_RADIUS).any():
            continue
        seen = None
        if len(visibility):
            vis = visibility[visibility.t <= k.t]
            if len(vis):
                last = vis[vis.t == vis.t.max()]
                seen = int(sum(victim in set(map(int, r.sees)) for r in last.itertuples()
                               if team_of[int(r.seat)] != team_of[victim]))
        out.append(_row(ep, "death_alone", victim, int(k.t), int(k.t), "sampled",
                        {"killer": None if pd.isna(k.seat) else int(k.seat), "weapon": k.weapon,
                         "nearest_teammate": round(float(distance.min())) if len(distance) else None,
                         "enemies_seeing": seen}))
    return out


def heart_lost_flags(ep) -> list[dict]:
    out = []
    states = ep["states"]
    hearts = ep.meta["hearts"]
    team_of = ep["seats"].set_index("seat").team.to_dict()
    caps = ep["captures"]
    for c in caps[(caps.kind == "capture_complete") & caps.previous_owner.isin([0, 1])].itertuples():
        loser = int(c.previous_owner)
        if loser == int(c.team):
            continue
        pos = hearts[int(c.heart)]["pos"]
        at = _positions_at(states, int(c.t))
        mates = at[(at.hp > 0) & (at.index.map(team_of) == loser)]
        distance = np.hypot(mates.x - pos[0], mates.z - pos[1])
        near = distance[distance <= FLAG_HEART_DEFENSE_RADIUS]
        if len(near):
            out.append(_row(ep, "heart_lost_with_allies", None, int(c.t), int(c.t), "sampled",
                            {"heart": int(c.heart), "captured_by": int(c.team), "allies_near": sorted(map(int, near.index)),
                             "nearest": round(float(near.min()))}, team=loser))
    return out


# ---------------------------------------------------------------- event flags (exact)

def grenade_flags(ep) -> list[dict]:
    out = []
    team_of = ep["seats"].set_index("seat").team.to_dict()
    ev = ep["events"]
    for row in ev[ev.kind == "grenade_blast"].itertuples():
        if pd.isna(row.seat):
            continue
        data = json.loads(row.data)
        victims = [int(v) for v in data["victims"]]
        if not any(team_of[v] != team_of[int(row.seat)] for v in victims):
            out.append(_row(ep, "wasted_grenade", int(row.seat), int(row.t), int(row.t), "exact",
                            {"pos": data["pos"], "friendly_victims": victims}))
    return out


def friendly_fire_flags(ep) -> list[dict]:
    out = []
    damage = ep["damage"]
    friendly = damage[damage.friendly.astype(bool) & ~damage["self"].astype(bool) & damage.seat.notna()].sort_values("t")
    for seat, group in friendly.groupby("seat"):
        t = group.t.to_numpy()
        breaks = np.flatnonzero(np.diff(t) > FLAG_FF_MERGE_TICKS) + 1
        for chunk in np.split(np.arange(len(group)), breaks):
            rows = group.iloc[chunk]
            out.append(_row(ep, "friendly_fire", int(seat), int(rows.t.min()), int(rows.t.max()), "exact",
                            {"victims": sorted(set(map(int, rows.victim))), "hp": int(rows.hp_removed.sum()),
                             "kills": int(rows.killed.sum()), "weapons": sorted(set(rows.weapon))}))
    return out


def wade_flags(ep) -> list[dict]:
    out = []
    ev = ep["events"]
    ticks = int(ep["episodes"].iloc[0].ticks)
    water = ev[ev.kind.isin(["enter_water", "leave_water"])].sort_values("t")
    deaths = ep["kills"]
    for seat, group in water.groupby("seat"):
        entered = None
        seat_deaths = deaths[deaths.victim == seat].t.to_numpy()
        for row in group.itertuples():
            if row.kind == "enter_water":
                entered = int(row.t)
            elif entered is not None:
                _maybe_wade(ep, out, int(seat), entered, int(row.t), "left")
                entered = None
        if entered is not None:  # no leave event: the stretch ended at death or the match end
            later = seat_deaths[seat_deaths > entered]
            _maybe_wade(ep, out, int(seat), entered, int(later[0]) if len(later) else ticks,
                        "died" if len(later) else "match_end")
    return out


def _maybe_wade(ep, out, seat, t0, t1, ended):
    if t1 - t0 >= FLAG_LONG_WADE_TICKS:
        out.append(_row(ep, "long_wade", seat, t0, t1, "exact", {"ticks": t1 - t0, "ended": ended}))


def zero_glory_flags(ep) -> list[dict]:
    episode = ep["episodes"].iloc[0]
    winner = int(episode.winner)
    if winner in (0, 1) and int(episode[f"glory_{winner}"]) == 0:
        return [_row(ep, "zero_glory_win", None, int(episode.ticks), int(episode.ticks), "exact",
                     {"winner": winner}, team=winner)]
    return []


def episode_flags(ep, only: set[str] | None = None) -> pd.DataFrame:
    """Every flag for one episode, sorted by tick."""
    rows = []
    for build in (stuck_flags, oscillation_flags, idle_flags, death_alone_flags, heart_lost_flags,
                  grenade_flags, friendly_fire_flags, wade_flags, zero_glory_flags):
        rows += build(ep)
    frame = pd.DataFrame(rows, columns=COLUMNS)
    if only:
        frame = frame[frame.flag.isin(only)]
    return frame.sort_values(["t_start", "flag"]).reset_index(drop=True)


def losses(batch, policy: str, flags: pd.DataFrame) -> pd.DataFrame:
    """The policy's losses and draws, worst Elo outcome first, with its flag counts per episode."""
    rows = []
    for ep in batch.episodes:
        for p in pw_metrics.policy_metrics(ep).itertuples():
            if policy not in (p.policy_key, p.policy_name) or p.result in (None, "win"):
                continue
            mine = flags[(flags.episode_id == ep.episode_id) &
                         ((flags.policy_key == p.policy_key) | (flags.seat.isna() & (flags.team == p.team)))]
            opponents = ep["seats"][ep["seats"].team != p.team].policy_name.unique()
            rows.append({"episode_id": ep.episode_id, "result": p.result, "elo_outcome": p.elo_outcome,
                         "glory_ours": p.glory_ours, "glory_theirs": p.glory_theirs,
                         "opponent": ",".join(sorted(opponents)), "ticks": int(ep["episodes"].iloc[0].ticks),
                         "flags": len(mine), **mine.flag.value_counts().to_dict()})
    frame = pd.DataFrame(rows)
    return frame.sort_values("elo_outcome").reset_index(drop=True) if len(frame) else frame


# ---------------------------------------------------------------- CLI

def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("pw_flags", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/pw_flags.py paintbot_pw_lab/episode_data/20260928T214433_* --json",
        "uv run python paintbot_pw_lab/tools/pw_flags.py ROOT --policy james-pw --flags stuck,death_alone --top 5",
        "uv run python paintbot_pw_lab/tools/pw_flags.py ROOT --top 0 --csv /tmp/flags.csv   # counts only"])
    parser.add_argument("roots", nargs="+", type=Path, help="episode dirs, batch dirs or NAME.replay files")
    parser.add_argument("--policy", help="our policy_key or policy_name: flags for its seats, losses worst first "
                                         "(exit 2 listing valid values if absent)")
    parser.add_argument("--flags", help=f"comma list, from: {','.join(FLAG_NAMES)}")
    parser.add_argument("--top", type=int, default=20,
                        help="flag rows to print (and return in --json) per episode (default 20; 0 = counts only)")
    parser.add_argument("--csv", type=Path, help="write every flag row to this CSV file")
    parser.add_argument("--vis-every", type=int, default=0,
                        help="trace visibility every M ticks (re-traces the cache), e.g. 24")
    parser.add_argument("--tag", help="pw_trace build (default: tools/release.env)")
    return parser


def run_cli(args, report: pw_cli.Report) -> dict:
    only = set(args.flags.split(",")) if args.flags else None
    if only and only - set(FLAG_NAMES):
        raise pw_cli.UsageError(f"unknown --flags {sorted(only - set(FLAG_NAMES))}", FLAG_NAMES)
    if args.top < 0:
        raise pw_cli.UsageError(f"--top {args.top}: give 0 (counts only) or more")
    batch = pw_episodes.load_batch(args.roots, tag=args.tag, options=pw_episodes.TraceOptions(vis_every=args.vis_every))
    report.add_batch(batch)
    pw_cli.require_policy(batch.episodes, args.policy)
    print(thresholds_line())
    frames = [episode_flags(ep, only) for ep in batch.episodes]
    flags = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=COLUMNS)
    worst = None
    if args.policy:
        shown = flags[[_belongs(batch, row, args.policy) for row in flags.itertuples()]] if len(flags) else flags
        worst = losses(batch, args.policy, flags)
        print(f"\n{args.policy}: {len(worst)} losses/draws, worst Elo outcome first")
        print(worst.to_string(index=False) if len(worst) else "  none")
        order = list(worst.episode_id) if len(worst) else []
    else:
        shown = flags
        order = []
    order += [e.episode_id for e in sorted(batch.episodes, key=lambda e: e.episode_id) if e.episode_id not in order]
    counts = shown.flag.value_counts().to_dict() if len(shown) else {}
    print("\nflag counts:", counts)
    listed = []
    for episode_id in order:
        rows = shown[shown.episode_id == episode_id]
        if not len(rows):
            continue
        per_flag = rows.flag.value_counts().to_dict()
        if args.top == 0:
            print(f"{episode_id}  {len(rows)} flags: {per_flag}")
            continue
        print(f"\n{episode_id}  {len(rows)} flags" + (f" (first {args.top})" if len(rows) > args.top else ""))
        print(rows.head(args.top).drop(columns=["episode_id", "policy_key"]).to_string(index=False))
        listed.append(rows.head(args.top))
    print(f"\n{len(batch.episodes)} episodes, {len(batch.failures)} failed")
    for path, code, message in batch.failures:
        print(f"FAILED [{code}] {path}: {message}")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        flags.to_csv(args.csv, index=False)
        print(f"wrote {args.csv}")
        report.output(args.csv)
    return {"thresholds": THRESHOLDS, "flag_counts": counts, "rows_total": int(len(shown)),
            "losses": pw_cli.records(worst) if worst is not None else None,
            "rows": pw_cli.records(pd.concat(listed, ignore_index=True)) if listed else [],
            "rows_note": f"at most --top {args.top} rows per episode; --csv FILE writes every row"}


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), run_cli, argv)


def _belongs(batch, flag, policy: str) -> bool:
    """A seat flag on one of the policy's seats, or a team flag on a team the policy plays."""
    seats = next(e for e in batch.episodes if e.episode_id == flag.episode_id)["seats"]
    mine = seats[(seats.policy_key == policy) | (seats.policy_name == policy)]
    if pd.notna(flag.seat):
        return int(flag.seat) in set(mine.seat)
    return pd.notna(flag.team) and int(flag.team) in set(mine.team)


if __name__ == "__main__":
    sys.exit(main())
