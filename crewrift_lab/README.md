# crewrift_lab

This README orients newcomers (human or agent). Two pointers do most of the work:

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
