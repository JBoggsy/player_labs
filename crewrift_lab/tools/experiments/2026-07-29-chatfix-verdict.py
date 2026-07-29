#!/usr/bin/env python3
"""Prereg verdict for 2026-07-29-chat-swallow-fix-prereg.md.

Cand (crewborg-chatfix:v1) vs baseline (loop-3 fresh v117 batch).
Adds the accusation landed-rate + votes-on-target instruments (telemetry chat_sent
vs RAW replay chat records — not the capped warehouse chat partition).

Usage: uv run python verdict.py --cand-wh ... --cand-eps ... --base-wh ... --base-eps ...
"""
from __future__ import annotations
import argparse, json, math, os, re, glob, zipfile
from collections import defaultdict
import duckdb
from scipy.stats import mannwhitneyu


def replay_has_text(replay_path: str, text: str) -> bool:
    try:
        data = open(replay_path, "rb").read()
    except OSError:
        return False
    return data.count(text.encode("ascii", "ignore")[:60]) > 0


def side(wh: str, eps_dir: str, policy: str) -> dict:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW players AS SELECT * FROM read_parquet('{wh}/episode_players.parquet')")
    m: dict = {}
    ops = {r[0] for r in con.execute(
        "SELECT DISTINCT episode_id FROM players WHERE slot>=0 AND (score <= -100 OR score IS NULL)").fetchall()}
    m["ops_eps"] = len(ops)
    subj = con.execute("SELECT episode_id, role, win FROM players WHERE slot=0").fetchall()
    subj = [s for s in subj if s[0] not in ops]
    crew = [(e, w) for e, r, w in subj if r in ("crew", "crewmate")]
    imp = [(e, w) for e, r, w in subj if r == "imposter"]
    m["n_crew"], m["n_imp"] = len(crew), len(imp)
    m["crew_wins"] = sum(1 for _, w in crew if w)
    m["imp_wins"] = sum(1 for _, w in imp if w)
    crew_eps = {e for e, _ in crew}

    cmap, roles = {}, {}
    for ep, slot, color, role in con.execute(f"""
      SELECT episode_id, slot, lower(json_extract_string(value,'$.color')), json_extract_string(value,'$.role')
      FROM read_parquet('{wh}/events/key=player_manifest/*.parquet')
      WHERE json_extract_string(value,'$.source')='replay' AND slot>=0""").fetchall():
        cmap[(ep, color)] = slot
        roles[(ep, slot)] = role
    votes = defaultdict(list)
    for ep, ts, tslot in con.execute(f"""
      SELECT episode_id, ts, TRY_CAST(json_extract_string(value,'$.target_slot') AS INT)
      FROM read_parquet('{wh}/events/key=vote_cast/*.parquet')
      WHERE slot >= 1 AND json_extract_string(value,'$.target_slot') IS NOT NULL""").fetchall():
        votes[ep].append((ts, tslot))

    # HS landed (mechanism): from warehouse chat (HS is the FIRST chat usually — cap-safe check via raw replay)
    sent = landed = 0
    hs_sent = hs_landed = 0
    votes_on_target_landed = []
    votes_on_imp_target = []
    for d in glob.glob(os.path.join(eps_dir, "*/")):
        z = os.path.join(d, "artifacts", "policy_artifact_0.zip")
        ej = os.path.join(d, "episode.json")
        rp = os.path.join(d, "replay.json")
        if not (os.path.exists(z) and os.path.exists(ej) and os.path.exists(rp)):
            continue
        eid = json.load(open(ej)).get("id")
        if eid in ops or eid not in crew_eps:
            continue
        sends = []
        with zipfile.ZipFile(z) as zf:
            with zf.open("telemetry.jsonl") as f:
                for line in f:
                    if b"domain.chat_sent" not in line:
                        continue
                    j = json.loads(line)
                    if j.get("kind") == "trace":
                        sends.append((j["tick"], j["data"]["text"]))
        raw = open(rp, "rb").read()
        for tick, text in sends:
            is_hs = text.startswith("HS1 ")
            hit = raw.count(text.encode("ascii", "ignore")[:60]) > 0
            if is_hs:
                hs_sent += 1
                hs_landed += hit
                continue
            if " sus" not in text:
                continue
            sent += 1
            landed += hit
            color = text.split(" ")[0]
            tslot = cmap.get((eid, color))
            if hit and tslot is not None:
                nv = sum(1 for ts, vt in votes[eid] if vt == tslot and tick < ts <= tick + 1300)
                votes_on_target_landed.append(nv)
                if roles.get((eid, tslot)) == "imposter":
                    votes_on_imp_target.append(nv)
    m["acc_sent"], m["acc_landed"] = sent, landed
    m["hs_sent"], m["hs_landed"] = hs_sent, hs_landed
    m["votes_on_imp_target"] = votes_on_imp_target

    # standard guards
    rows = con.execute(f"""
    WITH sel AS (
      SELECT episode_id, ts,
             lower(json_extract_string(value,'$.target')) AS target_color,
             json_extract_string(value,'$.truth_roles.' || json_extract_string(value,'$.target')) AS target_role
      FROM read_parquet('{wh}/events/key=belief_meeting_vote_selected/*.parquet')
      WHERE json_extract_string(value,'$.target') != 'skip'
    ),
    cmap AS (
      SELECT episode_id, slot AS tslot, lower(json_extract_string(value,'$.color')) AS color
      FROM read_parquet('{wh}/events/key=player_manifest/*.parquet')
      WHERE json_extract_string(value,'$.source')='replay' AND slot >= 0
    ),
    deaths AS (
      SELECT episode_id, slot AS dslot, MIN(ts) AS death_ts FROM (
        SELECT episode_id, TRY_CAST(json_extract(value,'$.victim_slot') AS INT) AS slot, ts
        FROM read_parquet('{wh}/events/key=kill/*.parquet')
        UNION ALL SELECT episode_id, slot, ts FROM read_parquet('{wh}/events/key=died/*.parquet') WHERE slot>=0
      ) GROUP BY 1,2
    )
    SELECT s.episode_id, s.target_role,
           (d.death_ts IS NOT NULL AND d.death_ts >= s.ts AND d.death_ts <= s.ts + 1400) AS ej
    FROM sel s
    LEFT JOIN cmap c ON c.episode_id=s.episode_id AND c.color=s.target_color
    LEFT JOIN deaths d ON d.episode_id=s.episode_id AND d.dslot=c.tslot
    """).fetchall()
    rows = [r for r in rows if r[0] not in ops and r[0] in crew_eps]
    m["hits"] = sum(1 for r in rows if r[1] == "imposter")
    m["mis"] = sum(1 for r in rows if r[1] in ("crew", "crewmate"))
    m["mis_ej"] = sum(1 for r in rows if r[1] in ("crew", "crewmate") and r[2])
    m["vote_timeouts"] = con.execute(f"""
      SELECT COUNT(*) FROM read_parquet('{wh}/events/key=score/*.parquet')
      WHERE slot=0 AND json_extract_string(value,'$.reason') LIKE '%failing to vote%'""").fetchone()[0]
    return m


