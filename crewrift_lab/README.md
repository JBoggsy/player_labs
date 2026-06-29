# crewrift_lab

The **Crewrift** corner of [player_labs](../README.md) — where we build, evaluate, and
improve player policies for Crewrift, a Coworld social-deduction game (*Among Us*–style:
crewmates do tasks and vote out imposters; imposters kill, vent, and blend in).

This README orients newcomers (human or agent). Two pointers do most of the work:

- **[`AGENTS.md`](AGENTS.md)** — the operating model *for this lab*: the improvement
  loop in Crewrift terms, the player-policy index, and the lab's practices. Read it to
  *work* here.
- **[`../README.md`](../README.md)** — lab-wide setup (`uv sync` / Observatory auth)
  and the ground rules. Everything here is public, so there are **no extra
  credentials** — building players (Python or Nim) and the replay reader need only
  Docker; see [`docs/designs/building_players.md`](docs/designs/building_players.md).

## The game

Crewrift speaks the binary **Sprite-v1** protocol — the engine streams a labeled scene
and the player emits gamepad input; there is **no semantic "do task / vote" API**, so a
player decodes the scene into game state itself. The full, gameplay-perspective guide
(rules, roles, scoring, strategy) is **[`docs/crewrift-gameplay.md`](docs/crewrift-gameplay.md)**
— read that to understand the game without leaving the repo. Authoritative engine
source lives in the `Metta-AI/coworld-crewrift` repo.

## The player policies

Three Crewrift policies are vendored here as drift-able forks under
[`crewrift/`](crewrift/) (full per-policy summary in [`AGENTS.md`](AGENTS.md#player-policies)):

- **crewborg** *(Python)* — the main policy under optimization; a full Player-SDK agent
  (perception → belief/suspicion → strategy → action). It imports the shared
  `players.player_sdk` from the **pinned public players repo** (`pyproject.toml`; no
  local checkout — see [`../README.md`](../README.md)), so the SDK stays fixed even as
  the fork drifts. Its internals: `crewrift/crewborg/design.md`.
- **notsus** *(Nim)* — the minimal reference baseline / comparison opponent.
- **suspectra** *(Nim + LLM)* — notsus plus a bounded meeting-LLM.

## Docs

- **[`docs/crewrift-gameplay.md`](docs/crewrift-gameplay.md)** — the game, from a
  gameplay perspective (start here for a mental model).
- **[`docs/crewrift-protocol.md`](docs/crewrift-protocol.md)** — what any Crewrift player
  must do over the wire (the Sprite-v1 I/O contract).
- **[`docs/crewrift-replays.md`](docs/crewrift-replays.md)** — reading a finished game
  (the `expand_replay` timeline + a policy's logs).
- **[`docs/designs/building_players.md`](docs/designs/building_players.md)** — building
  player images in-lab.

## Quickstart

```sh
# Build a player image (linux/amd64) — just Docker, no credentials.
tools/build_player.sh crewborg            # or: notsus | suspectra

# Build the version-matched replay reader (host-native), then read a replay.
tools/build_expand_replay.sh
tools/bin/expand_replay <replay.json>

# Analyze a batch of episodes into a strengths/weaknesses report:
#   1) pull them with the coworld-episode-artifacts skill, then
#   2) run the crewrift-survey skill:
.claude/skills/crewrift-survey/scripts/survey.py <episodes_dir> --out /tmp/survey.html
#   (survey reads results.json + episode.json — instant; open the HTML it writes.
#    For cross-episode behavioural data, build a crewrift-event-warehouse instead.)
```

The full evaluate → report → improve → submit cycle, and which skill drives each step,
is in [`AGENTS.md`](AGENTS.md).
</content>
