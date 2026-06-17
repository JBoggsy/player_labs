"""Gate-1 real-config local episode for mentalist_v4.

The stub-worker cert smoke does NOT exercise the LLM/fingerprint path (stub_worker:true,
self-play -> identical fallbacks). This builds a REAL-config episode request from the
default axis_combo variant with require_signing:false + stub_worker:false + the real fleet
worker, then runs two slots of mentalist-v4:dev against each other via
`coworld run-episode ... --use-bedrock --aws-profile softmax` so the live judge scores and
Titan fingerprinting + the passphrase flow actually run.

Usage (from repo root):
  uv run python cue_n_woo_lab/mentalist_v4/tools/gate1_real_episode.py \
      --manifest /private/tmp/cnw_research/cue-n-woo/v2/coworld/coworld_manifest.json \
      --image mentalist-v4:dev --out /tmp/v4_gate1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from coworld import certifier
from coworld.cli import load_coworld_package

FLEET = "https://cue-n-woo-fleet.softmax-research.net"


def build_request(manifest: Path) -> dict:
    pkg = load_coworld_package(manifest)
    spec = certifier.build_manifest_episode_job_spec(
        pkg, variant_id="default",
        player_images=["mentalist-v4:dev", "mentalist-v4:dev"],
        player_run=["python", "-m", "mentalist_v4"],
    )
    # by_alias=True so the schema field serializes as "$schema" (its alias), not the
    # Python attr "schema_" — the request validator rejects the unaliased name.
    req = spec.model_dump(mode="json", by_alias=True) if hasattr(spec, "model_dump") else dict(spec)
    # Override the degenerate cert game_config with the real axis_combo tournament config.
    gc = req.get("game_config") or req.get("config") or {}
    gc.update({
        "concept_type": "axis_combo",
        "concept_axis_count": 4,
        "stub_worker": False,
        "require_signing": False,
        "llm_worker_url": FLEET,
        "reveal_concept_to_clients": True,   # so the replay shows what we faced (local only)
        "round_timeout_seconds": 600,
    })
    if "game_config" in req:
        req["game_config"] = gc
    else:
        req["config"] = gc
    return req


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--image", default="mentalist-v4:dev")
    ap.add_argument("--out", default="/tmp/v4_gate1")
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    manifest = Path(args.manifest)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    req = build_request(manifest)
    req_path = out / "episode_request.json"
    req_path.write_text(json.dumps(req, indent=2))
    print(f"wrote real-config request -> {req_path}", file=sys.stderr)

    # Images + run argv live INSIDE the request (build_manifest_episode_job_spec set them);
    # the CLI forbids combining a request file with positional image overrides.
    cmd = [
        "coworld", "run-episode", str(manifest), str(req_path),
        "--use-bedrock", "--aws-profile", "softmax", "--aws-region", "us-east-1",
        "--output-dir", str(out), "--timeout-seconds", str(args.timeout),
    ]
    print("  " + " ".join(cmd), file=sys.stderr)
    # MENTALIST_TRACE_OUTPUTS so we capture the fingerprint/passphrase traces locally.
    import os
    env = dict(os.environ, MENTALIST_TRACE_OUTPUTS="jsonl@stderr")
    proc = subprocess.run(cmd, env=env)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
