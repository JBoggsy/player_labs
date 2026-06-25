"""Build a warehouse report_request.json from fetch_artifacts-downloaded episode dirs.

The crewrift-event-warehouse expects a report_request.json with file:// refs to
each episode's results + (zlib) replay, plus a players list (slot/player_id/name).
Our XP-request episodes were pulled by fetch_artifacts.py into <dir>/<ts>_<ereq>/
with episode.json (participants), results.json, and replay.json.z (zlib).
"""
import json, sys
from pathlib import Path

out_dir = Path(sys.argv[1])          # where to write report_request.json
ep_roots = [Path(p) for p in sys.argv[2:]]  # one or more dirs containing *ereq* episode dirs

episodes = []
seen = set()
for root in ep_roots:
    for ep in sorted(root.glob("*ereq*")):
        rj = ep / "replay.json.z"
        rs = ep / "results.json"
        ej = ep / "episode.json"
        if not (rj.exists() and rs.exists() and ej.exists()):
            continue
        meta = json.loads(ej.read_text())
        ereq = meta.get("id") or ep.name.split("_", 1)[-1]
        if ereq in seen:
            continue
        seen.add(ereq)
        players = [
            {"slot": p["position"],
             "player_id": p.get("policy_version_id"),
             "display_name": p.get("label") or p.get("policy_name")}
            for p in (meta.get("participants") or [])
        ]
        episodes.append({
            "episode_request_id": ereq,
            "status": "success",
            "manifest": {"ereq_id": ereq, "status": "success", "include": ["results", "replay"],
                         "files": {"results": "results.json", "replay": "replay.json.z"}},
            "artifacts": {
                "results": {"uri": rs.as_uri(), "media_type": "application/json"},
                "replay": {"uri": rj.as_uri(), "media_type": "application/octet-stream", "encoding": "zlib"},
            },
            "players": players,
        })

out_dir.mkdir(parents=True, exist_ok=True)
req = {"type": "report_request", "request_id": "xp_imposter_sample",
       "report_uri": (out_dir / "REPORT_PLACEHOLDER.zip").as_uri(), "episodes": episodes}
(out_dir / "report_request.json").write_text(json.dumps(req, indent=2))
print(f"wrote {out_dir/'report_request.json'} with {len(episodes)} episodes")
