# mentalist_v4 — Cue-n-Woo player image (Player SDK based). Build from this dir:
#   docker build --platform linux/amd64 --build-arg PLAYERS_SDK_REF=main -t mentalist-v4:dev .
# Contract: read COWORLD_PLAYER_WS_URL, play one slot, exit cleanly (../../player-build.md).
#
# Unlike v1-v3 (hand-rolled websocket loop), v4 runs on players.player_sdk:
#   - run_message_bridge  (transport + the exit-0-on-unclean-close rule)
#   - TraceOutputs        (telemetry -> the episode artifact zip)
# So the image installs the SDK from the public Metta-AI/players repo (pinned ref),
# mirroring crewborg's image. websockets is an SDK base dep; [bedrock] adds boto3 for
# the (future, scan-gated) fingerprint/writer LLM path. Nothing secret is baked in;
# any LLM backend is chosen at runtime from the pod env.
FROM python:3.12-slim

ARG PLAYERS_SDK_REF=main

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Shared SDK (brings websockets/pydantic/numpy) + boto3 for the Bedrock path (Titan
# embeddings for fingerprinting + the writer). scikit-learn powers the char-TFIDF
# fingerprint fallback that runs when Titan/Bedrock is unavailable, so it must ship.
RUN pip install --upgrade pip \
 && pip install "players[bedrock] @ https://github.com/Metta-AI/players/archive/${PLAYERS_SDK_REF}.tar.gz" \
                "anthropic>=0.107.1" "scikit-learn>=1.5"

# Put the player package on the path as `mentalist_v4`.
COPY . /app/mentalist_v4

# Strategy variant baked at build time (config.STRATEGY_MODE reads MENTALIST_STRATEGY).
# "fingerprint" (default) | "rare" | "flood". Lets the A/B race compare strategies as
# distinct images from ONE codebase. FLOOD_WORD seeds flood mode + the rare-mode fallback.
ARG MENTALIST_STRATEGY=fingerprint
ARG MENTALIST_FLOOD_WORD=phlogiston
ARG MENTALIST_FLOOD_REPEATS=8
ARG MENTALIST_RARE_BASKET=0
ARG MENTALIST_FLOOD_AWARE=0
ARG MENTALIST_MULTI_BASELINE=0
ARG MENTALIST_INJECT_ANSWER="the lighthouse keeper's ledger"
ARG MENTALIST_INJECT_STYLE=opponent_wrong
ENV MENTALIST_STRATEGY=${MENTALIST_STRATEGY} \
    MENTALIST_FLOOD_WORD=${MENTALIST_FLOOD_WORD} \
    MENTALIST_FLOOD_REPEATS=${MENTALIST_FLOOD_REPEATS} \
    MENTALIST_RARE_BASKET=${MENTALIST_RARE_BASKET} \
    MENTALIST_FLOOD_AWARE=${MENTALIST_FLOOD_AWARE} \
    MENTALIST_MULTI_BASELINE=${MENTALIST_MULTI_BASELINE} \
    MENTALIST_INJECT_ANSWER=${MENTALIST_INJECT_ANSWER} \
    MENTALIST_INJECT_STYLE=${MENTALIST_INJECT_STYLE}

CMD ["python", "-m", "mentalist_v4"]
