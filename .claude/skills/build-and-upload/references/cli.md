# Upload CLI reference

```bash
uv run coworld upload-policy --help
uv run python .claude/skills/build-and-upload/scripts/versions.py --name POLICY
```

`upload-policy [IMAGE]` accepts `--file PATH` instead of an image for a game-hosted policy. `--name` chooses the policy, repeated `--run` provides container command arguments, `--tag KEY=VALUE` adds private bookkeeping, and `--secret-env KEY=VALUE` provides runtime secrets. `--use-bedrock` and `--bedrock-model` are optional model access settings; verify whether the game/player actually consumes them.

An upload registers a version. Submission is a separate operation. Use [the skill](../SKILL.md) and the selected game's build guide for the exact artifact recipe.
