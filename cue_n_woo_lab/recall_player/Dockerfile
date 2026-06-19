# recall_player — Cue-n-Woo player image (NO LLM). Build from this directory:
#   docker build --platform linux/amd64 -t recall:dev .
# Contract: read COWORLD_PLAYER_WS_URL, play one slot, exit cleanly (../../player-build.md).
# Fully programmatic: no LLM backend, no AWS/Anthropic creds, nothing secret — only a
# WebSocket client. Strategy = planted digit-recall (see config.py / README.md).
FROM python:3.12-slim

RUN pip install --no-cache-dir websockets==15.0.1

ENV PYTHONPATH=/app
WORKDIR /app
COPY . /app/recall_player

CMD ["python", "-m", "recall_player"]
