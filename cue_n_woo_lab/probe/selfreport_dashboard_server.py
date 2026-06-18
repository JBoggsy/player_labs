"""Live dashboard for the self-report fingerprint scan (probe_selfreport_fingerprint).

Reuses the scan's own work plan (sample_concepts + the probe dicts + cache_path) so
counts can't drift. Reads only cache_sr/. Serves the shared probe_dashboard.html.

Run:  uv run python selfreport_dashboard_server.py   # http://localhost:8801
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import time

import probe_selfreport_fingerprint as P

PORT = int(os.environ.get("PROBE_DASH_PORT", "8801"))
HERE = os.path.dirname(__file__)
DASHBOARD_HTML = os.path.join(HERE, "probe_dashboard.html")
RATE_WINDOW = 120
CONCEPTS = int(os.environ.get("SR_CONCEPTS", "60"))


def _plan():
    axes = P.load_axes()
    concepts = P.sample_concepts(axes, CONCEPTS)
    probes = {**P.SELF_REPORT_PROBES, **P.BASELINE_PROBES}
    return concepts, probes


def compute_status() -> dict:
    concepts, probes = _plan()
    now = time.time()
    # group "per_axis" view by probe name (reuse the axis-bars UI)
    per_probe = []
    done = total = 0
    for name, text in probes.items():
        d = sum(1 for c in concepts
                if os.path.exists(P.cache_path("; ".join(v for _, v in c), text)))
        per_probe.append({"axis": name, "values": len(concepts), "done": d, "total": len(concepts)})
        done += d
        total += len(concepts)

    recent_count = 0
    newest = []
    if os.path.isdir(P.CACHE):
        entries = []
        for fn in os.listdir(P.CACHE):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(P.CACHE, fn)
            try:
                mt = os.path.getmtime(path)
            except OSError:
                continue
            entries.append((mt, path))
            if now - mt <= RATE_WINDOW:
                recent_count += 1
        entries.sort(reverse=True)
        newest = entries[:12]

    rate = recent_count / (RATE_WINDOW / 60.0)
    pending = total - done
    eta = round(pending / rate * 60.0) if rate > 0 else None

    recent = []
    for mt, path in newest:
        try:
            rec = json.load(open(path))
        except (OSError, json.JSONDecodeError):
            continue
        recent.append({"concept": rec.get("concept", "?")[:60],
                       "qidx": 0,
                       "answer_preview": (rec.get("answer", "") or "")[:130],
                       "age_seconds": round(now - mt, 1)})

    return {
        "now": now, "total": total, "done": done, "pending": pending,
        "pct": round(100.0 * done / total, 1) if total else 0.0,
        "refs": {"done": done, "total": total},
        "draws": {"done": 0, "total": 0},
        "per_axis": per_probe,
        "rate_per_min": round(rate, 1), "recent_count": recent_count,
        "rate_window_seconds": RATE_WINDOW,
        "eta_seconds": eta,
        "phase": f"self-report scan ({CONCEPTS} concepts)",
        "axes_count": len(probes), "questions": CONCEPTS,
        "worker_url": P.wc.DEFAULT_URL, "recent": recent,
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/index.html", "/dashboard"):
            self._file(DASHBOARD_HTML, "text/html")
        elif self.path.startswith("/status"):
            self._json(compute_status())
        else:
            self.send_error(404)

    def _file(self, path, ctype):
        try:
            body = open(path, "rb").read()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Self-report scan dashboard: http://localhost:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
