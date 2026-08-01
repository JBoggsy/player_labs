# Wowborg v5: a Python policy over the game's canonical hosted WS /env.

ARG WOWBORG_ENVIRONMENT_IMAGE=scratch
FROM ${WOWBORG_ENVIRONMENT_IMAGE} AS environment_contract

FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/opt/wowborg:/opt/vanilla-wow

RUN pip install --no-cache-dir \
    "gymnasium>=1.3,<2" \
    "msgpack>=1.1" \
    "pydantic>=2.11" \
    "websockets>=15"

# Copy the exact Python environment and navmesh SDK shipped by the deployed game
# image. The policy image contains no WoW client: the game owns that process.
COPY --from=environment_contract \
    /usr/local/lib/python3.11/dist-packages/environment \
    /opt/vanilla-wow/environment
COPY --from=environment_contract \
    /usr/local/lib/python3.11/dist-packages/player/__init__.py \
    /opt/vanilla-wow/player/__init__.py
COPY --from=environment_contract \
    /usr/local/lib/python3.11/dist-packages/player/sdk \
    /opt/vanilla-wow/player/sdk
COPY . /opt/wowborg/wowborg

ARG WOWBORG_POLICY=world_race
ENV WOWBORG_POLICY=${WOWBORG_POLICY}

ARG WOWBORG_STATIONS=""
ENV WOWBORG_STATIONS=${WOWBORG_STATIONS}

CMD ["python3", "-m", "wowborg"]
