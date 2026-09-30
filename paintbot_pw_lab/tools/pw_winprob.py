#!/usr/bin/env python3
"""Paintbot PW win-probability model and event credit.

A logistic model of P(team wins | team-level state at tick t), fit on hash-checked episodes
through pw_episodes, evaluated out-of-fold with folds grouped by episode, and used to credit
every capture, kill and death with its change in win probability (Leetify / CS:GO practice).

    # 1. a modest public league sample (no auth; gentle via pw_public.py: <= 40 episodes, pauses,
    #    backs off on 429; --versions defaults to the release.env version)
    uv run python paintbot_pw_lab/tools/pw_winprob.py fetch --out DIR [--max-episodes 40] [--versions X.Y.Z]
    # 2. fit + held-out evaluation + calibration + out-of-fold credit tables
    uv run python paintbot_pw_lab/tools/pw_winprob.py fit ROOT [ROOT ...] --out OUT
    # 3. credit a new batch with a saved model (in-sample for episodes that were in the fit)
    uv run python paintbot_pw_lab/tools/pw_winprob.py credit ROOT [ROOT ...] --model OUT/model.json --out OUT2

Outputs (OUT/): model.json, report.json, wp_ticks.parquet (P per sampled tick),
wp_events.parquet (one row per credited event), wp_policy.parquet (one row per
(episode, policy_key): the miner's unit). Contract: paintbot_pw_lab/docs/tools/pw_winprob.md.

P(win) is about the heart-meter winner only. The ladder ranks by the glory margin
(docs/mechanics.md §1); glory enters here only as a feature.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pw_cli  # noqa: E402
import pw_episodes  # noqa: E402
import pw_public  # noqa: E402

COMPETITION_DIVISION = pw_public.COMPETITION_DIVISION   # paintbot-pw league, Competition
MAX_FETCH_EPISODES = 40
# Keep episodes of the release the lab is pinned to (tools/release.env): "coworld-v0.3.79" -> "0.3.79".
DEFAULT_VERSIONS = pw_episodes.DEFAULT_TAG.removeprefix("coworld-v")

SAMPLE_EVERY_TICKS = 24        # fit on one row per second of play (state rows are every 6 ticks)
MIN_RULES = 47                 # behind-in-cogs glory (rules 47) changes the game being modelled
C_REGULARIZATION = 1.0         # sklearn LogisticRegression C (L2), on standardized features
FOLDS = 5
CALIBRATION_BINS = 10
PHASE_BINS_SECONDS = (0, 60, 120, 240, 600)   # early/mid/late buckets for the held-out report
THIN_EPISODES = 60             # below this many decided episodes the report says "thin data"
SWING_WINDOW_TICKS = 1440      # "worst minute": the largest one-minute drop in a team's P(win)

# Features from one team's point of view ("own" vs "enemy"). Every row is also used mirrored
# (teams swapped, label flipped), so the model is side-aware only through `side`. A feature that
# is the same for both teams (time alone) would get zero weight, so time enters as an interaction.
FEATURES = (
    "own_meter", "enemy_meter",           # meter tick-points / meter target (0..1)
    "own_hearts", "enemy_hearts",         # control hearts held / hearts on the map
    "own_lives", "enemy_lives",           # team lives left / 32 (16 seats x 2 lives)
    "own_cogs_out", "enemy_cogs_out",     # cogs out of the match / 8
    "glory_diff",                         # (own - enemy unsettled glory) / 1000
    "lives_ratio",                        # log((own lives + 1) / (enemy lives + 1)): 5 v 1 is decisive, 30 v 26 is not
    "hearts_x_time",                      # (own - enemy hearts fraction) x t / end_tick
    "race",                               # log((enemy ticks-to-fill + 24) / (own ticks-to-fill + 24))
    "side",                               # 1 if own team is Azure (odd seats)
)
BASELINE_FEATURES = ("own_meter", "enemy_meter", "own_hearts", "enemy_hearts")


# ---------------------------------------------------------------- fetch (public, gentle)

def cmd_fetch(args, report) -> dict:
    """Recent completed rounds of a division -> completed episodes of the wanted coworld
    versions -> OUT/<ereq>/episode.json (the public listing row) + replay.gz (public replay_url).
    pw_episodes reads these directories; results come from `participant_scores`.
    Requests go through pw_public (pause, back-off, User-Agent); episodes on disk are skipped."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    versions = set(args.versions.split(","))
    kept, present, skipped = 0, 0, {}
    try:
        for round_row in pw_public.rounds(division_id=args.division, limit=args.rounds):
            if kept >= args.max_episodes:
                break
            if round_row["status"] != "completed":
                skipped["round_not_completed"] = skipped.get("round_not_completed", 0) + 1
                continue
            for row in pw_public.round_episodes(round_row["id"], limit=50):
                if kept >= args.max_episodes:
                    break
                reason = pw_public.skip_reason(row, versions)
                if reason:
                    skipped[reason] = skipped.get(reason, 0) + 1
                    continue
                try:
                    new = pw_public.save_episode(out / row["id"], row, round_row)
                except pw_public.BadReplay as error:
                    print(f"{row['id']}: {error}; skipped", file=sys.stderr)
                    skipped["bad_replay"] = skipped.get("bad_replay", 0) + 1
                    continue
                kept += 1
                present += not new
                print(f"{row['id']}  round {round_row['round_number']}  {row['coworld_version']}"
                      f"{'' if new else '  (already present)'}", file=sys.stderr)
    except pw_public.RateLimited as error:
        raise pw_cli.RateLimited(f"public API rate limit ({error})",
                                 "the same winprob fetch command (already-saved episodes are skipped)") from error
    except pw_public.PublicFetchError as error:
        raise pw_cli.EnvironmentMissing(f"public API read failed ({error})",
                                        "the same command again later (network or rate limit)") from error
    print(f"fetched {kept} episodes into {out} ({present} already present); skipped {skipped or 'none'}")
    report.counts.update(processed=kept, excluded=sum(skipped.values()))
    report.output(out)
    if not kept:
        report.fail(str(out), "no_episodes", f"no completed episodes of versions {sorted(versions)} in the last "
                                             f"{args.rounds} rounds; skipped {skipped}")
    report.suggest(f"uv run python paintbot_pw_lab/tools/pw.py winprob fit {out} --json")
    return {"out": str(out), "episodes": kept, "already_present": present, "skipped": skipped,
            "versions": sorted(versions)}


