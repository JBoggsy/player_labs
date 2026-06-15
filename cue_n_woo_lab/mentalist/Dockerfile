# mentalist — Cue-n-Woo player image. Build from this directory:
#   docker build --platform linux/amd64 -t mentalist:dev .
# Contract: read COWORLD_PLAYER_WS_URL, play one slot, exit cleanly
# (../../player-build.md). Nothing secret is baked in; the LLM backend is chosen
# at runtime from the pod env (writer.py): USE_BEDROCK (creds from the pod's
# Bedrock IRSA role, set by `upload-policy --use-bedrock`) OR ANTHROPIC_API_KEY
# (set by `upload-policy --secret-env ANTHROPIC_API_KEY=...`).
FROM python:3.12-slim

# anthropic backs both LLM transports; boto3 supplies the botocore credential
# chain that anthropic's AnthropicBedrock client uses for the Bedrock backend.
RUN pip install --no-cache-dir websockets==15.0.1 boto3==1.42.6 "anthropic>=0.107.1"

ENV PYTHONPATH=/app
WORKDIR /app
COPY . /app/mentalist

CMD ["python", "-m", "mentalist"]
