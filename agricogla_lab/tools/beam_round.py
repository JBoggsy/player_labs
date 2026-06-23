#!/usr/bin/env python3
"""One beam-search round for the agricogla farmhand policy (LAB / SDK version).

Same loop as the original bespoke runner, but builds via the lab path:
  build_player.sh --params '<json>'  ->  coworld upload-policy
so candidates are SDK-based farmhand images (vendored cogweb bridge), and the
mutation surface is farmhand/params.py DEFAULT_PARAMS.

Round: load beam-state -> propose N mutations off the beam -> build+upload each ->
hosted xp-request vs champion + top-2 -> parse mean score by policy_version_id ->
regression-tolerant promote (anneal) -> auto-submit on margin -> log + state.

Runs unattended via cron-beam-round.sh (setpriv + setsid + tee + flock).
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent          # agricogla_lab/
TOOLS = LAB / "tools"
STATE = TOOLS / "beam-state.json"
LOG = TOOLS / "beam-log.jsonl"
LEAGUE = "league_b81baeb4-0e1b-4e71-b162-08f46b2b6a45"
CHAMPION_REF = "agricogla-boses:v1"
CHAMPION_VID = "2664e3d4-bfaa-4576-9d29-1a81cf5ad202"
BUILD = TOOLS / "build_player.sh"

N_CANDIDATES = 3
EPISODES = 16
BEAM_WIDTH = 4
SUBMIT_MARGIN = 1.5
EXPLORE_TEMP = 0.30


def default_params() -> dict:
    sys.path.insert(0, str(LAB))
    from agricogla.farmhand.params import DEFAULT_PARAMS
    return dict(DEFAULT_PARAMS)


def log(stage: str, **kw):
    print(f"::{stage}:: " + json.dumps(kw)[:300], flush=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"t": int(time.time()), "stage": stage, **kw}) + "\n")


def sh(cmd, timeout=1200):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except (ValueError, OSError):
            pass
    seed = {"params": {}, "label": "farmhand-baseline", "score": None, "vid": None}
    beam = [seed]
    for f in sorted((LAB / "candidates").glob("[A-D]-*.json")):
        try:
            ov = {k: v for k, v in json.loads(f.read_text()).items() if not k.startswith("_")}
            beam.append({"params": ov, "label": f.stem, "score": None, "vid": None})
        except (ValueError, OSError):
            continue
    return {"round": 0, "beam": beam, "champion": seed, "history": []}


def mutate(base: dict, rng: random.Random) -> dict:
    keys = list(default_params().keys())
    out = dict(base)
    for k in rng.sample(keys, min(rng.randint(2, 4), len(keys))):
        cur = out.get(k, default_params()[k])
        out[k] = round(cur * rng.choice([0.6, 0.8, 1.25, 1.5, 1.75]), 2)
    return out


def build_upload(label: str, params: dict) -> str | None:
    tag = f"players-farmhand-{label}:dev".lower()
    name = f"agricogla-farmhand-{label}".lower().replace("_", "-")[:48]
    rc, out = sh(["bash", str(BUILD), "farmhand", "--tag", tag,
                  "--params", json.dumps(params)], timeout=1800)
    if rc != 0:
        log("build_failed", label=label, tail=out[-200:])
        return None
    rc, out = sh(["coworld", "upload-policy", tag, "--name", name], timeout=600)
    if rc != 0:
        log("upload_failed", label=label, tail=out[-200:])
        return None
    for line in out.splitlines():
        if "Upload complete:" in line:
            return line.split("Upload complete:")[1].strip()
    return f"{name}:v1"


def xp_request(cand_ref: str) -> str | None:
    body = {"target": {"league_id": LEAGUE},
            "roster": [{"slot": 0, "player": {"policy_ref": cand_ref}},
                       {"slot": 1, "player": {"policy_ref": CHAMPION_REF}},
                       {"slot": 2, "player": {"top_n": 1}},
                       {"slot": 3, "player": {"top_n": 2}}],
            "num_episodes": EPISODES, "notes": f"beam: {cand_ref} vs champion + top-2"}
    bf = TOOLS / ".xp-body.json"
    bf.write_text(json.dumps(body))
    rc, out = sh(["coworld", "xp-request", "create", str(bf), "--json"], timeout=120)
    bf.unlink(missing_ok=True)
    if rc != 0:
        return None
    try:
        return json.loads(out)["id"]
    except (ValueError, KeyError):
        return next((t for t in out.split() if t.startswith("xreq_")), None)


def poll_scores(xreq, cand_label, timeout=2700):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc, out = sh(["coworld", "xp-request", "episodes", xreq, "--json"], timeout=120)
        if rc == 0:
            try:
                eps = json.loads(out)
                eps = eps if isinstance(eps, list) else eps.get("episodes", eps.get("entries", []))
            except ValueError:
                eps = []
            done = [e for e in eps if e.get("status") == "completed" and e.get("scores")]
            if eps and len(done) >= max(1, int(0.8 * len(eps))):
                agg, labels = defaultdict(list), {}
                for e in done:
                    for p in (e.get("participants") or []):
                        labels[p["policy_version_id"]] = p.get("label", "")
                    for s in (e.get("scores") or []):
                        agg[s["policy_version_id"]].append(s["score"])
                cand = [v for pid, ss in agg.items() if labels.get(pid) == cand_label for v in ss]
                champ = agg.get(CHAMPION_VID, [])
                if cand and champ:
                    return sum(cand) / len(cand), sum(champ) / len(champ)
        time.sleep(60)
    log("poll_timeout", xreq=xreq, cand=cand_label)
    return None


def promote(beam, evaluated, rng):
    scored = [e for e in beam + evaluated if e.get("score") is not None]
    scored.sort(key=lambda e: e["score"], reverse=True)
    survivors = scored[:BEAM_WIDTH]
    for e in scored[BEAM_WIDTH:]:
        if e.get("novel") and rng.random() < EXPLORE_TEMP and len(survivors) < BEAM_WIDTH + 1:
            survivors.append(e)
            log("explore_keep", label=e["label"], score=e["score"])
    return survivors


def main():
    rng = random.Random(int(time.time()) % 100000)
    st = load_state()
    rnd = st["round"] + 1
    log("round_start", round=rnd, beam=[e["label"] for e in st["beam"]])

    parents = [e for e in st["beam"] if e.get("score") is not None] or st["beam"]
    parents.sort(key=lambda e: e.get("score") or -999, reverse=True)
    proposals = [{"params": mutate(parents[i % len(parents)].get("params", {}), rng),
                  "label": f"r{rnd}c{i}", "parent": parents[i % len(parents)]["label"], "novel": True}
                 for i in range(N_CANDIDATES)]

    evaluated = []
    for prop in proposals:
        log("building", label=prop["label"], parent=prop["parent"])
        ref = build_upload(prop["label"], prop["params"])
        if not ref:
            continue
        log("uploaded", label=prop["label"], policy=ref)
        xreq = xp_request(ref)
        if not xreq:
            continue
        log("polling", label=prop["label"], xreq=xreq, episodes=EPISODES)
        res = poll_scores(xreq, ref.split(":")[0])
        if not res:
            continue
        cand_mean, champ_mean = res
        prop.update(score=round(cand_mean, 2), delta_vs_champ=round(cand_mean - champ_mean, 2),
                    policy_ref=ref, xreq=xreq)
        evaluated.append(prop)
        log("evaluated", label=prop["label"], score=prop["score"],
            delta=prop["delta_vs_champ"], parent=prop["parent"])
        if prop["delta_vs_champ"] >= SUBMIT_MARGIN:
            rc, out = sh(["coworld", "submit", ref.split(":")[0], "--league", LEAGUE], timeout=180)
            log("submitted" if rc == 0 else "submit_failed", label=prop["label"],
                policy=ref, delta=prop["delta_vs_champ"], tail=out[-160:])

    new_beam = promote(st["beam"], evaluated, rng)
    best = max(new_beam, key=lambda e: e.get("score") or -999) if new_beam else st["champion"]
    st.update(round=rnd, beam=new_beam, champion=best)
    st["history"].append({"round": rnd, "best": best["label"], "best_score": best.get("score"),
                          "n_eval": len(evaluated)})
    STATE.write_text(json.dumps(st, indent=1))
    log("round_done", round=rnd, best=best["label"], best_score=best.get("score"),
        beam=[f'{e["label"]}={e.get("score")}' for e in new_beam])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("round_error", error=f"{type(e).__name__}: {e}")
        raise
