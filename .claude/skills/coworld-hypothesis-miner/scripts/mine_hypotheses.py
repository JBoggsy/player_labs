#!/usr/bin/env python3
"""CLI: mine a corpus of episode rows into ranked, testable hypotheses.

Usage:
  uv run python mine_hypotheses.py --rows <episodes.jsonl> \
      --adapter <lab>/.claude/skills/<lab>-hypothesis-miner/scripts/features.py \
      [--top 5] [--out report.md] [--json assoc.json]

The rows file is JSONL, one scored episode row per line, in whatever shape the
lab's adapter expects. The adapter module must export:
  - `adapter`  : FeatureAdapter (raw_row -> Episode | None)
  - `METAS`    : dict[str, FeatureMeta]
See SKILL.md for the adapter contract.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from variance_miner import mine, render_report  # noqa: E402


def load_adapter(path: Path):
    """Import a lab's feature-adapter module by file path."""
    # The adapter imports `variance_miner`, which is already on sys.path (above).
    spec = importlib.util.spec_from_file_location("lab_features", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot import adapter module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("adapter", "METAS"):
        if not hasattr(mod, attr):
            raise SystemExit(f"adapter module {path} must export `{attr}` (see SKILL.md)")
    return mod.adapter, mod.METAS


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", required=True, help="JSONL of episode rows (one scored episode per line)")
    ap.add_argument("--adapter", required=True, help="path to the lab's features.py adapter module")
    ap.add_argument("--top", type=int, default=5, help="max hypotheses to emit")
    ap.add_argument("--out", help="write the markdown report here (default: stdout)")
    ap.add_argument("--json", dest="json_out", help="also dump the full association table as JSON")
    args = ap.parse_args()

    rows = [json.loads(line) for line in Path(args.rows).read_text().splitlines() if line.strip()]
    adapter, metas = load_adapter(Path(args.adapter))
    res = mine(rows, adapter, metas)
    report = render_report(res, top=args.top)

    if args.out:
        Path(args.out).write_text(report)
        print(f"wrote {args.out}  ({res.n_episodes} episodes, {len(res.associations)} features)", file=sys.stderr)
    else:
        print(report)

    if args.json_out:
        Path(args.json_out).write_text(json.dumps([a.__dict__ for a in res.associations], indent=2))
        print(f"wrote {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
