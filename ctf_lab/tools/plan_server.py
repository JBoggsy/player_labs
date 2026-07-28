"""Live co-general server: static ctf_lab/ hosting + battle-plan save/sync.

Replaces the bare `python3 -m http.server` for the plan editor. Adds:

  POST /battle_plans/<name>.json   — save a plan (the editor's Save button);
                                     validated as JSON, written atomically.
  GET  /battle_plans/<name>.json   — served with a strong ETag (content hash),
                                     so the editor can poll cheaply and reload
                                     when the OTHER general edits the file.

Both directions of the live loop ride ordinary file I/O: the human saves from
the browser -> the file changes -> the agent reads it; the agent edits the
file (or commits) -> the editor's 2s poll sees a new ETag -> reloads (unless
the human has unsaved local edits — then it warns instead of clobbering).

Usage:
    uv run python ctf_lab/tools/plan_server.py [--port 8792]
    # then open http://localhost:8792/tools/plan_editor.html
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
PLAN_RE = re.compile(r"^/battle_plans/([a-zA-Z0-9_\-]+)\.json$")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(LAB), **kwargs)

    def log_message(self, fmt, *args):  # quiet: only saves are interesting
        if self.command == "POST":
            super().log_message(fmt, *args)

    def end_headers(self):
        # ETag on plan GETs so the editor can poll with If-None-Match.
        if self.command in ("GET", "HEAD"):
            m = PLAN_RE.match(self.path.split("?")[0])
            if m:
                p = LAB / "battle_plans" / f"{m.group(1)}.json"
                if p.exists():
                    tag = hashlib.sha1(p.read_bytes()).hexdigest()[:16]
                    self.send_header("ETag", f'"{tag}"')
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_POST(self):
        m = PLAN_RE.match(self.path.split("?")[0])
        if not m:
            self.send_error(404, "POST only accepts /battle_plans/<name>.json")
            return
        name = m.group(1)
        length = int(self.headers.get("Content-Length", 0))
        if length > 2_000_000:
            self.send_error(413)
            return
        raw = self.rfile.read(length)
        try:
            doc = json.loads(raw)
        except ValueError as exc:
            self.send_error(400, f"invalid JSON: {exc}")
            return
        dest = LAB / "battle_plans" / f"{name}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps(doc, indent=2) + "\n"
        with tempfile.NamedTemporaryFile("w", dir=dest.parent, delete=False) as tmp:
            tmp.write(body)
        Path(tmp.name).replace(dest)
        tag = hashlib.sha1(body.encode()).hexdigest()[:16]
        payload = json.dumps({"ok": True, "etag": tag}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8792)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"co-general server: http://localhost:{args.port}/tools/plan_editor.html")
    srv.serve_forever()


if __name__ == "__main__":
    main()
