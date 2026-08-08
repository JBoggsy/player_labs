#!/usr/bin/env python3
"""Run sharded, resumable download and preprocessing for an expert manifest."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


RL_ROOT = Path(__file__).resolve().parent


def prune_shard_corpora(workspace: Path) -> None:
    for shard_prepared in (workspace / "shards").glob("shard-*/prepared"):
        for pattern in ("*.samples.jsonl", "*.maps.jsonl"):
            for artifact in shard_prepared.glob(pattern):
                artifact.unlink()


def run_shard(manifest: Path, workspace: Path, log: Path) -> dict:
    prepared = workspace / "prepared" / "provenance.json"
    if prepared.exists():
        provenance = json.loads(prepared.read_text())
        return {
            "manifest": str(manifest),
            "workspace": str(workspace),
            "status": "already_complete",
            "split_counts": provenance["split_counts"],
            "failures": len(provenance.get("failures", ())),
        }

    workspace.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    with log.open("a") as output:
        for stage in ("download", "prepare"):
            command = [
                sys.executable,
                "-u",
                str(RL_ROOT / "pipeline.py"),
                stage,
                "--manifest",
                str(manifest),
                "--workspace",
                str(workspace),
            ]
            if stage == "download":
                command.append("--elevated")
            else:
                command.extend(("--artifacts-root", str(workspace / "raw")))
            output.write("+ " + " ".join(command) + "\n")
            output.flush()
            subprocess.run(
                command,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=True,
                env=environment,
            )

    provenance = json.loads(prepared.read_text())
    return {
        "manifest": str(manifest),
        "workspace": str(workspace),
        "status": "completed",
        "split_counts": provenance["split_counts"],
        "failures": len(provenance.get("failures", ())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--shards", type=int, default=8)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-episodes", type=int)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.workers <= 0:
        parser.error("--workers must be positive")

    manifests = args.workspace / "manifests"
    subprocess.run(
        [
            sys.executable,
            str(RL_ROOT / "shard_expert_manifest.py"),
            "--manifest",
            str(args.manifest),
            "--out",
            str(manifests),
            "--shards",
            str(args.shards),
            "--seed",
            str(args.seed),
            *(
                ("--max-episodes", str(args.max_episodes))
                if args.max_episodes is not None
                else ()
            ),
        ],
        check=True,
    )
    shard_manifests = sorted(manifests.glob("shard-*.json"))
    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_shard,
                manifest,
                args.workspace / "shards" / manifest.stem,
                args.workspace / "logs" / f"{manifest.stem}.log",
            ): manifest
            for manifest in shard_manifests
        }
        for future in as_completed(futures):
            manifest = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(json.dumps(result), flush=True)
            except Exception as error:
                failure = {"manifest": str(manifest), "error": str(error)}
                errors.append(failure)
                print(json.dumps(failure), flush=True)

    run_summary = {"shards": results, "errors": errors}
    (args.workspace / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2) + "\n"
    )
    if errors:
        raise RuntimeError(f"{len(errors)} preprocessing shards failed; rerun to resume")
    merged_provenance = args.workspace / "prepared" / "provenance.json"
    if merged_provenance.exists():
        prune_shard_corpora(args.workspace)
        print(f"merged corpus already complete at {merged_provenance}", flush=True)
        return 0
    subprocess.run(
        [
            sys.executable,
            str(RL_ROOT / "merge_prepared_shards.py"),
            "--shards-root",
            str(args.workspace / "shards"),
            "--out",
            str(args.workspace / "prepared"),
        ],
        check=True,
    )
    prune_shard_corpora(args.workspace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
