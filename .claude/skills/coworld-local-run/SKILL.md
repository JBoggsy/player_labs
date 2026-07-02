---
name: coworld-local-run
description: "Use to run your own built player policy in a LOCAL Coworld episode and watch it — a DEBUGGING tool for when a hosted eval shows the artifact can't connect → play → exit cleanly and you need to watch it fail. NOT part of the standard loop, NOT a pre-upload gate (upload straight away; the next eval is the test). Triggers: 'debug the player locally', 'run a local game', 'run my policy locally and watch it', 'why won't the build connect', 'open the replay locally'. Game-agnostic; correctness only, NOT a competitive matchup (you can't run other users' policies locally)."
---

# Coworld Local Run (local debugging)

Run your **own** built policy image in a local Coworld episode and watch the result.
This is a **debugging tool, not a gate**: the standard loop uploads straight after a
rebuild and lets the next experience request catch breakage. Reach for a local run only
when a hosted eval shows the artifact **can't connect → play → exit cleanly** and you
need to watch it fail up close. It is correctness/liveness only, **not** a competitive
test (you generally can't run other users' policies locally, so all competitive
judgment comes from experience requests; see `coworld-experience-requests`).

**Announce at start:** "Running the built policy locally to debug it."

## Two footguns this skill guards (read first)

1. **Images must be `linux/amd64`** — the runner hard-fails on arm64. On Apple Silicon,
   build with `docker build --platform linux/amd64 -t <tag> .`
2. **Your policy image is the *positional* argument** to `run-episode`. Omit it and the
   runner **silently runs the manifest's reference player** — your change isn't under
   test even though the run "passes". `--run` alone does *not* swap the player; it only
   sets the argv for a supplied image.

## Workflow

1. **Build crewborg `linux/amd64`** (the cluster + local runner are amd64):

   ```bash
   crewrift_lab/tools/build_player.sh crewborg   # builds players-crewborg:dev
   ```
   (or the **`build-and-upload`** skill.)

2. **Run it** — the helper does download (if needed) → amd64 check → run-episode
   with your image in every slot → a PASS/FAIL verdict + the replay command:

   ```bash
   # run with the Coworld SDK available (a uv env with coworld[auth]) + Docker
   S=.claude/skills/coworld-local-run/scripts/smoke.py
   uv run python "$S" --coworld <cow_id|name> --image players-crewborg:dev
   # multi-token entrypoint, longer timeout, custom out dir:
   uv run python "$S" --coworld cow_... --image players-crewborg:dev \
     --run python --run -m --run crewrift.crewborg.coworld.policy_player --timeout 180
   ```

   **Heads-up — the first run can take several minutes.** `download` pulls the
   game's Docker image (often hundreds of MB) and tags it; that's the slow part. It's
   cached and idempotent, so later runs against the same game are fast. If a user
   is watching, tell them it's pulling the game image and may take a bit — it isn't stuck.

   **The run passes** when it exits 0: the CLI exited cleanly (no game/player container
   crashed), `results.json` validated, and a `replay` was written. The default run uses
   the package's **certification** config, which is deliberately degenerate — **a score
   of 0 there is NOT a failure**; this checks liveness/correctness, not gameplay.

3. **Watch it** — the script prints the exact command; or open the viewer / watch live:

   ```bash
   uv run coworld replay <manifest> <out>/replay        # headless result → browser viewer
   uv run coworld play   <manifest> <your-tag>:dev      # watch a fresh local game live
   ```

## Doing it by hand (what the script runs)

```bash
uv run coworld download <cow_id|name>          # -> ./coworld/<cow_id>/coworld_manifest.json (+ pulls/tags game images)
uv run coworld run-episode ./coworld/<cow_id>/coworld_manifest.json \
    <your-tag>:dev --output-dir /tmp/smoke --timeout-seconds 120
uv run coworld replay ./coworld/<cow_id>/coworld_manifest.json /tmp/smoke/replay
```

`run-episode` writes `results.json`, `replay` (no extension), `config.json`, and
`logs/{game.stdout,game.stderr,policy_agent_<slot>}.log` to the output dir. The
positional image is reused for **all** slots (self-play); pass **one image per slot** to
mix players (there is no single-slot override — reference players are used only when you
supply *zero* images).

## Notes

- **`run` vs `play`:** `run-episode` is headless and writes the artifacts (the usual
  debugging case); `play` opens the live browser viewer and keeps the session alive —
  use it to watch a game in real time.
- **Real (non-degenerate) variant:** `run-episode` now takes **`--variant <id>`** (added
  since 0.1.20), so you can run a fuller game headlessly — or `coworld play <manifest>
  <image> --variant <id>` to watch it. For competitive numbers, use experience requests.
- **Debug the LLM path locally** with `--use-bedrock` on a by-hand `run-episode` (the
  helper doesn't pass it): it uses **your own** AWS creds and there is **no sidecar
  locally**, so it proves the code can call Bedrock but **not** that the hosted upload is
  correct — that contract is the
  [Bedrock section of `coworld-platform.md`](../../../crewrift_lab/docs/coworld-platform.md#bedrock--in-pod-llm).
- **Auth/network:** `download` needs `softmax login` (for a name) + Docker + network to
  pull/tag the game image; once the game image and your `:dev` image are local, the run
  is offline. `cow_…` ids are stable; **names resolve to whatever is canonical now**.
- The player-image contract + the runner lifecycle live in
  [`coworld-platform.md`](../../../crewrift_lab/docs/coworld-platform.md). Full CLI reference
  (exact flags, outputs, every gotcha): [`references/cli.md`](references/cli.md).
- CLI **re-verified 2026-06-27** (`run-episode` gained `--variant`/`-n`/`--use-bedrock`
  since the original 0.1.20 pass — see `references/cli.md`).