# ---------------------------------------------------------------- features

def team_rows(ep) -> tuple[pd.DataFrame | None, str | None]:
    """Team-0 view of every state row plus the episode facts, or (None, exclusion reason)."""
    e = ep["episodes"].iloc[0]
    if e["mode"] != "teams" or int(e["seats"]) != 16:
        return None, "not_16_seat_teams"
    if e["map"] not in ("", None) and not pd.isna(e["map"]):
        return None, "not_heartwick"
    if int(e["rules"]) < MIN_RULES:
        return None, f"rules_below_{MIN_RULES}"
    if int(e["winner"]) not in (0, 1):
        return None, "draw"
    ts = ep["team_states"].sort_values("t").reset_index(drop=True).copy()
    ts["episode_id"] = ep.episode_id
    ts["source"] = e["source"]
    ts["end_tick"] = int(e["end_tick"])
    ts["target"] = int(e["meter_target_ticks"])
    ts["hearts"] = int(e["hearts"])
    ts["ticks"] = int(e["ticks"])
    ts["team0_won"] = int(int(e["winner"]) == 0)
    return ts, None


def features(ts: pd.DataFrame, own: int) -> pd.DataFrame:
    """FEATURES from team `own`'s point of view for every row of `ts` (team_rows output)."""
    enemy = 1 - own
    f = pd.DataFrame(index=ts.index)
    target = ts["target"].astype(float)
    for who, team in (("own", own), ("enemy", enemy)):
        f[f"{who}_meter"] = ts[f"meter_ticks_{team}"] / target
        f[f"{who}_hearts"] = ts[f"hearts_owned_{team}"] / ts["hearts"]
        f[f"{who}_lives"] = ts[f"team_lives_{team}"] / 32.0
        f[f"{who}_cogs_out"] = ts[f"cogs_out_{team}"] / 8.0
    f["glory_diff"] = (ts[f"glory_{own}"] - ts[f"glory_{enemy}"]) / 1000.0

    def ticks_to_fill(team):
        remaining = (target - ts[f"meter_ticks_{team}"]).clip(lower=0)
        # No hearts held: time to fill is at least the rest of the match.
        return np.where(ts[f"hearts_owned_{team}"] > 0, remaining / ts[f"hearts_owned_{team}"].clip(lower=1),
                        ts["end_tick"] - ts["t"] + remaining)

    time_frac = ts["t"] / ts["end_tick"]
    f["lives_ratio"] = np.log((ts[f"team_lives_{own}"] + 1.0) / (ts[f"team_lives_{enemy}"] + 1.0))
    f["hearts_x_time"] = (f["own_hearts"] - f["enemy_hearts"]) * time_frac
    f["race"] = np.log((ticks_to_fill(enemy) + 24.0) / (ticks_to_fill(own) + 24.0))
    f["side"] = float(own)
    return f[list(FEATURES)].astype(float)


