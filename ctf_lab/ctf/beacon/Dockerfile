# beacon player image — CTF's first Python Player-SDK policy.
#
# Build context is ctf_lab/ctf/beacon (see build_player.sh / the CMD below), so the
# COPYs place the package at /app/ctf/beacon with a minimal /app/ctf/__init__.py.
# beacon needs no runtime deps beyond the players SDK (numpy for the baked nav grid
# ships with the SDK's base deps). Platform is set by the build invocation
# (buildx --platform=linux/amd64), not here.

FROM python:3.12-slim

ARG PLAYERS_SDK_REF=e8921a6b18484030d8704277e4c52d3aae5c8917

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --upgrade pip \
 && pip install "players[bedrock] @ https://github.com/Metta-AI/coworld-tools/archive/${PLAYERS_SDK_REF}.tar.gz#subdirectory=players"

COPY ctf_init.py /app/ctf/__init__.py
COPY beacon /app/ctf/beacon

CMD ["python", "-m", "ctf.beacon"]
