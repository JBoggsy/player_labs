"""Verify the trust floor is live in the hosted cand arm: dump every
chat_evidence_applied contributions dict. Under the 0.9 floor, single-speaker
accusation terms must be >= 0.9*ln1.5 (0.365) and typically ln1.5 (0.405, HS);
the v1 signature values like 0.29 (0.71*ln1.5) must be absent."""
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1])
vals = Counter()
n = 0
for d in sorted(p for p in root.iterdir() if p.is_dir()):
    z = d / "artifacts" / "policy_artifact_0.zip"
    if not z.exists():
        continue
    try:
        zf = zipfile.ZipFile(z)
    except zipfile.BadZipFile:
        continue
    with zf.open("telemetry.jsonl") as f:
        for line in f:
            if b"chat_evidence_applied" not in line or b'"trace"' not in line:
                continue
            rec = json.loads(line)
            for color, v in (rec.get("data", {}).get("contributions") or {}).items():
                vals[round(v, 3)] += 1
                n += 1
print(f"total nonzero contributions: {n}")
for v, c in sorted(vals.items()):
    print(f"  {v:+.3f}: {c}")
