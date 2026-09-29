#!/usr/bin/env python3
"""Paintbot PW A/B adapter (lab tool T5) over the shared coworld-ab engines.

Reads episodes through pw_episodes (hash-checked traces) and pw_metrics, builds one row per
(episode, arm policy), and hands the rows to `ab_stats` (independent arms) or
`paired_stats` (paired, head-to-head, SPRT). Contract and worked commands:
paintbot_pw_lab/docs/tools/compare.md. Design rationale: docs/designs/.tooling-plan-brief.md §7.

Designs (--design):
  paired  both arms vs the same opponent policy; episodes pair by (opponent, side, seed).
          seed = game_config.seed (hosted, set per request by pw_ab_requests.py) or the
          engine seed (local). Paired t + Wilcoxon for means, exact McNemar for rates.
  h2h     candidate vs baseline in the same episode; one-sample t of the candidate's Elo
          outcome vs 0.5, exact binomial on decisive games, other metrics paired in-episode.
  field   unpaired arms (e.g. vs a mix of leaders): Fisher rates, Welch means (ab_stats).

Unit: one row per (episode, arm policy); a policy's 8 seats are summed within the episode and
per-seat metrics divide by its seat count. Primary metric: the ladder's Elo outcome score,
clamp(0.5 + (our glory - their glory) / 2000, 0, 1); a platform failure attributed to one
policy is a forfeit (0 for that side, 1 for the other), as in metta elo.py.

Usage (repo root):
  uv run python paintbot_pw_lab/tools/compare.py compare ROOT... --design paired \
      --baseline NAME:vN --candidate NAME:vM [--target elo_outcome] [--out OUT.json] [--requests MANIFEST] [--json]
  uv run python paintbot_pw_lab/tools/compare.py sprt ROOT... --design paired \
      --baseline NAME:vN --candidate NAME:vM [--h0 0 --h1 0.05 --alpha 0.05 --beta 0.05]
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parents[1] / ".claude" / "skills" / "coworld-ab" / "scripts"))
import ab_stats  # noqa: E402
import paired_stats  # noqa: E402
import pw_cli  # noqa: E402
import pw_episodes  # noqa: E402
import pw_metrics  # noqa: E402

DESIGNS = ("paired", "h2h", "field")
SIDES = ("red", "blue")  # engine team 0 (Ember, even seats) / 1 (Azure, odd seats)

# (key, higher_is_better, kind, applies_to_group). Rates are binary per episode.
METRICS = [
    ("elo_outcome", True, "mean", None),
    ("win_rate", True, "rate", None),
    ("draw_rate", False, "rate", None),
    ("zero_glory_win_rate", False, "rate", None),   # a 0-glory win scores 0.5 on the ladder
    ("first_capture_rate", True, "rate", None),
    ("hearts_held_mean", True, "mean", None),
    ("kills_per_seat", True, "mean", None),
    ("deaths_per_seat", False, "mean", None),
    ("gun_enemy_accuracy", True, "mean", None),
    ("dealt_hp_enemy_per_seat", True, "mean", None),
    ("captures_per_seat", True, "mean", None),
    ("alive_share", True, "mean", None),
    ("heart_reach_share", True, "mean", None),
    ("idle_share", False, "mean", None),
    ("trade_kills_per_seat", True, "mean", None),
    ("vm_disabled_suspect_seats", False, "mean", None),
    ("ops_fail_rate", False, "rate", "all"),
]
PRIMARY = "elo_outcome"
PER_SEAT = {"kills_per_seat": "kills", "deaths_per_seat": "deaths", "dealt_hp_enemy_per_seat": "dealt_hp_enemy",
            "captures_per_seat": "captures_completed", "trade_kills_per_seat": "trade_kills"}
DIRECT = ("gun_enemy_accuracy", "alive_share", "heart_reach_share", "idle_share", "vm_disabled_suspect_seats")
H2H_TESTS = {"elo_outcome": "one_sample", "win_rate": "decisive_binomial"}

# metta observatory_competitions/v2/episode_failures.py INFRASTRUCTURE_ONLY_ERROR_TYPES
# (checked 2f2add7296): a failure of these types is never a policy's forfeit.
INFRASTRUCTURE_ERRORS = frozenset({
    "result_missing", "platform_error", "episode_inconclusive", "result_error", "pod_deleted",
    "pod_not_found", "node_disruption", "dispatch_failed", "hydration_failed", "player_never_started",
    "player_file_unavailable", "player_file_mismatch", "config_error", "artifact_transport_error",
    "cancelled", "worker_error", "worker_lost", "worker_oom"})


def _known(value):
    return None if value is None or pd.isna(value) else value


# ------------------------------------------------------------------ policy identity

def policy_label(name, version) -> str:
    return f"{name}:v{int(version)}" if _known(version) is not None else str(name)


def resolve_policy(spec: str, known: dict[str, str]) -> str:
    """spec -> policy_key. `known` maps policy_key -> label (name:vN, or the local name).

    Accepts an exact policy_key (policy_version_id or local:<name>) or an exact label."""
    if spec in known:
        return spec
    matches = sorted(key for key, label in known.items() if label == spec)
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise pw_cli.UsageError(f"{spec!r} matches several policy keys: {matches}; pass one policy_version_id")
    raise pw_cli.UsageError(f"{spec!r} is not in these episodes (policy_version_id, local:<name> or name:vN)",
                            sorted(set(known.values()) | set(known)))


# ------------------------------------------------------------------ platform failures

def failure_state(episode: dict | None) -> tuple[str, int | None]:
    """('ok'|'failed'|'unfinished', attributable failed seat or None) from episode.json."""
    if episode is None:
        return "ok", None  # local recording
    status = episode.get("status")
    failed = (status in ("failed", "cancelled") or episode.get("error_type")
              or episode.get("failed_policy_index") is not None)
    if not failed:
        return ("ok" if status == "completed" else "unfinished"), None
    index = episode.get("failed_policy_index")
    attributable = index is not None and episode.get("error_type") not in INFRASTRUCTURE_ERRORS
    return "failed", (int(index) if attributable else None)


def failure_rows(episode: dict, arm_keys: dict[str, str], exclusions: Counter) -> list[dict]:
    """Rows for an episode the platform failed. An attributable failure is a forfeit (Elo
    outcome 0 for the failed side, 1 for the other); every other metric stays unknown."""
    _, failed_seat = failure_state(episode)
    seats = {p["position"]: p for p in episode.get("participants", [])}
    rows = []
    for arm, key in arm_keys.items():
        ours = [pos for pos, p in seats.items() if p.get("policy_version_id") == key]
        if not ours:
            continue
        teams = {pos % 2 for pos in ours}
        if len(teams) != 1:
            exclusions["mirror"] += 1
            continue
        team = teams.pop()
        opponents = {p.get("policy_version_id"): policy_label(p.get("policy_name"), p.get("version"))
                     for pos, p in seats.items() if pos % 2 != team}
        other = sorted(opponents)
        row = empty_row(episode.get("id"), arm, key, team, other, ",".join(opponents[k] for k in other),
                        (episode.get("game_config") or {}).get("seed"), None, None, None,
                        episode.get("coworld_version"))
        row["ops_fail"] = 1.0
        if failed_seat is not None:
            won = float(failed_seat % 2 != team)
            row.update(elo_outcome=won, win_rate=won, draw_rate=0.0, forfeit="theirs" if won else "ours")
        rows.append(row)
    if rows:  # counted once per episode, not per arm row
        exclusions["ops_fail_forfeit_scored" if failed_seat is not None else "ops_fail_unattributed"] += 1
    return rows


def empty_row(episode_id, arm, key, team, opponent_keys, opponent_label, config_seed, engine_seed,
              final_hash, rules, coworld_version) -> dict:
    return {"episode_id": episode_id, "arm": arm, "policy_key": key, "side": SIDES[team],
            "opponent_key": ",".join(opponent_keys), "opponent": opponent_label,
            "config_seed": _known(config_seed), "engine_seed": _known(engine_seed),
            "final_hash": _known(final_hash), "rules": _known(rules), "coworld_version": _known(coworld_version),
            "ops_fail": 0.0, "forfeit": None, **{m[0]: None for m in METRICS if m[0] != "ops_fail_rate"}}


# ------------------------------------------------------------------ traced episodes

def episode_rows(ep, arm_keys: dict[str, str], exclusions: Counter) -> list[dict]:
    """One row per arm policy present in a traced episode."""
    seats = pw_metrics.seat_metrics(ep)
    policies = pw_metrics.policy_metrics(ep, seats).set_index("policy_key")
    teams = pw_metrics.team_metrics(ep, seats).set_index("team")
    episode = ep["episodes"].iloc[0]
    labels = {r.policy_key: policy_label(r.policy_name, r.policy_version) for r in ep["seats"].itertuples()}
    rows = []
    for arm, key in arm_keys.items():
        if key not in policies.index:
            continue
        p = policies.loc[key]
        if _known(p.team) is None:
            exclusions["mirror"] += 1
            continue
        team = int(p.team)
        other = sorted(ep["seats"][ep["seats"].team != team].policy_key.unique())
        row = empty_row(ep.episode_id, arm, key, team, other, ",".join(labels[k] for k in other),
                        episode.config_seed, episode.engine_seed, episode.final_hash, episode.rules,
                        episode.coworld_version)
        ours, theirs = teams.loc[team], teams.loc[1 - team]
        won = p.result == "win"
        row.update(elo_outcome=float(p.elo_outcome), win_rate=float(won), draw_rate=float(p.result == "draw"),
                   zero_glory_win_rate=float(won and p.glory_ours == 0),
                   first_capture_rate=float(_known(ours.first_capture_tick) is not None and (
                       _known(theirs.first_capture_tick) is None or ours.first_capture_tick < theirs.first_capture_tick)),
                   hearts_held_mean=float(ours.hearts_held_mean))
        for name, column in PER_SEAT.items():
            row[name] = float(p[column]) / int(p.seats)
        for name in DIRECT:
            row[name] = None if _known(p[name]) is None else float(p[name])
        rows.append(row)
    return rows


def load_rows(roots: list[Path], baseline: str, candidate: str, *, tag=None, jobs=None,
              refresh=False) -> tuple[list[dict], Counter, list[tuple[str, str, str]], dict[str, str]]:
    """(rows, exclusions, load failures, {arm: policy_key}) for every episode under the roots.

    Every episode is accounted for: a row, a counted exclusion, or a listed failure."""
    batch = pw_episodes.load_batch(roots, tag=tag, jobs=jobs, refresh=refresh)
    failed_meta: dict[str, dict] = {}
    load_failures = []
    exclusions: Counter = Counter()
    for path, code, message in batch.failures:
        where = Path(path)
        directory = where if where.is_dir() else where.parent
        meta = _read_json(directory / "episode.json")
        state, _ = failure_state(meta) if meta else ("ok", None)
        if state == "failed":
            failed_meta[str(directory)] = meta
        elif state == "unfinished":
            exclusions["unfinished"] += 1
        else:
            load_failures.append((path, code, message))
            exclusions[f"load_{code}"] += 1
    traced = []
    for ep in batch.episodes:
        meta = _read_json(ep.source.episode_json)
        state, _ = failure_state(meta)
        if state == "failed":
            failed_meta[str(ep.source.cache.parent)] = meta
        elif state == "unfinished":
            exclusions["unfinished"] += 1
        else:
            traced.append(ep)

    known: dict[str, str] = {}
    for ep in traced:
        for r in ep["seats"].itertuples():
            known[r.policy_key] = policy_label(r.policy_name, r.policy_version)
    for meta in failed_meta.values():
        for p in meta.get("participants", []):
            known.setdefault(p.get("policy_version_id"), policy_label(p.get("policy_name"), p.get("version")))
    arm_keys = {"baseline": resolve_policy(baseline, known), "candidate": resolve_policy(candidate, known)}
    if arm_keys["baseline"] == arm_keys["candidate"]:
        raise pw_cli.UsageError("baseline and candidate resolve to the same policy")

    rows = []
    for ep in traced:
        found = episode_rows(ep, arm_keys, exclusions)
        if not found and not set(ep["seats"].policy_key) & set(arm_keys.values()):
            exclusions["neither_arm_policy"] += 1
        rows += found
    for meta in failed_meta.values():
        found = failure_rows(meta, arm_keys, exclusions)
        if not found:
            exclusions["neither_arm_policy"] += 1
        rows += found
    return rows, exclusions, load_failures, arm_keys


def _read_json(path: Path | None) -> dict | None:
    return json.loads(path.read_text()) if path and path.is_file() else None


def check_single_ruleset(rows: list[dict]) -> None:
    """Never pool rules versions or coworld versions in one comparison."""
    for field in ("rules", "coworld_version"):
        values = sorted({str(r[field]) for r in rows if r[field] is not None})
        if len(values) > 1:
            raise pw_cli.UsageError(f"episodes span several {field} values {values}: split the roots and compare within one")


def drop_duplicate_games(rows: list[dict], exclusions: Counter) -> list[dict]:
    """The engine is deterministic: the same policies, side and seed with the same final hash
    is one game played twice, not two observations. Keep the first; count the rest."""
    seen, kept = set(), []
    for row in sorted(rows, key=lambda r: str(r["episode_id"])):
        if row["final_hash"] is not None:
            key = (row["arm"], row["opponent_key"], row["side"], row["engine_seed"], row["final_hash"])
            if key in seen:
                exclusions["duplicate_game"] += 1
                continue
            seen.add(key)
        kept.append(row)
    return kept


# ------------------------------------------------------------------ grouping and pairing

def pair_seed(row: dict):
    return row["config_seed"] if row["config_seed"] is not None else row["engine_seed"]


def pair_rows(rows: list[dict], exclusions: Counter) -> tuple[list[tuple[dict, dict]], dict]:
    """Design 1 pairs: same (opponent, side, seed). Replicates under one key pair in
    episode-id order (they are exchangeable); leftovers are counted as unpaired."""
    by_key: dict[tuple, dict[str, list]] = defaultdict(lambda: {"baseline": [], "candidate": []})
    for row in sorted(rows, key=lambda r: str(r["episode_id"])):
        seed = pair_seed(row)
        if seed is None:
            exclusions["no_seed"] += 1
            continue
        by_key[(row["opponent_key"], row["side"], seed)][row["arm"]].append(row)
    pairs, info = [], Counter()
    for arms in by_key.values():
        n = min(len(arms["baseline"]), len(arms["candidate"]))
        pairs += list(zip(arms["baseline"][:n], arms["candidate"][:n]))
        for arm in ("baseline", "candidate"):
            exclusions[f"unpaired_{arm}"] += len(arms[arm]) - n
    for b, c in pairs:
        if b["engine_seed"] is not None and c["engine_seed"] is not None and b["engine_seed"] != c["engine_seed"]:
            info["pairs_with_different_engine_seeds"] += 1
    return pairs, dict(info)


def h2h_pairs(rows: list[dict], exclusions: Counter) -> list[tuple[dict, dict]]:
    by_episode: dict[str, dict] = defaultdict(dict)
    for row in rows:
        by_episode[row["episode_id"]][row["arm"]] = row
    pairs = []
    for arms in by_episode.values():
        if len(arms) == 2:
            pairs.append((arms["baseline"], arms["candidate"]))
        else:
            exclusions["h2h_missing_an_arm"] += 1
    return pairs


def group_names(opponents: set[str]) -> list[str]:
    """all, red, blue, and one group per opponent when there is more than one."""
    return ["all", *SIDES, *(f"vs {o}" for o in sorted(opponents) if len(opponents) > 1)]


def groups_of(row: dict, opponents: set[str]) -> list[str]:
    return ["all", row["side"], *([f"vs {row['opponent']}"] if len(opponents) > 1 else [])]


def value_of(row: dict, key: str):
    return row["ops_fail"] if key == "ops_fail_rate" else row.get(key)


# ------------------------------------------------------------------ analysis

def analyse(rows: list[dict], design: str, exclusions: Counter, metrics=METRICS) -> dict:
    """Deltas plus the per-group inputs render_markdown needs."""
    episodes_by_arm = defaultdict(set)
    for row in rows:
        episodes_by_arm[row["arm"]].add(row["episode_id"])
    if design != "h2h" and episodes_by_arm["baseline"] & episodes_by_arm["candidate"]:
        raise pw_cli.UsageError("an episode holds both arms: use --design h2h")
    if design == "field":
        opponents = {r["opponent"] for r in rows}
        base_groups, cand_groups = defaultdict(list), defaultdict(list)
        for row in rows:
            for g in groups_of(row, opponents):
                (base_groups if row["arm"] == "baseline" else cand_groups)[g].append(row)
        values = lambda rs, key: [v for v in (value_of(r, key) for r in rs) if v is not None]  # noqa: E731
        metric_value = lambda rs, key: ((statistics.mean(values(rs, key)), len(values(rs, key)))  # noqa: E731
                                        if values(rs, key) else None)
        deltas = ab_stats.build_deltas(base_groups, cand_groups, metrics, metric_value, values, group_names(opponents))
        return {"deltas": deltas, "base_groups": base_groups, "cand_groups": cand_groups, "pairing": {},
                "analysis": ab_stats.INDEPENDENT_ANALYSIS, "note": ab_stats.INDEPENDENT_NOTE}
    if design == "paired":
        pairs, pairing = pair_rows(rows, exclusions)
        tests, analysis = {}, paired_stats.PAIRED_ANALYSIS
    else:
        pairs, pairing = h2h_pairs(rows, exclusions), {}
        tests, analysis = H2H_TESTS, paired_stats.H2H_ANALYSIS
    # Group by the candidate's side and opponent (in h2h the candidate's opponent is the baseline).
    opponents = {c["opponent"] for _, c in pairs}
    pair_groups = defaultdict(list)
    for b, c in pairs:
        for g in groups_of(c, opponents):
            pair_groups[g].append((b, c))
    deltas = paired_stats.build_paired_deltas(pair_groups, metrics, value_of, group_names(opponents), tests=tests)
    return {"deltas": deltas, "base_groups": {g: [b for b, _ in ps] for g, ps in pair_groups.items()},
            "cand_groups": {g: [c for _, c in ps] for g, ps in pair_groups.items()}, "pairing": pairing,
            "pairs": pairs, "analysis": analysis, "note": analysis}


def primary_sprt(rows: list[dict], design: str, exclusions: Counter, *, h0: float, h1: float,
                 alpha: float, beta: float) -> paired_stats.SprtResult:
    """SPRT on the primary metric. paired: mean per-pair difference (cand - base);
    h2h: the candidate's mean outcome minus 0.5; field: difference of arm means."""
    if design == "paired":
        pairs, _ = pair_rows(rows, exclusions)
        diffs = [c[PRIMARY] - b[PRIMARY] for b, c in pairs if b[PRIMARY] is not None and c[PRIMARY] is not None]
        return paired_stats.sprt_mean(diffs, h0=h0, h1=h1, alpha=alpha, beta=beta)
    if design == "h2h":
        values = [c[PRIMARY] - 0.5 for _, c in h2h_pairs(rows, exclusions) if c[PRIMARY] is not None]
        return paired_stats.sprt_mean(values, h0=h0, h1=h1, alpha=alpha, beta=beta)
    arm = lambda name: [r[PRIMARY] for r in rows if r["arm"] == name and r[PRIMARY] is not None]  # noqa: E731
    return paired_stats.sprt_two_sample(arm("baseline"), arm("candidate"), h0=h0, h1=h1, alpha=alpha, beta=beta)


