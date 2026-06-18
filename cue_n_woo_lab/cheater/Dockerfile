# cheater — Cue-n-Woo player image. Build from this directory:
#   docker build --platform linux/amd64 -t cheater:dev .
# Contract: read COWORLD_PLAYER_WS_URL, play one slot, exit cleanly
# (../../player-build.md). cheater is a deterministic baseline: no LLM backend,
# no AWS/Anthropic credentials, nothing secret. It needs only a WebSocket client.
FROM python:3.12-slim

RUN pip install --no-cache-dir websockets==15.0.1

ENV PYTHONPATH=/app
WORKDIR /app
COPY . /app/cheater

# Which authored-question set to use (config.QUESTION_SETS). Baked at build time
# so each variant image is self-contained for parallel live XP testing.
ARG CHEATER_QSET=generic
ENV CHEATER_QSET=${CHEATER_QSET}

CMD ["python", "-m", "cheater"]
