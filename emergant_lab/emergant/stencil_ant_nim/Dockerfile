# Native Stencil-ant player. The dependency graph is pinned by the exact
# canonical Emerg-ant game revision.

FROM debian:bookworm-slim AS build

ARG NIM_VERSION=2.2.6
ARG NIMBY_VERSION=0.1.26
ARG EMERG_ANT_GAME_REF

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*

RUN case "$(dpkg --print-architecture)" in \
      amd64) nimby_arch=X64 ;; \
      arm64) nimby_arch=ARM64 ;; \
      *) echo "unsupported architecture: $(dpkg --print-architecture)" >&2; exit 1 ;; \
    esac \
 && curl -fsSL -o /usr/local/bin/nimby \
      "https://github.com/treeform/nimby/releases/download/${NIMBY_VERSION}/nimby-Linux-${nimby_arch}" \
 && chmod +x /usr/local/bin/nimby \
 && nimby use "${NIM_VERSION}"

ENV PATH="/root/.nimby/nim/bin:${PATH}"
WORKDIR /workspace/stencil

RUN test -n "${EMERG_ANT_GAME_REF}" \
 && curl -fsSL -o nimby.lock \
      "https://raw.githubusercontent.com/Metta-AI/coworld-emerg-ant/${EMERG_ANT_GAME_REF}/nimby.lock" \
 && nimby sync -g nimby.lock

COPY . .

RUN nim c \
      -d:release \
      -d:useMalloc \
      --opt:speed \
      --passC:-flto \
      --passL:-flto \
      --stackTrace:on \
      --nimcache:/tmp/stencil-nimcache \
      --out:/tmp/stencil-ant \
      stencil.nim \
 && strip /tmp/stencil-ant

FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates libcurl4 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /tmp/stencil-ant /bin/stencil-ant

USER 65532:65532
ENTRYPOINT ["/bin/stencil-ant"]