# ------------------------------------------------------------------ CLI

def prepare(args) -> tuple[list[dict], Counter, list, dict]:
    rows, exclusions, failures, arm_keys = load_rows(args.roots, args.baseline, args.candidate,
                                                     tag=args.tag, jobs=args.jobs, refresh=args.refresh)
    check_single_ruleset(rows)
    rows = drop_duplicate_games(rows, exclusions)
    return rows, exclusions, failures, arm_keys


def print_accounting(rows, exclusions, failures, arm_keys, design) -> None:
    counts = Counter(r["arm"] for r in rows)
    print(f"Design: {design}. Unit: one row per (episode, arm policy); seats summed within the episode.")
    print(f"Arms: baseline {arm_keys['baseline']} ({counts['baseline']} rows), "
          f"candidate {arm_keys['candidate']} ({counts['candidate']} rows)")
    print(f"Exclusions and failure handling: {dict(sorted(exclusions.items())) or 'none'}")
    for path, code, message in failures:
        print(f"  LOAD FAILED [{code}] {path}: {message}")


def select_metrics(text: str | None) -> list:
    if not text:
        return METRICS
    wanted = text.split(",")
    unknown = sorted(set(wanted) - {m[0] for m in METRICS})
    if unknown:
        raise pw_cli.UsageError(f"unknown --metrics {unknown}", [m[0] for m in METRICS])
    return [m for m in METRICS if m[0] in wanted]


