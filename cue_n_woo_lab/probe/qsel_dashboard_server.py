"""Live dashboard for the question-selection probe (probe_question_selection).

Reuses the probe's own work plan (sample_refs + sample_combos + CANDIDATES + cache_path)
so counts can't drift. Reads only cache_qsel/. Serves the shared probe_dashboard.html.

Run:  uv run python qsel_dashboard_server.py   # http://localhost:8803
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import time

import probe_question_selection as P

PORT = int(os.environ.get("PROBE_DASH_PORT", "8803"))
HERE = os.path.dirname(__file__)
DASHBOARD_HTML = os.path.join(HERE, "probe_dashboard.html")
RATE_WINDOW = 120


def compute_status() -> dict:
    axes = P.load_axes()
    refs = P.sample_refs(axes)
    combos = ["; ".join(v for _, v in c) for c in P.sample_combos(axes, refs)]
    ref_vals = [v for _, v in refs]
    now = time.time()

    # per-question progress group (the axis-bars UI), refs+combos each
    per_q = []
    done = total = 0
    for qid in P.CANDIDATES:
        d = sum(1 for v in ref_vals if P.is_cached(v, qid)) + sum(1 for c in combos if P.is_cached(c, qid))
        n = len(ref_vals) + len(combos)
        per_q.append({"axis": qid, "values": n, "done": d, "total": n})
        done += d
        total += n

    recent_count = 0
    newest = []
    if os.path.isdir(P.CACHE):
        ents = []
        for fn in os.listdir(P.CACHE):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(P.CACHE, fn)
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
        "per_axis": per_q,
        "rate_per_min": round(rate, 1), "recent_count": recent_count,
        "rate_window_seconds": RATE_WINDOW,
        "eta_seconds": round(pending / rate * 60.0) if rate > 0 else None,
        "phase": "selecting 3 of 6 candidate PROBE QUESTIONS (measuring per-axis recovery)",
        "group_label": "Progress per candidate probe-question (these are QUESTIONS, not game axes)",
        "axes_count": len(P.CANDIDATES), "questions": total,
        "worker_url": P.wc.DEFAULT_URL, "recent": recent,
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
        print(f"Question-selection dashboard: http://localhost:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
