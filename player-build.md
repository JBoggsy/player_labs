# Building and uploading a Coworld player

Use [official runtime guidance](https://docs.softmax.com/coworld/build-a-coworld/player-runtimes), [protocol documentation](https://docs.softmax.com/coworld/build-a-player/protocol-and-runtime), and the project-local CLI help. The selected game's manifest and player guide determine which format to build. See the [upload skill](.claude/skills/build-and-upload/SKILL.md).

## Choose the declared runtime

| Contract | `platform-hosted` (default) | `game-hosted` |
| --- | --- | --- |
| Player artifact | `linux/amd64` container image | Game-defined file or packed directory |
| Execution | Platform starts player containers per seat | Game loads/runs the seat files |
| Interface | Game protocol via supplied WebSocket URL | Game-defined file and execution contract |
| Policy environment/secrets | Supported | Not provided |
| Submitted size cap | 5 GiB image | 100 MiB packed bytes |
| Bundled size cap | 512 MiB image | 100 MiB packed bytes |

File policies reject `--run`, `--secret-env`, `--use-bedrock`, and `--bedrock-model`. The staged outer file is named `file`, so do not rely on its original extension. Directory packing rejects symlinks. The game process can read/copy submitted files; it does not receive submitted image bytes. See [upload and evaluate](https://docs.softmax.com/coworld/build-a-player/upload-and-evaluate).

## Container contract

- Build `linux/amd64`, including on Apple Silicon.
- Read **`COWORLD_PLAYER_WS_URL` unchanged**. It includes the assigned slot, token and any game-owned parameters. `COGAMES_ENGINE_WS_URL` is a legacy alias.
- Speak the protocol linked by `game.protocols.player`; there is no universal observation/action format. Follow the game's seat/agent assignment.
- Finish cleanly when the game ends. The episode runner does not restart an exited player container.
- Keep diagnostics on stdout/stderr. For larger traces, the optional `COWORLD_PLAYER_ARTIFACT_UPLOAD_URL` accepts a replaceable ZIP of up to **200 MiB**; local URLs use `file://`, hosted ones use HTTP PUT. Finish uploads before exit. Missing optional telemetry does not itself fail an otherwise successful game.
- Hosted player pods request **250m CPU / 256Mi memory** by default. These are scheduling requests, **not hard resource limits**; inspect the actual runtime contract for the target.

Retrieve artifacts through the [current episode-request endpoints](.claude/skills/coworld-episode-artifacts/references/endpoint-map.md), not old `/jobs/...` routes. Replays/results are game-owned evidence; player logs explain decisions but do not override game outcomes.

## Build and upload

```bash
docker buildx build --platform linux/amd64 --load --tag my-player:local .
uv run coworld upload-policy my-player:local --name my-player \
  --run python --run -m --run my_player.main

# For a game-hosted target instead:
uv run coworld upload-policy --file ./my-player --name my-player
```

Use the lab's actual recipe. The image's baked command can be used when correct; repeated `--run` arguments override it. Record returned policy name/version/UUID, source revision, runtime configuration and intended change. **An identical upload may reuse an existing version.** Upload enters no league and does not establish that the player works.

The lab skips routine pre-upload local gates by preference. Use local runs for focused mechanism/transport debugging or own-policy self-play; use targeted XP for field performance. Explicit league submission is a separate authorized action.

## Secrets and model access

Never bake secrets into images, source or manifests. Container uploads support `--secret-env KEY=VALUE` and optional `--use-bedrock --bedrock-model MODEL`. Keep model choices, per-game budgets and tracing recipes in the game's lab.

For hosted Bedrock, read `AWS_ENDPOINT_URL_BEDROCK_RUNTIME` and send calls through that sidecar; injected placeholder credentials are not direct AWS credentials. `USE_BEDROCK` alone does not establish hosted proxy availability. Game-hosted files have no player secrets or Bedrock upload flags; the game owns model access and seat attribution. Local provider calls use separately supplied credentials and may incur provider charges. See [official Bedrock guidance](https://docs.softmax.com/coworld/build-a-player/bedrock).

Player architecture guidance is in [player engineering](docs/player-engineering.md); game-specific build scripts, protocols and observability belong in the relevant lab.
