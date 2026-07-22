"""Meeting-LLM spend profile from crewborg episode-artifact dirs: per trigger, per meeting
order, per role, plus per-seat estimated USD.

Usage: uv run python crewrift_lab/tools/spend_profile.py EPISODE_DIR [EPISODE_DIR ...]

Each EPISODE_DIR holds per-episode subdirs with artifacts/policy_artifact_0.zip (slot 0 =
crewborg), as produced by the coworld-episode-artifacts pipeline. Works on pre-llm_spend
telemetry (meeting_llm_call/decision/fallback); once domain.llm_spend ships (W4, see
docs/designs/2026-07-22-bedrock-spend-telemetry-design.md) the per-call events carry these
numbers directly. Rates mirror the sidecar's haiku family pricing.
"""
import json, zipfile, glob, collections, sys

IN_RATE, OUT_RATE = 1.0, 5.0  # haiku USD/1M

trig = collections.defaultdict(lambda: collections.Counter())
trig_tokens = collections.defaultdict(lambda: [0,0,0])  # in, out, n
trig_actions = collections.defaultdict(collections.Counter)
meet_order = collections.defaultdict(lambda: collections.Counter())
role_stats = collections.defaultdict(lambda: collections.Counter())
lat = collections.defaultdict(list)
seats = 0
seat_costs = []

dirs = sys.argv[1:]
if not dirs:
    sys.exit("usage: spend_profile.py EPISODE_DIR [EPISODE_DIR ...]")
for d in dirs:
    for ep in sorted(glob.glob(d + "/*")):
        for z in glob.glob(ep + "/artifacts/policy_artifact_0.zip"):  # slot 0 = crewborg
            try: data = zipfile.ZipFile(z).read("telemetry.jsonl")
            except Exception: continue
            seats += 1
            role = None
            meeting_idx = -1
            last_phase_meeting = None
            seat_cost = 0.0
            for line in data.splitlines():
                if b"role_resolved" in line:
                    try: rec = json.loads(line)
                    except Exception: continue
                    if rec.get("event")=="domain.role_resolved":
                        role = rec["data"].get("role")
                    continue
                if b"meeting_llm" not in line: continue
                try: rec = json.loads(line)
                except Exception: continue
                ev = rec.get("event",""); d_ = rec.get("data",{})
                if ev == "domain.meeting_llm_call":
                    t = d_.get("trigger")
                    if d_.get("calls_used") == 1:
                        meeting_idx += 1
                    trig[t]["calls"] += 1
                    meet_order[min(meeting_idx,4)]["calls"] += 1
                    role_stats[role]["calls"] += 1
                elif ev == "domain.meeting_llm_decision":
                    t = d_.get("trigger")
                    trig[t]["decisions"] += 1
                    u = d_.get("usage") or {}
                    ti, to = u.get("input_tokens") or 0, u.get("output_tokens") or 0
                    trig_tokens[t][0]+=ti; trig_tokens[t][1]+=to; trig_tokens[t][2]+=1
                    seat_cost += ti*IN_RATE/1e6 + to*OUT_RATE/1e6
                    act = (d_.get("decision") or {}).get("action")
                    trig_actions[t][act] += 1
                    meet_order[min(meeting_idx,4)]["decisions"] += 1
                    role_stats[role]["decisions"] += 1
                    if d_.get("latency_ms"): lat[t].append(d_["latency_ms"])
                elif ev == "domain.meeting_llm_fallback" and d_.get("reason")=="llm_call_failed":
                    t = d_.get("trigger")
                    err = d_.get("error") or ""
                    cls = "429" if ("429" in err or "Too many" in err) else ("timeout" if "Timeout" in err or "timed out" in err else "other")
                    trig[t][f"fail_{cls}"] += 1
                    meet_order[min(meeting_idx,4)][f"fail_{cls}"] += 1
                    role_stats[role][f"fail_{cls}"] += 1
            seat_costs.append(seat_cost)

print("crewborg slot-0 seats scanned:", seats)
print("\n=== per trigger ===")
print(f"{'trigger':22s} {'calls':>6s} {'dec':>5s} {'f429':>5s} {'fTO':>4s} {'foth':>4s} {'succ%':>6s} {'tok_in':>7s} {'tok_out':>7s} {'$/succ':>8s}")
for t in sorted(trig, key=lambda x: -trig[x]["calls"]):
    c = trig[t]
    ti, to, n = trig_tokens[t]
    cost = (ti*IN_RATE + to*OUT_RATE)/1e6/n if n else 0
    calls = c["calls"]
    print(f"{t:22s} {calls:6d} {c['decisions']:5d} {c['fail_429']:5d} {c['fail_timeout']:4d} {c['fail_other']:4d} {100*c['decisions']/max(calls,1):5.1f}% {ti//max(n,1):7d} {to//max(n,1):7d} {cost:8.5f}")
print("\n=== decision actions per trigger ===")
for t in trig_actions:
    print(f"{t:22s} {dict(trig_actions[t])}")
print("\n=== per meeting order (0-indexed, 4=4+) ===")
for m in sorted(meet_order):
    c = meet_order[m]
    print(f"meeting {m}: calls={c['calls']:5d} dec={c['decisions']:4d} f429={c['fail_429']:5d} fTO={c['fail_timeout']:3d}")
print("\n=== per role ===")
for r in role_stats:
    c = role_stats[r]
    print(f"{r}: calls={c['calls']} dec={c['decisions']} f429={c['fail_429']} fTO={c['fail_timeout']}")
import statistics
nz=[c for c in seat_costs if c>0]
print("\nseat est cost: mean=$%.5f median=$%.5f max=$%.5f (nonzero n=%d/%d)" % (statistics.fmean(seat_costs), statistics.median(seat_costs), max(seat_costs), len(nz), len(seat_costs)))
print("total est cost across seats: $%.4f" % sum(seat_costs))
