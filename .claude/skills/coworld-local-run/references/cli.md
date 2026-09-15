# Local execution reference

Checked with project-local `coworld 0.1.47` help and the official [packaging guide](https://docs.softmax.com/coworld/build-a-player/package-and-verify), [runtime guide](https://docs.softmax.com/coworld/build-a-coworld/player-runtimes), and [replay guide](https://docs.softmax.com/coworld/advanced/replays), 2026-09-14. No local games were run in the platform audit.

Use local runs for debugging, mechanism/parity evidence and own-policy self-play. The lab's no-routine-smoke-gate rule is a preference, not a platform limitation.

## Download

`coworld download REF --output-dir DIR [--refresh]` resolves a Coworld ID or canonical name and downloads its package/images. Names can resolve to newer versions; pin the episode's ID for reproduction. Download can pull/tag Docker images, so it is not merely a metadata query. Use the API manifest route when only inspecting configuration.

## Run an episode

```bash
uv run coworld run-episode path/to/coworld_manifest.json IMAGE \
  --run python --run -m --run MODULE --episodes N --variant VARIANT \
  --output-dir ./runs/local
```

For container policies, one supplied image is reused across slots; otherwise supply the required roster. Without overrides, bundled fixture players run, not your unlisted player. Repeated `--run` supplies argv. Inspect `--help` for current options rather than copying old monorepo CLI paths.

For game-hosted policies, supply one file/directory per seat; a single file is **not** duplicated across seats. Files use the game's loader contract and no player environment. Container `--run`, secrets, local Bedrock flags and `coworld play` do not apply.

Without a chosen variant, local execution normally uses the certification fixture; this is not necessarily the hosted competitive config. Multiple local episodes increment an existing integer game seed; do not assume that is how hosted XP chooses seeds. Inspect each run's config/results/logs and optional replay/artifacts. A process exit code alone does not prove useful gameplay or complete optional telemetry.

## Play and replay

`coworld play MANIFEST … --variant VARIANT` supports interactive platform-hosted play. `coworld replay MANIFEST REPLAY` uses the matching game container's viewer when the game does not declare a static viewer. `coworld replay-open ereq_… [--hosted]` opens a stored episode through its viewer; hosted session creation may allocate resources and is a separate action from reading existing replay bytes.

Replay format and compression are game-owned; neither local nor hosted execution implies a universal JSON/zlib format. Use the episode's game version and declared viewer.

## Model access

Local `--use-bedrock` with `--aws-profile`/`--aws-region` uses supplied local credentials. It does not verify the hosted sidecar or upload settings. Follow the workspace's credential rules, never assume ambient credentials are authorized, and account for external provider charges. See [player build](../../../../player-build.md).
