# Crewborg player image — in-lab build (Plan A).
#
# Built via `crewrift_lab/tools/build_player.sh crewborg`, which stages a small
# build context and invokes this Dockerfile. The context contains:
#   crewborg/        the vendored fork (crewrift_lab/crewrift/crewborg)
#   crewrift_init.py the lab's crewrift/__init__.py
#
# Unlike upstream, this fork is the top-level `crewrift.crewborg` package and
# imports only `players.player_sdk` from the SDK. So we install the SDK straight
# from the public Metta-AI/players repo (pinned via PLAYERS_SDK_REF) and put the
# fork on PYTHONPATH — we deliberately do NOT install the lab package itself (that
# would drag in lab tooling deps like coworld[auth]), and we bake NO
# behavior/experiment env (e.g. CREWBORG_BE_DUMB) — those are set at upload time so
# the image stays behavior-neutral and reproducible.

# Platform is set by the build invocation (buildx --platform=linux/amd64), not here.
FROM python:3.12-slim

ARG PLAYERS_SDK_REF=main

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Shared SDK + crewborg's runtime deps (numpy/pydantic/websockets/cramjam are
# players' base deps). Installed from the public players repo via its GitHub source
# tarball at the pinned ref (no git or local checkout needed in the build).
# `[bedrock]` adds boto3 so the meeting LLM can route through AWS Bedrock when the
# policy is uploaded with `--use-bedrock`; inert otherwise.
RUN pip install --upgrade pip \
 && pip install "players[bedrock] @ https://github.com/Metta-AI/players/archive/${PLAYERS_SDK_REF}.tar.gz"

# Put the vendored fork on the path as `crewrift.crewborg`.
COPY crewrift_init.py /app/crewrift/__init__.py
COPY crewborg /app/crewrift/crewborg

# Reads COWORLD_PLAYER_WS_URL (canonical) / COGAMES_ENGINE_WS_URL (alias), connects,
# plays one slot, and exits when the episode ends.
CMD ["python", "-m", "crewrift.crewborg.coworld.policy_player"]
