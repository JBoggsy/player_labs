"""Live dashboard for probe_selfreport_v2 (single-axis refs + 4-axis samples).

Reads only cache_srv2/; reuses the scan's own work plan so counts can't drift.
Run:  uv run python srv2_dashboard_server.py   # http://localhost:8802
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import time

import probe_selfreport_v2 as P

PORT = int(os.environ.get("PROBE_DASH_PORT", "8802"))
HERE = os.path.dirname(__file__)
DASHBOARD_HTML = os.path.join(HERE, "probe_dashboard.html")
RATE_WINDOW = 120
SAMPLES = int(os.environ.get("SRV2_SAMPLES", "40"))


def compute_status() -> dict:
    axes = P.load_axes()
    refs = [v for _, v in P.all_values(axes)]
    combos = ["; ".join(v for _, v in c) for c in P.sample_combos(axes, SAMPLES)]
    now = time.time()

    refs_done = sum(1 for v in refs if P.is_cached(v))
    samp_done = sum(1 for c in combos if P.is_cached(c))
    done = refs_done + samp_done
    total = len(refs) + len(combos)

    per_axis = [
        {"axis": "single-axis refs", "values": len(refs), "done": refs_done, "total": len(refs)},
        {"axis": "4-axis samples", "values": len(combos), "done": samp_done, "total": len(combos)},
    ]

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
        recent.append({"concept": rec.get("concept", "?")[:60], "qidx": 0,
                       "answer_preview": (rec.get("answer", "") or "")[:130],
                       "age_seconds": round(now - mt, 1)})

    return {
        "now": now, "total": total, "done": done, "pending": pending,
        "pct": round(100.0 * done / total, 1) if total else 0.0,
        "refs": {"done": refs_done, "total": len(refs)},
        "draws": {"done": samp_done, "total": len(combos)},
        "per_axis": per_axis,
        "rate_per_min": round(rate, 1), "recent_count": recent_count,
        "rate_window_seconds": RATE_WINDOW,
        "eta_seconds": round(pending / rate * 60.0) if rate > 0 else None,
        "phase": "refs" if refs_done < len(refs) else "samples",
        "axes_count": 1, "questions": len(refs) + len(combos),
        "worker_url": P.wc.DEFAULT_URL, "recent": recent,
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/index.html", "/dashboard"):
            self._send(DASHBOARD_HTML, "text/html", binary=True)
        elif self.path.startswith("/status"):
            body = json.dumps(compute_status()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def _send(self, path, ctype, binary=False):
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


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"SRv2 dashboard: http://localhost:{PORT}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
