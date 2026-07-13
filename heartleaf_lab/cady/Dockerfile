# Cady player image.
#
# Build context is heartleaf_lab/cady, so `COPY . /app/cady` copies the top-level
# `cady` package. Cady needs no extra runtime dependencies beyond players[bedrock].
# Platform is set by the build invocation (buildx --platform=linux/amd64), not here.

FROM python:3.12-slim

ARG PLAYERS_SDK_REF=e8921a6b18484030d8704277e4c52d3aae5c8917

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --upgrade pip \
 && pip install "players[bedrock] @ https://github.com/Metta-AI/coworld-tools/archive/${PLAYERS_SDK_REF}.tar.gz#subdirectory=players"

COPY . /app/cady

CMD ["python", "-m", "cady"]
