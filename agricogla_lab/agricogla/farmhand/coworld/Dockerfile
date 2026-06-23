# Farmhand player image — in-lab build.
#
# Built via `agricogla_lab/tools/build_player.sh farmhand`, which stages a small
# context (the vendored farmhand package + the lab's agricogla/__init__.py) and
# invokes this Dockerfile. All inputs are public, so the host needs only Docker.
#
# farmhand imports only `players.player_sdk` from the SDK — for the GENERAL
# primitives (run_message_bridge, TraceOutputs). The cogweb bridge is VENDORED in
# the farmhand package (coworld/cogweb_bridge.py) until it lands in the public SDK
# (Metta-AI/players PR), so we install the public SDK at PLAYERS_SDK_REF and put
# the package on PYTHONPATH. No behavior/experiment env is baked here — params are
# set at upload time via AGRICOGLA_PARAMS so the image stays reproducible.

# Platform is set by the build invocation (buildx --platform=linux/amd64), not here.
FROM python:3.12-slim

ARG PLAYERS_SDK_REF=main

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Shared SDK (brings websockets/pydantic/numpy — the general primitives the
# vendored cogweb bridge needs). Installed from the public players repo via its
# GitHub tarball at the pinned ref (no git/checkout needed in the build).
RUN pip install --upgrade pip \
 && pip install "players @ https://github.com/Metta-AI/players/archive/${PLAYERS_SDK_REF}.tar.gz"

# Stage layout (built by build_player.sh): /app/agricogla/{__init__.py,farmhand/...}
COPY agricogla_init.py /app/agricogla/__init__.py
COPY farmhand /app/agricogla/farmhand

# Read COWORLD_PLAYER_WS_URL, play one slot, exit cleanly (../../player-build.md).
CMD ["python", "-m", "agricogla.farmhand"]
