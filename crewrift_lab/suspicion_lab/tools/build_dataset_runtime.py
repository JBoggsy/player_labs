#!/usr/bin/env python3
"""Build the suspicion dataset from crewborg's OWN runtime-traced features.

The runtime-feature counterpart to `build_dataset.py` — the train->serve-gap rework
(design suspicion-learning.md §7.2). Rather than reconstructing features offline from
expanded replays, this reads the *exact* feature vectors crewborg computed at serve
time — `domain.suspicion_snapshot.ranking[].features`, emitted per meeting under
`CREWBORG_TRACE_SUSPICION_FEATURES=1` in the policy artifact — and labels each
(crewborg-observer, suspect, meeting) row with the suspect's ground-truth role from the
expanded replay's `player_manifest`. It emits the SAME parquet schema as
`build_dataset.py`, so `fit.py --features runtime` consumes it unchanged.

Inputs:
  --expanded   dir of `<ep>.jsonl.gz` from expand_corpus.py (for labels + meeting ticks)
  --artifacts  fetch_artifacts layout (episode dirs w/ episode.json + artifacts/*.zip)
Episodes are matched between the two by their `ereq_<id>` key.

    uv run python crewrift_lab/suspicion_lab/tools/build_dataset_runtime.py \
        --expanded /tmp/v76_expanded --artifacts /tmp/v76_arts \
        --policy crewborg --version 76 --out /tmp/runtime_dataset.parquet

Pre-v90 telemetry never carried CREWBORG_TRACE_SUSPICION_FEATURES (TRACE_GROUPS=all
does NOT imply it), so those snapshots lack `features`. `--allow-degraded`
reconstructs the 7 mechanically-recoverable features from the snapshot's event
summary (features_degraded=1 marks such rows; the other 12 features stay 0 —
including all social counters, so do NOT fit the full runtime feature set on
degraded rows). `--policy`/`--version` are repeatable; omit --version to take any.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import FEATURE_NAMES  # noqa: E402
from replay_parse import parse_game  # noqa: E402

# Exact-parity constants from the runtime scorer (crewborg is an installed package
# in this uv project). Used only by the --allow-degraded reconstruction below.
from crewrift.crewborg.strategy import suspicion as _rt  # noqa: E402

# Features reconstructable from the UN-flagged snapshot's per-suspect event summary
# (kind/dur/target/region/min_dist — no end_tick, no seen_ticks, no social counters).
# Mirrors `_fitted_features` (strategy/suspicion.py) event-for-event; everything not
# in this set is unrecoverable from degraded snapshots and stays 0.
DEGRADED_RECOVERABLE = (
    "witnessed_kills", "near_body_bodies", "tail_obs_samples", "tail_obs_max_run",
    "vent_visits", "copresence_killrange_samples", "task_site_dwell_samples",
)


def degraded_features(events: list[dict]) -> dict[str, float]:
    """Rebuild the 7 mechanically-recoverable runtime features from a snapshot's
    event summary — the path for pre-v90 telemetry that lacks `ranking[].features`
    (CREWBORG_TRACE_SUSPICION_FEATURES was never set on those uploads)."""
    unit = float((_rt._WEIGHTS or {}).get("sample_unit_ticks", _rt.DEFAULT_SAMPLE_UNIT_TICKS))
    tail_durations: list[int] = []
    copresence_ticks = 0
    task_ticks = 0
    vent_visits = 0
    near_bodies: set = set()
    witnessed = 0
    for ev in events or []:
        kind, dur, min_dist = ev.get("kind"), int(ev.get("dur") or 0), ev.get("min_dist")
        if kind in ("kill", "vent_use"):
            witnessed += 1
        elif kind == "near_body":
            if min_dist is not None:
                near_bodies.add(ev.get("target"))
        elif kind == "tailing_self":
            tail_durations.append(dur)
            if min_dist is not None and min_dist ** 2 <= _rt.COPRESENCE_DIST_SQ:
                copresence_ticks += dur
        elif kind == "task":
            task_ticks += dur
        elif kind == "vent":
            if dur > _rt.VENT_CROSS_TICKS:
                vent_visits += 1
    return {
        "witnessed_kills": float(witnessed),
        "near_body_bodies": float(len(near_bodies)),
        "tail_obs_samples": sum(tail_durations) / unit,
        "tail_obs_max_run": (max(tail_durations) if tail_durations else 0) / unit,
        "vent_visits": float(vent_visits),
        "copresence_killrange_samples": copresence_ticks / unit,
        "task_site_dwell_samples": task_ticks / unit,
    }

EREQ = re.compile(r"ereq_[0-9a-f]+")
# crewborg's traced snapshot fires at meeting start; require the matched meeting's
# call_tick to be within this many ticks of the snapshot (else the snapshot doesn't
# correspond to a real meeting we parsed — dropped and counted).
MATCH_TOL_TICKS = 400


def ereq_key(name: str) -> str | None:
    m = EREQ.search(name)
    return m.group(0) if m else None


def iter_snapshots(zpath: Path):
    """Yield (tick, data) for each domain.suspicion_snapshot in a policy artifact."""
    with zipfile.ZipFile(zpath) as zf:
        if "telemetry.jsonl" not in zf.namelist():
            return
        with zf.open("telemetry.jsonl") as f:
            for line in io.TextIOWrapper(f):
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (e.get("event") or e.get("name")) == "domain.suspicion_snapshot":
                    yield e.get("tick"), (e.get("data") or {})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--expanded", type=Path, required=True)
    ap.add_argument("--artifacts", type=Path, required=True)
    ap.add_argument("--policy", action="append", default=None,
                    help="Subject policy name(s); repeatable. Default: crewborg.")
    ap.add_argument("--version", type=int, action="append", default=None,
                    help="Subject version(s); repeatable. Omit to accept ANY version "
                         "of the named policies (observer_version records which).")
    ap.add_argument("--allow-degraded", action="store_true",
                    help="Also emit rows from snapshots WITHOUT ranking[].features "
                         "(pre-v90 telemetry), reconstructing the 7 recoverable "
                         "features from the event summary; features_degraded=1.")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    policies = set(args.policy or ["crewborg"])
    versions = set(args.version or [])

    art_by_ereq: dict[str, Path] = {}
    for d in sorted(args.artifacts.glob("*/")):
        k = ereq_key(d.name)
        if k:
            art_by_ereq[k] = d

    rows: list[dict] = []
    st: collections.Counter = collections.Counter()
    match_dists: list[int] = []

    for exp in sorted(args.expanded.glob("*.jsonl.gz")):
        k = ereq_key(exp.name)
        if not k or k not in art_by_ereq:
            st["no_artifact_dir"] += 1
            continue
        artdir = art_by_ereq[k]
        try:
            ep = json.loads((artdir / "episode.json").read_text())
        except OSError:
            st["no_episode_json"] += 1
            continue
        subject = next(
            (p for p in (ep.get("participants") or [])
             if p.get("policy_name") in policies
             and (not versions or p.get("version") in versions)),
            None,
        )
        if subject is None:
            st["no_subject_seat"] += 1
            continue
        cb_slot = subject.get("position")
        zpath = artdir / "artifacts" / f"policy_artifact_{cb_slot}.zip"
        if not zpath.exists():
            st["no_artifact_zip"] += 1
            continue
        try:
            game = parse_game(exp)
        except Exception as exc:  # noqa: BLE001 - skip corrupt games
            st["parse_fail"] += 1
            continue
        if not game.players or not game.meetings or cb_slot not in game.players:
            st["no_meetings_or_slot"] += 1
            continue
        # Crew-POV only: this is the crew suspicion model.
        if game.players[cb_slot].role != "crew":
            st["subject_imposter"] += 1
            continue

        color2slot = {p.color: s for s, p in game.players.items()}
        meetings = [(mi, m.call_tick) for mi, m in enumerate(game.meetings)]

        for tick, data in iter_snapshots(zpath):
            ranking = data.get("ranking") or []
            if not ranking or tick is None:
                continue
            mi, ct = min(meetings, key=lambda mc: abs(tick - mc[1]))
            dist = abs(tick - ct)
            if dist > MATCH_TOL_TICKS:
                st["snapshot_no_meeting"] += 1
                continue
            match_dists.append(dist)
            for entry in ranking:
                feats = entry.get("features")
                degraded = False
                if not isinstance(feats, dict):
                    if not args.allow_degraded:
                        st["no_features_skipped"] += 1
                        continue
                    feats = degraded_features(entry.get("events") or [])
                    degraded = True
                sslot = color2slot.get(entry.get("color"))
                if sslot is None or sslot == cb_slot:
                    st["suspect_unresolved"] += (sslot is None)
                    continue
                sus = game.players[sslot]
                row = {
                    "episode": game.episode,
                    "meeting_idx": mi,
                    "decision_tick": ct,
                    "observer_slot": cb_slot,
                    "observer_name": game.players[cb_slot].name,
                    "observer_policy": subject.get("policy_name"),
                    "observer_version": subject.get("version"),
                    "suspect_slot": sslot,
                    "suspect_name": sus.name,
                    "label_imposter": int(sus.role == "imposter"),
                    "snapshot_tick": tick,
                    "runtime_p": entry.get("p"),
                    "features_degraded": int(degraded),
                }
                # All FEATURE_NAMES columns (fit.py may reference either set); the traced
                # dict carries exactly the RUNTIME_FEATURES, offline-only names stay 0.
                for fn in FEATURE_NAMES:
                    row[fn] = float(feats.get(fn, 0.0))
                rows.append(row)
            st["snapshots"] += 1
        st["episodes_used"] += 1

    df = pd.DataFrame(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, index=False)
    log = lambda m: print(m, file=sys.stderr)  # noqa: E731
    log(f"Wrote {len(df)} rows from {st['episodes_used']} crew-POV episodes "
        f"({st['snapshots']} meeting-snapshots) -> {args.out}")
    log(f"stats: {dict(st)}")
    if match_dists:
        md = sorted(match_dists)
        log(f"snapshot->meeting tick gap: median {md[len(md)//2]}, max {md[-1]} (tol {MATCH_TOL_TICKS})")
    if len(df):
        log(f"base rate P(imposter) = {df.label_imposter.mean():.3f} "
            f"({int(df.label_imposter.sum())} imp / {int((1 - df.label_imposter).sum())} crew rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