def ztest(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p1 - p2) / se
    from math import erf, sqrt
    return z, 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand-wh", required=True); ap.add_argument("--cand-eps", required=True)
    ap.add_argument("--base-wh", required=True); ap.add_argument("--base-eps", required=True)
    args = ap.parse_args()
    C = side(args.cand_wh, args.cand_eps, "crewborg-chatfix")
    B = side(args.base_wh, args.base_eps, "crewborg")
    print(f"cand: crew {C['n_crew']} imp {C['n_imp']} ops {C['ops_eps']}")
    print(f"base: crew {B['n_crew']} imp {B['n_imp']} ops {B['ops_eps']}")
    print()
    lrC = C["acc_landed"] / C["acc_sent"]; lrB = B["acc_landed"] / B["acc_sent"]
    print(f"PRIMARY-1 accusation landed-rate: cand {C['acc_landed']}/{C['acc_sent']} = {lrC:.1%} "
          f"vs base {B['acc_landed']}/{B['acc_sent']} = {lrB:.1%}  (bar >=90%)")
    vC, vB = C["votes_on_imp_target"], B["votes_on_imp_target"]
    mC = sum(vC)/len(vC) if vC else 0; mB = sum(vB)/len(vB) if vB else 0
    if vC and vB:
        u, p = mannwhitneyu(vC, vB, alternative="greater")
        print(f"PRIMARY-2 votes-on-our-imp-target (landed acc): cand {mC:.2f} (n={len(vC)}) "
              f"vs base {mB:.2f} (n={len(vB)})  MW 1-sided p={p:.4f}")
    print()
    hsC = C["hs_landed"]/C["hs_sent"] if C["hs_sent"] else 0
    hsB = B["hs_landed"]/B["hs_sent"] if B["hs_sent"] else 0
    print(f"MECH-3 HS1 landed: cand {C['hs_landed']}/{C['hs_sent']} = {hsC:.1%} "
          f"vs base {B['hs_landed']}/{B['hs_sent']} = {hsB:.1%}  (bar >=90%)")
    print()
    z, pv = ztest(C["crew_wins"], C["n_crew"], B["crew_wins"], B["n_crew"])
    print(f"GUARD-4 crew WR: cand {C['crew_wins']/C['n_crew']:.1%} vs base {B['crew_wins']/B['n_crew']:.1%} (z={z:+.2f} p={pv:.3f})")
    z2, pv2 = ztest(C["imp_wins"], C["n_imp"], B["imp_wins"], B["n_imp"])
    print(f"GUARD-5 imposter WR: cand {C['imp_wins']/C['n_imp']:.1%} vs base {B['imp_wins']/B['n_imp']:.1%} (z={z2:+.2f} p={pv2:.3f})")
    print(f"GUARD-6 vote_timeouts: cand {C['vote_timeouts']} base {B['vote_timeouts']}")
    meC = C["mis_ej"]/C["n_crew"]; meB = B["mis_ej"]/B["n_crew"]
    print(f"GUARD-7 mis-ej-we-voted/cep: cand {meC:.3f} vs base {meB:.3f} (bar {1.5*meB:.3f})")
    hC = C["hits"]/C["n_crew"]; hB = B["hits"]/B["n_crew"]
    print(f"GUARD-8 hits/cep: cand {hC:.3f} vs base {hB:.3f} (must not be down)")


if __name__ == "__main__":
    main()