def record_counts(report: pw_cli.Report, rows, exclusions) -> None:
    """Envelope counts once the analysis has added its exclusions (load failures are listed
    separately as failures: exit 1)."""
    report.counts.update(processed=len({r["episode_id"] for r in rows}), rows=len(rows),
                         excluded=sum(exclusions.values()), exclusions=dict(sorted(exclusions.items())))


def cmd_compare(args, report: pw_cli.Report) -> dict:
    metrics = select_metrics(args.metrics)
    rows, exclusions, failures, arm_keys = prepare(args)
    for path, code, message in failures:        # listed even if the analysis then refuses the design
        report.fail(path, code, message)
    result = analyse(rows, args.design, exclusions, metrics)
    sprt = primary_sprt(rows, args.design, Counter(), h0=args.h0, h1=args.h1, alpha=args.alpha, beta=args.beta)
    record_counts(report, rows, exclusions)
    print_accounting(rows, exclusions, failures, arm_keys, args.design)
    if result["pairing"]:
        print(f"Pairing diagnostics: {result['pairing']}")
    print(f"SPRT on {PRIMARY} (H0 {args.h0}, H1 {args.h1}): {sprt.decision}, LLR {sprt.llr:.2f} "
          f"in [{sprt.lower:.2f}, {sprt.upper:.2f}], n {sprt.n}{', ' + sprt.note if sprt.note else ''}")
    print()
    print(ab_stats.render_markdown(args.baseline, args.candidate, result["base_groups"], result["cand_groups"],
                                   result["deltas"], args.target, ["all"], metrics, note=result["note"]))
    if args.design != "field":
        print()
        print(paired_stats.render_detail(result["deltas"]))
    emit = paired_stats.emit_json if args.design != "field" else ab_stats.emit_json
    summary = emit(args.baseline, args.candidate, args.target, result["deltas"], analysis=result["analysis"])
    summary.update(
        design=args.design, unit="episode per arm policy", arm_policy_keys=arm_keys,
        exclusions=dict(exclusions), load_failures=[list(f) for f in failures], pairing=result["pairing"],
        sprt=sprt.as_dict(), requests={"xreq_ids": args.xreq or [],
                                       "manifest": _read_json(args.requests) if args.requests else None})
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({**summary, "rows": rows}, indent=2, default=str) + "\n")
        print(f"\n[wrote JSON: {args.out}]")
        report.output(args.out)
        report.suggest(f"uv run python .claude/skills/coworld-ab/scripts/compare_report.py {args.out}")
    return {**summary, "rows": f"{len(rows)} rows; --out FILE writes them"}


