"""Peek at key telemetry payloads from one W3 cand episode."""
import json
import sys
import zipfile

z = zipfile.ZipFile(sys.argv[1])
want = {
    "domain.chat_received",
    "domain.honor_known_member",
    "domain.honor_claim",
    "domain.chat_evidence_applied",
    "domain.suspicion_snapshot",
    "domain.role_resolved",
}
with z.open("telemetry.jsonl") as f:
    for line in f:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("name") in want:
            print(json.dumps(rec)[:600])
