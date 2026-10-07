# Bundled webDiplomacy 0.7.7 player image: its ENTRYPOINT is the Coworld launcher, which
# runs CMD as the bot subprocess with WEBDIP_* env vars. Pinned by digest so local and
# hosted runs use the same launcher/players code (coworld_pkg/.../coworld_images.json).
FROM public.ecr.aws/q5f4m8t9/cogames@sha256:ee04a88a155b95f45b04029fa2dab586fa866bec82853efec673dbfb2f1de4ac
# `diplomacy` (AGPL-3.0, same license as the coworld): local adjudicator for lookahead.
RUN uv pip install --python /opt/.venv/bin/python --no-cache diplomacy==1.1.2
COPY . /opt/webdip_bot/
WORKDIR /opt
# Which personality this image plays (personalities.py); one image per uploaded policy.
ARG POLICY=machiavelli
ENV WEBDIP_POLICY=${POLICY}
CMD ["/opt/.venv/bin/python", "-m", "webdip_bot.bot"]
