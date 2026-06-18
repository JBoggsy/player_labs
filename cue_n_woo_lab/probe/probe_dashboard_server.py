"""Live dashboard server for the axis-recovery probe.

Serves a self-contained dashboard at `/` and a JSON status feed at `/status`,
computed live from the cache/ directory. It only READS the cache, so it runs
safely alongside the in-progress probe and needs no changes to it.

Status is derived from the probe's OWN deterministic work plan (it imports
`probe_axis_recovery` and reuses `reference_concepts`/`build_test_draws`/
`_cache_path`), so the dashboard's totals can never drift from what the probe
actually generates.

Run:  uv run python probe_dashboard_server.py        # then open http://localhost:8787
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import time

import probe_axis_recovery as P

PORT = 8799  # 8787 is often taken by a stray `python -m http.server`; override with PROBE_DASH_PORT
PORT = int(os.environ.get("PROBE_DASH_PORT", PORT))
HERE = os.path.dirname(__file__)
DASHBOARD_HTML = os.path.join(HERE, "probe_dashboard.html")
RATE_WINDOW_SECONDS = 120  # throughput is measured over the last N seconds


def _work_plan() -> dict:
    """Reconstruct the probe's exact (concept, qidx) work list, grouped."""
    axes = P.load_axes()
    refs: list[tuple[str, str, int]] = []  # (axis, concept_text, qidx)
    for ax in P.TESTED_AXES:
        for value in axes[ax]:
            for q in range(len(P.QUESTIONS)):
                refs.append((ax, value, q))
    draws = P.build_test_draws(axes)
    draw_items: list[tuple[str, str, int]] = []  # (tested_axis, concept_text, qidx)
    for d in draws:
        for q in range(len(P.QUESTIONS)):
            draw_items.append((d["tested_axis"], d["concept_text"], q))
    return {"axes": axes, "refs": refs, "draws": draw_items, "draw_specs": draws}


def compute_status() -> dict:
    plan = _work_plan()
    axes = plan["axes"]
    now = time.time()

    # Per-axis reference progress.
    per_axis = []
    refs_done_total = 0
    for ax in P.TESTED_AXES:
        n_vals = len(axes[ax])
        total = n_vals * len(P.QUESTIONS)
        done = sum(1 for value in axes[ax] for q in range(len(P.QUESTIONS))
                   if os.path.exists(P._cache_path(value, q)))
        refs_done_total += done
        per_axis.append({"axis": ax, "values": n_vals, "done": done, "total": total})

    refs_total = len(plan["refs"])
    draws_total = len(plan["draws"])
    draws_done = sum(1 for _, concept, q in plan["draws"] if os.path.exists(P._cache_path(concept, q)))

    total = refs_total + draws_total
    done = refs_done_total + draws_done

    # Throughput + ETA from cache-file mtimes in the recent window.
    recent_count = 0
    newest_files = []
    if os.path.isdir(P.CACHE_DIR):
        entries = []
        for name in os.listdir(P.CACHE_DIR):
            if not name.endswith(".json"):
                continue
            path = os.path.join(P.CACHE_DIR, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            entries.append((mtime, path))
            if now - mtime <= RATE_WINDOW_SECONDS:
                recent_count += 1
        entries.sort(reverse=True)
        newest_files = entries[:12]

    rate_per_min = recent_count / (RATE_WINDOW_SECONDS / 60.0)
    pending = total - done
    eta_seconds = (pending / rate_per_min * 60.0) if rate_per_min > 0 else None

    # Recent completions (read the newest cache files for their concept text).
    recent = []
    for mtime, path in newest_files:
        try:
            rec = json.load(open(path))
        except (OSError, json.JSONDecodeError):
            continue
        recent.append({
            "concept": rec.get("concept", "?"),
            "qidx": rec.get("qidx"),
            "answer_preview": (rec.get("answer", "") or "")[:140],
            "age_seconds": round(now - mtime, 1),
        })

    phase = "references" if refs_done_total < refs_total else "test draws"

    return {
        "now": now,
        "total": total, "done": done, "pending": pending,
        "pct": round(100.0 * done / total, 1) if total else 0.0,
        "refs": {"done": refs_done_total, "total": refs_total},
        "draws": {"done": draws_done, "total": draws_total},
        "per_axis": per_axis,
        "rate_per_min": round(rate_per_min, 1),
        "recent_count": recent_count,
        "rate_window_seconds": RATE_WINDOW_SECONDS,
        "eta_seconds": round(eta_seconds) if eta_seconds is not None else None,
        "phase": phase,
        "axes_count": len(P.TESTED_AXES),
        "questions": len(P.QUESTIONS),
        "worker_url": P.wc.DEFAULT_URL,
        "recent": recent,
    }


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # quiet
        pass

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/index.html", "/dashboard"):
            self._send_file(DASHBOARD_HTML, "text/html")
        elif self.path.startswith("/status"):
            self._send_json(compute_status())
        else:
            self.send_error(404)

    def _send_file(self, path: str, ctype: str):
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

    def _send_json(self, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"Probe dashboard: http://localhost:{PORT}  (Ctrl-C to stop)", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
