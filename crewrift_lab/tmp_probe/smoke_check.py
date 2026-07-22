"""Quick smoke over cand telemetry: chat_evidence_applied fires, LLM decisions
present (not all fallback), version tag sanity."""
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

root = Path(sys.argv[1])
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20

c = Counter()
eps = 0
for d in sorted(p for p in root.iterdir() if p.is_dir())[:limit]:
    z = d / "artifacts" / "policy_artifact_0.zip"
    if not z.exists():
        continue
    eps += 1
    try:
        zf = zipfile.ZipFile(z)
    except zipfile.BadZipFile:
        continue
    with zf.open("telemetry.jsonl") as f:
        for line in f:
            if b"chat_evidence_applied" in line:
                c["chat_evidence_applied"] += 1
                rec = json.loads(line)
                if rec.get("kind") == "trace" and rec.get("data", {}).get("contributions"):
                    c["chat_evidence_nonzero"] += 1
            elif b"meeting_llm_decision" in line:
                c["llm_decision"] += 1
            elif b"meeting_llm_fallback" in line:
                c["llm_fallback"] += 1
            elif b"honor_known_member" in line:
                c["honor_known_member"] += 1
print(f"eps scanned: {eps}")
for k, v in c.most_common():
    print(f"  {k}: {v}")
