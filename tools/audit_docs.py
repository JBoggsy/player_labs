#!/usr/bin/env python3
"""Inventory owned documentation and check local Markdown/HTML file targets.

Checks targets, not heading anchors or semantic correctness. Skips generated local
artifacts and code fences. All documentation targets are checked.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def inventory(root: Path = ROOT) -> dict:
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root
    ).decode().split('\0')
    docs, broken = [], []
    for name in sorted(set(names)):
        path = root / name
        if path.suffix not in {'.md', '.html'} or not path.is_file():
            continue
        docs.append({'path': name, 'class': 'current'})
        source = re.sub(r'(?ms)^```.*?^```[^\n]*', '', path.read_text())
        targets = re.findall(r'\]\(([^\n)]+)\)|(?:href|src)=["\']([^"\']+)["\']', source)
        for markdown, html in targets:
            target = (markdown or html).split(' "', 1)[0].strip('<> ')
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            if any(token in target for token in ('<', '>', '{', '}', '$', '*', '`')):
                continue  # Template, not a concrete file claim.
            local = re.sub(r":\d+(?:-\d+)?$", "", unquote(parsed.path))
            if local.startswith('/'):
                continue  # Machine/web-root targets aren't repository-relative links.
            if not (path.parent / local).exists():
                broken.append({'path': name, 'target': target, 'class': 'current'})
    return {'documents': docs, 'broken_targets': broken,
            'limits': 'Local file targets only; no anchor, remote URL, command or semantic verification.'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path, help='Write detailed inventory')
    args = parser.parse_args()
    result = inventory()
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + '\n')
    current = [row for row in result['broken_targets'] if row['class'] == 'current']
    print(f"{len(result['documents'])} documents; {len(current)} broken targets")
    for row in current:
        print(f"{row['path']}: {row['target']}")
    return bool(current)


if __name__ == '__main__':
    raise SystemExit(main())
