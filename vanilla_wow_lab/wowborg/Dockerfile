# Wowborg player image.
#
# Build context is vanilla_wow_lab/wowborg, so `COPY . /app/wowborg` copies
# the top-level `wowborg` package. Wowborg needs no extra runtime dependencies
# beyond players[bedrock] and its websocket dependencies.

FROM python:3.12-slim

ARG PLAYERS_SDK_REF=e8921a6b18484030d8704277e4c52d3aae5c8917

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --upgrade pip \
 && pip install "players[bedrock] @ https://github.com/Metta-AI/coworld-tools/archive/${PLAYERS_SDK_REF}.tar.gz#subdirectory=players"

COPY . /app/wowborg

CMD ["python", "-m", "wowborg"]
