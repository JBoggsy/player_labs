# Suspectra player image — in-lab build (Plan A).
#
# Built via `crewrift_lab/tools/build_player.sh suspectra`, which sets the build
# context to this directory and passes the pinned CREWRIFT_REF.
#
# Suspectra is notsus (Nim) plus a bounded Bedrock/Anthropic meeting LLM driven by
# a Python helper. Like notsus, the Nim binary compiles against the crewrift game
# modules, so the build clones the game repo at the pinned ref, nimby-syncs, and
# overlays this source at players/suspectra. The runtime stage adds python3 +
# anthropic + boto3 for the meeting helper. Host needs only Docker.

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
# coworld-crewrift and its bitworld dep are PRIVATE Metta-AI repos, so both the
# clone and the nimby sync need a GitHub token. It is supplied as a BuildKit secret
# (tools/build_player.sh passes `--secret id=gh_token,env=GITHUB_PAT`) and is NEVER
# baked into a layer: the credential helper reads it from the mounted secret file at
# git-invocation time, so only the path — not the token — is stored in git config,
# and the secret mount disappears when this RUN finishes. Clone + sync share one RUN
# so the token is available for both.
RUN --mount=type=secret,id=gh_token \
    git config --global credential.helper \
      '!f(){ echo username=x-access-token; echo "password=$(cat /run/secrets/gh_token)"; };f' \
 && git clone https://github.com/Metta-AI/coworld-crewrift.git . \
 && git checkout "$CREWRIFT_REF" \
 && nimby --global sync nimby.lock

# Overlay the lab's vendored suspectra source, then build the Nim binary.
COPY . ./players/suspectra
RUN nim c \
      -d:release \
      -d:botHeadless \
      -d:useMalloc \
      --opt:speed \
      --stackTrace:on \
      --nimcache:/tmp/suspectra-nimcache \
      --out:suspectra \
      players/suspectra/suspectra.nim

FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates coreutils libcurl4 python3 python3-pip \
 && rm -rf /var/lib/apt/lists/*

# Meeting-LLM helper deps. boto3 backs the Anthropic SDK's Bedrock client used when
# the policy is uploaded with --use-bedrock.
RUN python3 -m pip install --break-system-packages --no-cache-dir \
      "anthropic>=0.40.0" \
      "boto3>=1.34.0"

WORKDIR /workspace/crewrift
COPY --from=build /workspace/crewrift/suspectra /bin/suspectra
COPY llm_meeting.py /srv/suspectra/llm_meeting.py
COPY memory /srv/suspectra/memory

# Operational config for the meeting LLM (file locations + bounded call budget).
# These wire the helper to its prompt/memory files and cap latency; they are the
# policy's identity (suspectra = notsus + LLM meetings), not an experiment knob.
ENV SUSPECTRA_LLM_HELPER=/srv/suspectra/llm_meeting.py \
    SUSPECTRA_LLM_SYSTEM_PROMPT_PATH=/srv/suspectra/memory/system.md \
    SUSPECTRA_LLM_MEETINGS=1 \
    SUSPECTRA_LLM_PROCESS_TIMEOUT_SECONDS=6 \
    SUSPECTRA_LLM_TIMEOUT_SECONDS=5 \
    SUSPECTRA_LLM_MAX_TOKENS=160 \
    SUSPECTRA_LLM_TEMPERATURE=0 \
    SUSPECTRA_LLM_MIN_SUBMIT_CONFIDENCE=0.75 \
    AWS_REGION=us-west-2

# Reads COWORLD_PLAYER_WS_URL, connects, plays one slot, exits when the game ends.
CMD ["/bin/suspectra"]
