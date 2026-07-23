# Wowborg v2 player image — our policy layered on the DEPLOYED reference player (the
# Nim shim). Design: docs/designs/wowborg-v2-shim-adoption.md.
#
# The base image (pinned by digest in tools/versions.env, passed as WOWBORG_BASE_IMAGE)
# already contains king_richard, the navmesh helper + Valley-of-Trials mmaps, the
# installed wow_sdk + vanilla_wow_coworld packages, and the CMD
# ["python3", "-m", "vanilla_wow_coworld.player"] WS session wrapper — which we keep.
# We add only the wowborg package and repoint KING_NIMROD_COMMAND at our shim
# supervisor, exactly the injection seam the reference image itself uses for its
# general-grinder policy.
#
# Build via tools/build_player.sh (sources versions.env, forces --platform=linux/amd64).

ARG WOWBORG_BASE_IMAGE
FROM ${WOWBORG_BASE_IMAGE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Prepend /opt/wowborg so `import wowborg` resolves; the shim itself appends
# /opt/coworld-player (the game repo's bots/ package) for king_richard's use.
ENV PYTHONPATH=/opt/wowborg

COPY . /opt/wowborg/wowborg

# The swap point: the base wrapper spawns this command per wow_session.
ENV KING_NIMROD_COMMAND="python3 -m wowborg.shim"
# Active policy for this build (see wowborg/policies/__init__.py). Hosted runs can't
# set per-request env, so the policy ships baked into the image tag we upload.
ARG WOWBORG_POLICY=random_walk
ENV WOWBORG_POLICY=${WOWBORG_POLICY}

# Optional station override for the world_race policy — pure DATA, JSON
# [[name, map_id, x, y, z, expected], ...]. Empty = the in-code catalog.
# This is the one-shot generality seam: new courses ship as data, never code.
ARG WOWBORG_STATIONS=""
ENV WOWBORG_STATIONS=${WOWBORG_STATIONS}

# CMD inherited from the base image: python3 -m vanilla_wow_coworld.player
