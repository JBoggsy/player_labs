"""Drive the cue-n-woo-analyst over downloaded tournament episodes (in-process).

Builds one episode-bundle zip per downloaded episode dir (results.json +
replay.json, which is exactly what cnw_analyst.BundleReader infers), attaches
stable per-slot player identity from episode.json.participants (so players are
aggregated across seat rotation by `policy_name:vN`), and calls the analyst's
in-process `build_and_write_report`. Writes a Parquet-table analysis zip.

Usage:
  uv run python run_analyst.py <rounds_root> <out_zip>
    rounds_root: dir containing r*/<episode-dir>/ with results.json + replay.json
    out_zip:     destination .zip for the analysis tables

Run with the analyst's own venv so its deps (pyarrow, pydantic) resolve:
  cd .../reporter_lab/cue-n-woo-analyst && uv run python <this> <root> <out>
"""
from __future__ import annotations

import glob
import io
import json
import os
import sys
import zipfile

from cnw_analyst.protocol import EpisodeInput, PlayerIdentity, ReportRequest, RoundMetadata
from cnw_analyst.service import build_and_write_report


def player_key(p: dict) -> str:
    name = p.get("policy_name") or p.get("player_name") or f"slot{p.get('position')}"
    ver = p.get("version")
    return f"{name}:v{ver}" if ver is not None else name


def build_bundle_zip(episode_dir: str, out_path: str) -> bool:
    """Zip results.json (+ replay.json) for one episode. Returns False if no results."""
    results = os.path.join(episode_dir, "results.json")
    if not os.path.exists(results):
        return False
    replay = os.path.join(episode_dir, "replay.json")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(results, "results.json")
        if os.path.exists(replay):
            zf.write(replay, "replay.json")
    with open(out_path, "wb") as f:
        f.write(buf.getvalue())
    return True


def main() -> None:
    rounds_root, out_zip = sys.argv[1], sys.argv[2]
    bundle_dir = os.path.join(rounds_root, "_bundles")
    os.makedirs(bundle_dir, exist_ok=True)

    episode_dirs = sorted(glob.glob(os.path.join(rounds_root, "r*", "*")))
    episodes: list[EpisodeInput] = []
    skipped = 0
    for ep_dir in episode_dirs:
        if not os.path.isdir(ep_dir):
            continue
        ep_json = os.path.join(ep_dir, "episode.json")
        if not os.path.exists(ep_json):
            skipped += 1
            continue
        meta = json.load(open(ep_json))
        if meta.get("status") != "completed":
            skipped += 1
            continue
        participants = meta.get("participants") or []
        if not participants:
            skipped += 1
            continue
        ep_id = meta.get("id") or os.path.basename(ep_dir)
        bundle_path = os.path.join(bundle_dir, f"{ep_id}.zip")
        if not build_bundle_zip(ep_dir, bundle_path):
            skipped += 1
            continue
        players = [
            PlayerIdentity(slot=p["position"], player_id=player_key(p),
                           display_name=f'{p.get("policy_name")}:v{p.get("version")}')
            for p in participants
        ]
        episodes.append(EpisodeInput(bundle_uri=f"file://{bundle_path}", episode_id=ep_id, players=players))

    print(f"episodes prepared: {len(episodes)} (skipped {skipped})", flush=True)
    request = ReportRequest(
        type="report_request",
        request_id="cnw-recent-10-rounds",
        report_uri=f"file://{os.path.abspath(out_zip)}",
        episodes=episodes,
        round=RoundMetadata(league="Cue N Woo", division="Competition", round_id="rounds-224-233"),
    )
    result = build_and_write_report(request)
    print(f"DONE: {result}  -> {out_zip}", flush=True)


if __name__ == "__main__":
    main()
