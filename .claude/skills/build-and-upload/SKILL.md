---
name: build-and-upload
description: Build or package a Coworld player and upload a new version for evaluation. Does not submit to a league.
---

# Build and upload a player version

Within an authorized policy-improvement task, package the selected player and upload a new version immediately. The next hosted evaluation measures it; no routine pre-upload smoke gate. League submission is separate and requires explicit permission.

## Select the game's artifact contract

Read the game's build guide and [shared artifact contract](../../../player-build.md). The current CLI supports both:

- **Container policy:** use the lab's build script, targeting `linux/amd64`. Pass the actual player entrypoint with repeated `--run` arguments when the image contains multiple roles.
- **Game-hosted policy:** package the file/directory format accepted by that game and use `--file`. A prompt bundle is not universally interchangeable with a container.

```bash
uv run coworld upload-policy IMAGE --name POLICY --run python --run -m --run MODULE
uv run coworld upload-policy --file POLICY_PATH --name POLICY
```

These are templates: replace uppercase placeholders from the game guide. Check `uv run coworld upload-policy --help` for current flags. Enable only the game's intended runtime, model and telemetry options; there is no shared LLM environment-variable recipe. [Crewrift's recipe](../../../crewrift_lab/user_preferences.md) is game-specific.

## Record and evaluate

Record policy name, sequential version and immutable version UUID, source commit/diff, build/runtime configuration, intended change and evaluation links in the player's version log. Avoid storing secrets in logs. Resolve uploaded versions with:

```bash
uv run python .claude/skills/build-and-upload/scripts/versions.py --name POLICY
```

Create the targeted [experience request](../coworld-experience-requests/SKILL.md) and stream artifacts. If the artifact cannot play, use [local debugging](../coworld-local-run/SKILL.md). Uploading alone demonstrates neither operation nor gameplay improvement. See [policy lifecycle](../coworld-policy-lifecycle/SKILL.md) for the separately authorized submission step.
