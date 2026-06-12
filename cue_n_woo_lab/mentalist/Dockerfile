# mentalist — Cue-n-Woo player image. Build from this directory:
#   docker build --platform linux/amd64 -t mentalist:dev .
# Contract: read COWORLD_PLAYER_WS_URL, play one slot, exit cleanly
# (../../player-build.md). Bedrock creds come from the pod role at runtime
# (--use-bedrock at upload); nothing secret is baked in.
FROM python:3.12-slim

RUN pip install --no-cache-dir websockets==15.0.1 boto3==1.42.6

ENV PYTHONPATH=/app
WORKDIR /app
COPY . /app/mentalist

CMD ["python", "-m", "mentalist"]
