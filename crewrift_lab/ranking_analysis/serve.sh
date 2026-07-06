#!/usr/bin/env bash
# Serve the HTML report over Tailscale (or localhost if not on a tailnet).
#   ./serve.sh [host] [port]
# Defaults: host = this machine's Tailscale IP (falls back to 127.0.0.1), port 8811.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HOST="${1:-$(tailscale ip -4 2>/dev/null | head -1 || true)}"
HOST="${HOST:-127.0.0.1}"
PORT="${2:-8811}"
echo "Serving report at http://${HOST}:${PORT}/report.html"
cd "${HERE}/data"
exec python3 -m http.server "${PORT}" --bind "${HOST}"
