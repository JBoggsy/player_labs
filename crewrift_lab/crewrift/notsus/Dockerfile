# notsus player image — in-lab build (Plan A).
#
# Built via `crewrift_lab/tools/build_player.sh notsus`, which sets the build
# context to this directory and passes the pinned CREWRIFT_REF.
#
# notsus is Nim and compiles against the crewrift game's modules. The lab vendors
# only the player source, so the build clones the game repo at the pinned ref,
# nimby-syncs its deps, overlays this source at players/notsus, and compiles. The
# result is a self-contained linux/amd64 binary; the host needs only Docker.

FROM debian:bookworm-slim AS build
ARG CREWRIFT_REF=d9f6b30

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*

# nimby 0.1.26 -> Nim 2.2.4 (matches the game repo's toolchain).
RUN arch="$(dpkg --print-architecture)"; \
    if [ "$arch" = "amd64" ]; then \
      url="https://github.com/treeform/nimby/releases/download/0.1.26/nimby-Linux-X64"; \
    elif [ "$arch" = "arm64" ]; then \
      url="https://github.com/treeform/nimby/releases/download/0.1.26/nimby-Linux-ARM64"; \
    else echo "unsupported arch: $arch" && exit 1; fi \
 && curl -fsSL -o /usr/local/bin/nimby "$url" \
 && chmod +x /usr/local/bin/nimby \
 && nimby use 2.2.4
ENV PATH="/root/.nimby/nim/bin:$PATH"

WORKDIR /workspace/crewrift
# coworld-crewrift and its bitworld dep are public, so the clone + nimby sync need no
# credentials. (Pinning to CREWRIFT_REF — not the default branch — keeps the build
# matched to the game version the league runs; see docs/crewrift-replays.md §B.)
RUN git clone https://github.com/Metta-AI/coworld-crewrift.git . \
 && git checkout "$CREWRIFT_REF" \
 && nimby --global sync nimby.lock

# Overlay the lab's vendored notsus source over the in-tree player dir, then build.
COPY . ./players/notsus
RUN nim c \
      -d:release \
      -d:botHeadless \
      -d:useMalloc \
      --opt:speed \
      --stackTrace:on \
      --nimcache:/tmp/notsus-nimcache \
      --out:notsus \
      players/notsus/notsus.nim

FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates libcurl4 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace/crewrift
COPY --from=build /workspace/crewrift/notsus /bin/notsus
# Reads COWORLD_PLAYER_WS_URL, connects, plays one slot, exits when the game ends.
CMD ["/bin/notsus"]
