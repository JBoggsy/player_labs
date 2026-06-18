"""Live dashboard for the full v6 reference scan (build_v6_references).

Reuses the scan's own work plan (rows = 326 values x 3 questions) so counts can't drift.
Reads only cache_qsel/. Serves the shared probe_dashboard.html.

Run:  uv run python v6refs_dashboard_server.py   # http://localhost:8804
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import time

import build_v6_references as B

PORT = int(os.environ.get("PROBE_DASH_PORT", "8804"))
HERE = os.path.dirname(__file__)
DASHBOARD_HTML = os.path.join(HERE, "probe_dashboard.html")
RATE_WINDOW = 120


def compute_status() -> dict:
    axes = B.load_axes()
    allrows = B.rows(axes)
    now = time.time()

    # group by question
    per_q = {}
    for ax, v, qid in allrows:
        s = per_q.setdefault(qid, [0, 0])
        s[1] += 1
        if B.is_cached(v, qid):
            s[0] += 1
    per_axis = [{"axis": q, "values": n, "done": d, "total": n} for q, (d, n) in per_q.items()]
    done = sum(d for d, n in per_q.values())
    total = sum(n for d, n in per_q.values())

    recent_count = 0
    newest = []
    if os.path.isdir(B.CACHE):
        ents = []
        for fn in os.listdir(B.CACHE):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(B.CACHE, fn)
            try:
                mt = os.path.getmtime(path)
            except OSError:
                continue
            ents.append((mt, path))
            if now - mt <= RATE_WINDOW:
                recent_count += 1
        ents.sort(reverse=True)
        newest = ents[:12]

    rate = recent_count / (RATE_WINDOW / 60.0)
    pending = total - done
    recent = []
    for mt, path in newest:
        try:
            rec = json.load(open(path))
        except (OSError, json.JSONDecodeError):
            continue
        recent.append({"concept": f"[{rec.get('qid','?')}] {rec.get('concept','?')}"[:60], "qidx": 0,
                       "answer_preview": (rec.get("answer", "") or "")[:130],
                       "age_seconds": round(now - mt, 1)})

    return {
        "now": now, "total": total, "done": done, "pending": pending,
        "pct": round(100.0 * done / total, 1) if total else 0.0,
        "refs": {"done": done, "total": total}, "draws": {"done": 0, "total": 0},
        "per_axis": per_axis,
        "rate_per_min": round(rate, 1), "recent_count": recent_count,
        "rate_window_seconds": RATE_WINDOW,
        "eta_seconds": round(pending / rate * 60.0) if rate > 0 else None,
        "phase": "FULL v6 reference scan: 326 axis-values x 3 probe questions",
        "group_label": "Progress per probe question (326 single-axis self-reports each)",
        "axes_count": len(per_q), "questions": total,
        "worker_url": B.wc.DEFAULT_URL, "recent": recent,
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/index.html", "/dashboard"):
            body = open(DASHBOARD_HTML, "rb").read()
            ctype = "text/html"
        elif self.path.startswith("/status"):
            body = json.dumps(compute_status()).encode()
            ctype = "application/json"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"v6 reference-scan dashboard: http://localhost:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
