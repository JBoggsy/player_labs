# Nim 2.2.4, linux/amd64 compiler image. Only the extension enters the runtime image.
FROM nimlang/nim@sha256:f632c76b88ad90f2fb73ea2b01c0e567fa05fbaa5c2d6aea2dff24cbdb7f4b97 AS native
ADD --checksum=sha256:8bfd634a0b47a2f02ba7c57cb723250c2e2ff21171054f47faee321974d4772e https://codeload.github.com/yglukhov/nimpy/tar.gz/b07fc2c6f09fadb0ae224ce5bf66361ec3fe12e3 /build/nimpy.tar.gz
WORKDIR /build
RUN tar -xzf nimpy.tar.gz
COPY adjudicator_native.nim /build/
RUN nim c -d:release --app:lib --threads:on --path:/build/nimpy-b07fc2c6f09fadb0ae224ce5bf66361ec3fe12e3 --out:/build/adjudicator_native.so adjudicator_native.nim

# Bundled webDiplomacy 0.7.7 player image, with the launcher pinned by digest.
FROM public.ecr.aws/q5f4m8t9/cogames@sha256:ee04a88a155b95f45b04029fa2dab586fa866bec82853efec673dbfb2f1de4ac
# Package fallback adjudicator (AGPL-3.0).
RUN uv pip install --python /opt/.venv/bin/python --no-cache diplomacy==1.1.2
# Press player's agent harness (talks only to the Coworld LLM sidecar).
RUN uv pip install --python /opt/.venv/bin/python --no-cache "pydantic-ai-slim[openai]==2.54.0"
COPY . /opt/webdip_bot/
COPY --from=native /build/adjudicator_native.so /opt/webdip_bot/adjudicator_native.so
COPY --from=native /build/nimpy-b07fc2c6f09fadb0ae224ce5bf66361ec3fe12e3/LICENSE /opt/webdip_bot/licenses/nimpy.txt
COPY --from=native /opt/nim/copying.txt /opt/webdip_bot/licenses/nim.txt
WORKDIR /opt
# Fail the build if the extension cannot load in the actual Python 3.12 runtime.
RUN /opt/.venv/bin/python -c 'from webdip_bot.fastadj import adjudicate; assert adjudicate([], []) == ([], [])'
ARG POLICY=machiavelli
ENV WEBDIP_POLICY=${POLICY}
CMD ["/opt/.venv/bin/python", "-m", "webdip_bot.bot"]