def design(ts: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """Mirrored training rows: (X, y, groups, weights). Each episode weighs 1 in total."""
    x0, x1 = features(ts, 0), features(ts, 1)
    y0 = ts["team0_won"].to_numpy()
    X = pd.concat([x0, x1], ignore_index=True)
    y = np.concatenate([y0, 1 - y0])
    groups = np.concatenate([ts["episode_id"].to_numpy()] * 2)
    per_episode = ts.groupby("episode_id")["t"].transform("size").to_numpy()
    weights = np.concatenate([1.0 / per_episode] * 2) / 2
    return X, y, groups, weights


# ---------------------------------------------------------------- model

class WinModel:
    """Standardize + L2 logistic regression; P(team 0 wins) averages both points of view."""

    def __init__(self, feature_names=FEATURES, c: float = C_REGULARIZATION):
        self.feature_names = list(feature_names)
        self.scaler = StandardScaler()
        self.model = LogisticRegression(C=c, max_iter=2000)

    def fit(self, X: pd.DataFrame, y, weights) -> "WinModel":
        Z = self.scaler.fit_transform(X[self.feature_names].to_numpy())
        self.model.fit(Z, y, sample_weight=weights)
        return self

    def own_probability(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(self.scaler.transform(X[self.feature_names].to_numpy()))[:, 1]

    def team0_probability(self, ts: pd.DataFrame) -> np.ndarray:
        return (self.own_probability(features(ts, 0)) + 1 - self.own_probability(features(ts, 1))) / 2

    def to_json(self) -> dict:
        return {"features": self.feature_names, "scaler_mean": self.scaler.mean_.tolist(),
                "scaler_scale": self.scaler.scale_.tolist(), "coef": self.model.coef_[0].tolist(),
                "intercept": float(self.model.intercept_[0]), "C": self.model.C}

    @classmethod
    def from_json(cls, data: dict) -> "WinModel":
        model = cls(data["features"], data["C"])
        model.scaler.mean_ = np.array(data["scaler_mean"])
        model.scaler.scale_ = np.array(data["scaler_scale"])
        model.scaler.n_features_in_ = len(data["features"])
        model.model.coef_ = np.array([data["coef"]])
        model.model.intercept_ = np.array([data["intercept"]])
        model.model.classes_ = np.array([0, 1])
        return model


def sample_rows(ts: pd.DataFrame, every: int) -> pd.DataFrame:
    """Fit rows: every `every` ticks, strictly before the final tick (the result is known there)."""
    return ts[(ts["t"] % every == 0) & (ts["t"] < ts["ticks"])]


def out_of_fold(fit_rows: pd.DataFrame, feature_names, folds: int) -> tuple[pd.Series, dict[str, int]]:
    """Team-0 P for every row from a model that never saw that row's episode."""
    episodes = fit_rows["episode_id"].unique()
    k = min(folds, len(episodes))
    predictions = pd.Series(np.nan, index=fit_rows.index)
    fold_of = {}
    for fold, (train_idx, test_idx) in enumerate(GroupKFold(n_splits=k).split(fit_rows, groups=fit_rows["episode_id"])):
        train, test = fit_rows.iloc[train_idx], fit_rows.iloc[test_idx]
        X, y, _, w = design(train)
        model = WinModel(feature_names).fit(X, y, w)
        predictions.iloc[test_idx] = model.team0_probability(test)
        fold_of.update({episode: fold for episode in test["episode_id"].unique()})
    return predictions, fold_of


def scores(y, p, weights) -> dict:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    out = {"rows": int(len(y)), "log_loss": float(log_loss(y, p, sample_weight=weights, labels=[0, 1])),
           "brier": float(brier_score_loss(y, p, sample_weight=weights)),
           "accuracy": float(np.average((p >= 0.5) == (np.asarray(y) == 1), weights=weights))}
    out["auc"] = float(roc_auc_score(y, p, sample_weight=weights)) if len(set(y)) == 2 else None
    return out


def calibration(y, p, episodes, bins: int = CALIBRATION_BINS) -> list[dict]:
    frame = pd.DataFrame({"y": y, "p": p, "episode": episodes})
    frame["bin"] = np.minimum((frame["p"] * bins).astype(int), bins - 1)
    table = []
    for b, group in frame.groupby("bin"):
        table.append({"bin": f"{b / bins:.1f}-{(b + 1) / bins:.1f}", "rows": int(len(group)),
                      "episodes": int(group["episode"].nunique()), "mean_predicted": float(group["p"].mean()),
                      "observed": float(group["y"].mean())})
    return table


def evaluate(fit_rows: pd.DataFrame, folds: int) -> tuple[dict, pd.Series]:
    """Held-out report: full model vs a meter+hearts baseline vs a coin, by phase and source."""
    p_full, fold_of = out_of_fold(fit_rows, FEATURES, folds)
    p_base, _ = out_of_fold(fit_rows, BASELINE_FEATURES, folds)
    y = fit_rows["team0_won"].to_numpy()
    w = 1.0 / fit_rows.groupby("episode_id")["t"].transform("size").to_numpy()
    report = {
        "held_out": {"model": scores(y, p_full, w), "baseline_meter_hearts": scores(y, p_base, w),
                     "coin": scores(y, np.full(len(y), 0.5), w)},
        "calibration": calibration(y, p_full.to_numpy(), fit_rows["episode_id"].to_numpy()),
        "by_phase": [], "by_source": [],
        "folds": {"k": min(folds, fit_rows["episode_id"].nunique()), "grouped_by": "episode_id"},
    }
    seconds = fit_rows["t"] / 24.0
    for low, high in zip(PHASE_BINS_SECONDS, PHASE_BINS_SECONDS[1:]):
        mask = ((seconds >= low) & (seconds < high)).to_numpy()
        if mask.sum() and len(set(y[mask])) == 2:
            report["by_phase"].append({"seconds": f"{low}-{high}", "episodes": int(fit_rows["episode_id"][mask].nunique()),
                                       **scores(y[mask], p_full[mask], w[mask])})
    for source, group in fit_rows.groupby("source"):
        mask = (fit_rows["source"] == source).to_numpy()
        if len(set(y[mask])) == 2:
            report["by_source"].append({"source": source, "episodes": int(group["episode_id"].nunique()),
                                        **scores(y[mask], p_full[mask], w[mask])})
    return report, p_full


# ---------------------------------------------------------------- credit

def probability_series(ts: pd.DataFrame, model: WinModel) -> pd.DataFrame:
    """Team-0 P at every state row; the final row is the known result (1 or 0)."""
    p = model.team0_probability(ts)
    final = (ts["t"] >= ts["ticks"]).to_numpy()
    p[final] = ts["team0_won"].to_numpy()[final]
    return pd.DataFrame({"episode_id": ts["episode_id"], "t": ts["t"], "p_team0": p, "final": final})


def credit_events(ep, series: pd.DataFrame) -> pd.DataFrame:
    """One row per capture_complete, kill and death: the acting team's change in P(win) between
    the last state row before the event tick and the first row at or after it. Other events in
    the same bracket share the change: `bracket_events` counts them (1 = this event alone)."""
    events = []
    caps = ep["captures"]
    for row in caps[caps["kind"] == "capture_complete"].itertuples():
        events.append({"t": int(row.t), "kind": "capture", "seat": row.seat, "team": int(row.team),
                       "other_seat": pd.NA, "weapon": None})
    for row in ep["kills"].itertuples():
        if not pd.isna(row.seat) and not bool(row.self):
            events.append({"t": int(row.t), "kind": "friendly_kill" if bool(row.friendly) else "kill",
                           "seat": row.seat, "team": int(row.team), "other_seat": row.victim, "weapon": row.weapon})
        events.append({"t": int(row.t), "kind": "death", "seat": row.victim, "team": int(row.victim_team),
                       "other_seat": row.seat, "weapon": row.weapon})
    if not events:
        return pd.DataFrame()
    frame = pd.DataFrame(events)
    t_series = series["t"].to_numpy()
    p_series = series["p_team0"].to_numpy()
    after_idx = np.searchsorted(t_series, frame["t"].to_numpy(), side="left")
    after_idx = np.minimum(after_idx, len(t_series) - 1)
    before_idx = np.maximum(after_idx - 1, 0)
    frame["t_before"], frame["t_after"] = t_series[before_idx], t_series[after_idx]
    sign = np.where(frame["team"] == 0, 1.0, -1.0)
    frame["wp_before"] = np.where(sign > 0, p_series[before_idx], 1 - p_series[before_idx])
    frame["wp_after"] = np.where(sign > 0, p_series[after_idx], 1 - p_series[after_idx])
    frame["delta_wp"] = frame["wp_after"] - frame["wp_before"]
    # A kill and its death are two views of one fact: count captures + deaths per bracket.
    is_fact = frame["kind"].isin(["capture", "death"]).to_numpy()
    per_bracket = pd.Series(after_idx[is_fact]).value_counts()
    frame["bracket_events"] = pd.Series(after_idx).map(per_bracket).astype(int).to_numpy()
    frame.insert(0, "episode_id", ep.episode_id)
    return frame


def worst_minutes(series: pd.DataFrame) -> dict[int, tuple[int | None, float | None]]:
    """Per team: the start tick and size of the largest drop in its P(win) over any window of
    SWING_WINDOW_TICKS (from sampled rows)."""
    t = series["t"].to_numpy()
    p = series["p_team0"].to_numpy()
    worst = {0: (None, None), 1: (None, None)}
    j = 0
    for i in range(len(t)):
        while j < len(t) and t[j] - t[i] <= SWING_WINDOW_TICKS:
            j += 1
        if j - 1 <= i:
            continue
        change = p[i + 1:j] - p[i]
        for team, drop in ((0, -change.min()), (1, change.max())):
            if drop > 0 and (worst[team][1] is None or drop > worst[team][1]):
                worst[team] = (int(t[i]), float(drop))
    return worst


def policy_credit(ep, events: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """One row per (episode, policy_key): summed delta_wp by event kind over the policy's seats."""
    seats = ep["seats"][["seat", "team", "policy_key"]]
    worst = worst_minutes(series)
    rows = []
    for key, group in seats.groupby("policy_key"):
        teams = set(group["team"].astype(int))
        team = teams.pop() if len(teams) == 1 else None
        mine = events[events["seat"].isin(set(group["seat"]))] if len(events) else events
        row = {"episode_id": ep.episode_id, "policy_key": key, "team": team, "n_seats": len(group)}
        for kind in ("capture", "kill", "death", "friendly_kill"):
            subset = mine[mine["kind"] == kind] if len(mine) else mine
            row[f"n_{kind}s"] = int(len(subset))
            row[f"wp_{kind}s"] = float(subset["delta_wp"].sum()) if len(subset) else 0.0
        row["wp_net"] = row["wp_captures"] + row["wp_kills"] + row["wp_deaths"] + row["wp_friendly_kills"]
        start = series.iloc[0]["p_team0"]
        row["wp_start"] = None if team is None else float(start if team == 0 else 1 - start)
        row["worst_minute_start_t"] = None if team is None else worst[team][0]
        row["worst_minute_drop"] = None if team is None else worst[team][1]
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- batch plumbing

def load(roots: list[Path], jobs: int | None, report=None) -> tuple[list, list[pd.DataFrame], dict]:
    batch = pw_episodes.load_batch(roots, jobs=jobs)
    if report is not None:
        report.add_batch(batch)
    exclusions = dict(batch.exclusions)
    kept, frames = [], []
    for path, code, message in batch.failures:
        print(f"EXCLUDED [{code}] {path}: {message}", file=sys.stderr)
    for ep in batch.episodes:
        ts, reason = team_rows(ep)
        if ts is None:
            exclusions[reason] = exclusions.get(reason, 0) + 1
            print(f"EXCLUDED [{reason}] {ep.episode_id}", file=sys.stderr)
            if report is not None:
                report.counts["excluded"] += 1
            continue
        kept.append(ep)
        frames.append(ts)
    return kept, frames, exclusions


def write_credit(out: Path, episodes, frames, series_of) -> dict:
    ticks, events, policies = [], [], []
    for ep, ts in zip(episodes, frames):
        series = series_of(ep, ts)
        ticks.append(series)
        ev = credit_events(ep, series)
        events.append(ev)
        policies.append(policy_credit(ep, ev, series))
    tables = {"wp_ticks": pd.concat(ticks, ignore_index=True),
              "wp_events": pd.concat([e for e in events if len(e)], ignore_index=True),
              "wp_policy": pd.concat(policies, ignore_index=True)}
    for name, frame in tables.items():
        frame.to_parquet(out / f"{name}.parquet", index=False)
    return tables


def event_summary(events: pd.DataFrame) -> list[dict]:
    rows = []
    for kind, group in events.groupby("kind"):
        alone = group[group["bracket_events"] == 1]
        rows.append({"kind": kind, "n": int(len(group)), "mean_delta_wp": float(group["delta_wp"].mean()),
                     "n_alone_in_bracket": int(len(alone)),
                     "mean_delta_wp_alone": float(alone["delta_wp"].mean()) if len(alone) else None})
    return rows


def data_verdict(n_episodes: int, by_source: dict) -> str:
    if n_episodes < THIN_EPISODES:
        return (f"THIN DATA: {n_episodes} decided episodes (< {THIN_EPISODES}). Treat coefficients and "
                "credit as descriptive; calibration bins above ~0.2 and below ~0.8 hold few episodes.")
    verdict = f"{n_episodes} decided episodes; rows within an episode are correlated, so episodes are the sample size."
    hosted = by_source.get("hosted", 0)
    if hosted < THIN_EPISODES:
        verdict += (f" Only {hosted} are league (hosted) episodes (< {THIN_EPISODES}): the rest are local "
                    "play, a different field; read the by-source rows.")
    return verdict


def cmd_fit(args, envelope) -> dict | None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    episodes, frames, exclusions = load([Path(r) for r in args.roots], args.jobs, envelope)
    if len(episodes) < 4:
        envelope.fail("fit", "too_few_episodes", f"only {len(episodes)} usable episodes; need at least 4 "
                                                 "for a grouped split")
        envelope.exit_code = pw_cli.EXIT_PARTIAL
        return None
    all_rows = pd.concat(frames, ignore_index=True)
    fit_rows = sample_rows(all_rows, args.sample_every).reset_index(drop=True)
    report, p_oof = evaluate(fit_rows, args.folds)

    X, y, _, w = design(fit_rows)
    model = WinModel().fit(X, y, w)
    sources = all_rows.groupby("source")["episode_id"].nunique().to_dict()
    model_json = {**model.to_json(), "fitted_episodes": sorted(all_rows["episode_id"].unique()),
                  "sample_every": args.sample_every, "min_rules": MIN_RULES, "engine_release": pw_episodes.DEFAULT_TAG,
                  "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (out / "model.json").write_text(json.dumps(model_json, indent=1) + "\n")

    # Credit with out-of-fold models: refit each fold on the other episodes and apply to all
    # state rows of the held-out episodes, so no episode is credited by a model that saw it.
    fold_models = {}
    episodes_ids = fit_rows["episode_id"].unique()
    k = min(args.folds, len(episodes_ids))
    for train_idx, test_idx in GroupKFold(n_splits=k).split(fit_rows, groups=fit_rows["episode_id"]):
        Xf, yf, _, wf = design(fit_rows.iloc[train_idx])
        fold_model = WinModel().fit(Xf, yf, wf)
        for episode in fit_rows.iloc[test_idx]["episode_id"].unique():
            fold_models[episode] = fold_model
    tables = write_credit(out, episodes, frames, lambda ep, ts: probability_series(ts, fold_models[ep.episode_id]))

    report.update({
        "episodes": len(episodes), "by_source_episodes": sources, "exclusions": exclusions,
        "fit_rows": int(len(fit_rows)), "sample_every": args.sample_every,
        "team0_win_rate": float(fit_rows.groupby("episode_id")["team0_won"].first().mean()),
        "coefficients_standardized": dict(zip(FEATURES, model.model.coef_[0].round(4).tolist())),
        "credit_prediction": "out_of_fold", "event_summary": event_summary(tables["wp_events"]),
        "verdict": data_verdict(len(episodes), sources),
    })
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print_report(report, out)
    for name in ("model.json", "report.json", "wp_ticks.parquet", "wp_events.parquet", "wp_policy.parquet"):
        envelope.output(out / name)
    envelope.suggest(f"uv run python paintbot_pw_lab/tools/pw.py winprob credit NEW_ROOT --model {out}/model.json "
                     f"--out OUT2 --json")
    return {"report": str(out / "report.json"), "model": str(out / "model.json"), "verdict": report["verdict"],
            "held_out": report["held_out"], "episodes": report["episodes"], "event_summary": report["event_summary"]}


def cmd_credit(args, envelope) -> dict:
    out = Path(args.out)
    model_path = Path(args.model)
    if not model_path.is_file():
        raise pw_cli.UsageError(f"--model {model_path} does not exist (write one with `pw_winprob.py fit`)")
    out.mkdir(parents=True, exist_ok=True)
    data = json.loads(model_path.read_text())
    model = WinModel.from_json(data)
    fitted = set(data["fitted_episodes"])
    episodes, frames, exclusions = load([Path(r) for r in args.roots], args.jobs, envelope)
    if not episodes:
        envelope.fail("credit", "no_usable_episodes", f"no episode left to credit; exclusions {exclusions}")
        envelope.exit_code = pw_cli.EXIT_PARTIAL
        return None
    tables = write_credit(out, episodes, frames, lambda ep, ts: probability_series(ts, model))
    in_fit = sum(ep.episode_id in fitted for ep in episodes)
    print(f"credited {len(episodes)} episodes ({in_fit} of them were in the model's fit, so their credit is in-sample); "
          f"exclusions {exclusions or 'none'}; wrote {out}")
    summary = event_summary(tables["wp_events"])
    for row in summary:
        print(f"  {row['kind']:<14} n={row['n']:<6} mean dWP {row['mean_delta_wp']:+.4f}")
    for name in ("wp_ticks.parquet", "wp_events.parquet", "wp_policy.parquet"):
        envelope.output(out / name)
    return {"credited": len(episodes), "in_fit": in_fit, "exclusions": exclusions, "event_summary": summary}


def print_report(report: dict, out: Path) -> None:
    print(report["verdict"])
    print(f"episodes {report['episodes']} {report['by_source_episodes']}; fit rows {report['fit_rows']} "
          f"(every {report['sample_every']} ticks); team-0 win rate {report['team0_win_rate']:.2f}; "
          f"excluded {report['exclusions'] or 'none'}")
    print(f"held-out ({report['folds']['k']}-fold grouped by episode; each episode weighs 1):")
    for name, s in report["held_out"].items():
        print(f"  {name:<22} log loss {s['log_loss']:.3f}  Brier {s['brier']:.3f}  accuracy {s['accuracy']:.3f}"
              f"  AUC {s['auc'] if s['auc'] is None else round(s['auc'], 3)}")
    print("  by phase (model):")
    for s in report["by_phase"]:
        print(f"    {s['seconds']:>8} s  episodes {s['episodes']:<4} log loss {s['log_loss']:.3f}  Brier {s['brier']:.3f}  "
              f"accuracy {s['accuracy']:.3f}")
    for s in report["by_source"]:
        print(f"  source {s['source']:<7} episodes {s['episodes']:<4} log loss {s['log_loss']:.3f}  Brier {s['brier']:.3f}  "
              f"accuracy {s['accuracy']:.3f}")
    print("calibration (held-out; predicted vs observed team-0 win rate):")
    for b in report["calibration"]:
        print(f"  {b['bin']}  rows {b['rows']:<6} episodes {b['episodes']:<4} predicted {b['mean_predicted']:.3f}  "
              f"observed {b['observed']:.3f}")
    print("coefficients (standardized, full fit):", report["coefficients_standardized"])
    print("event credit (out-of-fold; delta P(win) for the acting team):")
    for row in report["event_summary"]:
        alone = "n/a" if row["mean_delta_wp_alone"] is None else f"{row['mean_delta_wp_alone']:+.4f}"
        print(f"  {row['kind']:<14} n={row['n']:<6} mean {row['mean_delta_wp']:+.4f}  "
              f"alone-in-bracket n={row['n_alone_in_bracket']} mean {alone}")
    print(f"wrote {out}/model.json, report.json, wp_ticks.parquet, wp_events.parquet, wp_policy.parquet")


def build_parser() -> pw_cli.ArgumentParser:
    parser = pw_cli.ArgumentParser("pw_winprob", __doc__, examples=[
        "uv run python paintbot_pw_lab/tools/pw_winprob.py fetch --out paintbot_pw_lab/episode_data/wp --json",
        "uv run python paintbot_pw_lab/tools/pw_winprob.py fit paintbot_pw_lab/episode_data/wp "
        "--out paintbot_pw_lab/analysis/pw_winprob/fit --json",
        "uv run python paintbot_pw_lab/tools/pw_winprob.py credit ROOT --model OUT/model.json --out OUT2 --json"])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("fetch", help="download a modest public league sample (no auth)")
    p.add_argument("--out", required=True, help="directory; one <ereq>/ per episode (e.g. episode_data/wp)")
    p.add_argument("--division", default=COMPETITION_DIVISION, help="division id (default: Competition)")
    p.add_argument("--rounds", type=int, default=6, help="most recent rounds to list (default %(default)s)")
    p.add_argument("--max-episodes", type=int, default=MAX_FETCH_EPISODES,
                   help=f"at most {MAX_FETCH_EPISODES} (default %(default)s)")
    p.add_argument("--versions", default=DEFAULT_VERSIONS,
                   help="comma-separated coworld versions to keep (default: the release.env version, %(default)s)")
    p.set_defaults(func=cmd_fetch)

    for name, func in (("fit", cmd_fit), ("credit", cmd_credit)):
        p = sub.add_parser(name, help="fit + held-out evaluation" if name == "fit" else "credit with a saved model")
        p.add_argument("roots", nargs="+", help="episode or batch directories")
        p.add_argument("--out", required=True, help="output directory (e.g. paintbot_pw_lab/analysis/pw_winprob/fit)")
        p.add_argument("--jobs", type=int, help="parallel trace jobs (default: half the cores)")
        p.set_defaults(func=func)
    fit, credit = sub.choices["fit"], sub.choices["credit"]
    fit.add_argument("--sample-every", type=int, default=SAMPLE_EVERY_TICKS, help="fit rows every N ticks (default %(default)s)")
    fit.add_argument("--folds", type=int, default=FOLDS, help="grouped folds (default %(default)s)")
    credit.add_argument("--model", required=True, help="model.json written by fit")
    return parser


def run_cli(args, report):
    if args.command == "fetch" and args.max_episodes > MAX_FETCH_EPISODES:
        raise pw_cli.UsageError(f"--max-episodes is capped at {MAX_FETCH_EPISODES} (be gentle with the public API)")
    return args.func(args, report)


def main(argv: list[str] | None = None) -> int:
    return pw_cli.run(build_parser(), run_cli, argv)


if __name__ == "__main__":
    sys.exit(main())
