# stencil player image — Paintbot's first Python Player-SDK policy.
#
# Build context is paintbot_lab/paintbot/stencil (see build_player.sh / the CMD
# below), so the COPYs place the package at /app/paintbot/stencil with a minimal
# /app/paintbot/__init__.py. Runtime deps beyond the players SDK: cramjam (snappy
# decode of the walkability sprite — the online nav source; numpy ships with the
# SDK's base deps). Platform is set by the build invocation
# (buildx --platform=linux/amd64), not here.

FROM python:3.12-slim

ARG PLAYERS_SDK_REF=e8921a6b18484030d8704277e4c52d3aae5c8917

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --upgrade pip \
 && pip install "players[bedrock] @ https://github.com/Metta-AI/coworld-tools/archive/${PLAYERS_SDK_REF}.tar.gz#subdirectory=players" \
    cramjam

COPY paintbot_init.py /app/paintbot/__init__.py
COPY stencil /app/paintbot/stencil

CMD ["python", "-m", "paintbot.stencil"]
