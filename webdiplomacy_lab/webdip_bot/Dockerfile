# Bundled webDiplomacy 0.7.7 player image: its ENTRYPOINT is the Coworld launcher, which
# runs CMD as the bot subprocess with WEBDIP_* env vars. Pinned by digest so local and
# hosted runs use the same launcher/players code (coworld_pkg/.../coworld_images.json).
FROM public.ecr.aws/q5f4m8t9/cogames@sha256:ee04a88a155b95f45b04029fa2dab586fa866bec82853efec673dbfb2f1de4ac
COPY __init__.py bot.py config.py dumbbot.py /opt/webdip_bot/
WORKDIR /opt
CMD ["/opt/.venv/bin/python", "-m", "webdip_bot.bot"]
