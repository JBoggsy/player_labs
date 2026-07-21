#!/usr/bin/env python3
"""Build a bounded, verified subset of an existing scraped corpus (e.g.
suspicion_lab's corpus/ + expanded/) for a historical cross-check.

Not every scraped batch has a complete 4-file set (episode.json + replay.json
+ replay.json.z + results.json) — the most recent batch in a corpus is often
an interrupted/partial scrape (episode.json only). This walks the corpus in
chronological order (directory names are timestamp-prefixed) and symlinks the
first N directories that have BOTH results.json (needed for win/role/policy
outcomes) AND a matching expanded/<name>.jsonl.gz (needed for chat/vote
parsing) into two output directories, so downstream tools can point at a
uniform, complete slice instead of the raw corpus.

Usage:
    uv run python crewrift_lab/chat_effectiveness/tools/build_historical_subset.py \
        --corpus crewrift_lab/suspicion_lab/corpus \
        --expanded crewrift_lab/suspicion_lab/expanded \
        --out-corpus /tmp/hist_corpus_subset --out-expanded /tmp/hist_expanded_subset \
        --limit 3000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def build_subset(corpus: Path, expanded: Path, out_corpus: Path, out_expanded: Path, limit: int) -> tuple[int, int]:
    out_corpus.mkdir(parents=True, exist_ok=True)
    out_expanded.mkdir(parents=True, exist_ok=True)

    candidates = sorted(d.name for d in corpus.iterdir() if d.is_dir())
    linked = 0
    skipped = 0
    for name in candidates:
        if linked >= limit:
            break
        corpus_dir = corpus / name
        expanded_file = expanded / f"{name}.jsonl.gz"
        if not (corpus_dir / "results.json").exists() or not expanded_file.exists():
            skipped += 1
            continue
        (out_corpus / name).symlink_to(corpus_dir, target_is_directory=True)
        (out_expanded / f"{name}.jsonl.gz").symlink_to(expanded_file)
        linked += 1
    return linked, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--expanded", type=Path, required=True)
    parser.add_argument("--out-corpus", type=Path, required=True)
    parser.add_argument("--out-expanded", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=3000, help="Max episodes to link (chronological order).")
    args = parser.parse_args(argv)

    linked, skipped = build_subset(args.corpus, args.expanded, args.out_corpus, args.out_expanded, args.limit)
    print(f"Linked {linked} complete episodes -> {args.out_corpus} / {args.out_expanded}", file=sys.stderr)
    print(f"Skipped {skipped} (missing results.json or expanded replay)", file=sys.stderr)
    if linked == 0:
        sys.exit("No complete episodes found — check --corpus/--expanded paths and that a scrape has finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