def cmd_sprt(args, report: pw_cli.Report) -> dict:
    rows, exclusions, failures, arm_keys = prepare(args)
    for path, code, message in failures:
        report.fail(path, code, message)
    result = primary_sprt(rows, args.design, exclusions, h0=args.h0, h1=args.h1, alpha=args.alpha, beta=args.beta)
    record_counts(report, rows, exclusions)
    print_accounting(rows, exclusions, failures, arm_keys, args.design)
    estimate = "-" if result.estimate is None else f"{result.estimate:+.4f}"
    print(f"SPRT {PRIMARY} ({args.design}): decision {result.decision}  LLR {result.llr:.3f}  "
          f"bounds [{result.lower:.3f}, {result.upper:.3f}]  n {result.n}  estimate {estimate}"
          f"{'  (' + result.note + ')' if result.note else ''}")
    payload = {**result.as_dict(), "design": args.design, "arm_policy_keys": arm_keys, "exclusions": dict(exclusions)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(payload, indent=2) + "\n")
        report.output(args.out)
    return payload


def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("compare", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/compare.py compare ROOT --design h2h --baseline base.bas "
        "--candidate cand.bas --json",
        "uv run python paintbot_pw_lab/tools/compare.py compare ROOT --design paired --baseline james-pw:v3 "
        "--candidate james-pw:v4 --out /tmp/ab.json",
        "uv run python paintbot_pw_lab/tools/compare.py sprt ROOT --design paired --baseline james-pw:v3 "
        "--candidate james-pw:v4 --json"])
    sub = parser.add_subparsers(dest="command", required=True)
    for name, helptext in (("compare", "full A/B report"), ("sprt", "sequential stop check on the primary metric")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("roots", nargs="+", type=Path, help="episode dirs / batch dirs / .replay files (both arms)")
        p.add_argument("--design", choices=DESIGNS, required=True, help="paired | h2h | field (see the module doc)")
        p.add_argument("--baseline", required=True, help="policy_version_id, local:<name>, or name:vN")
        p.add_argument("--candidate", required=True, help="policy_version_id, local:<name>, or name:vN")
        p.add_argument("--tag", help=f"pw_trace build (default {pw_episodes.DEFAULT_TAG})")
        p.add_argument("--jobs", type=int, help="parallel traces (default: half the cores)")
        p.add_argument("--refresh", action="store_true", help="re-trace even when the cache is valid")
        p.add_argument("--h0", type=float, default=0.0, help="SPRT null effect on the primary metric")
        p.add_argument("--h1", type=float, default=0.05, help="SPRT alternative effect")
        p.add_argument("--alpha", type=float, default=0.05, help="SPRT type I error")
        p.add_argument("--beta", type=float, default=0.05, help="SPRT type II error")
        p.add_argument("--out", type=Path, help="write the full result JSON (with every row) here, e.g. "
                                                "RUN/ab.json; input for coworld-ab compare_report.py")
        if name == "compare":
            p.add_argument("--target", choices=[m[0] for m in METRICS], default=PRIMARY,
                           help="metric the verdict is about (default %(default)s)")
            p.add_argument("--metrics", help="comma list to report (pre-register it); default all")
            p.add_argument("--xreq", action="append", help="experience request id behind this batch (repeat)")
            p.add_argument("--requests", type=Path, help="pw_ab_requests.py manifest to store with the result")
    return parser


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), lambda args, report: (cmd_compare if args.command == "compare"
                                                            else cmd_sprt)(args, report), argv)


if __name__ == "__main__":
    sys.exit(main())
