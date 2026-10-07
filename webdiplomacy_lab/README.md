# webdiplomacy_lab

Lab for the `webdiplomacy` Coworld: classic 7-power Diplomacy on the real, unmodified
webDiplomacy server. The league plays no-press `classic-gunboat`, one episode a day,
ranked by mean score (SC²-share draws, solo = 1).

- Game, player contract, gotchas and evidence formats:
  [`docs/webdiplomacy-gameplay.md`](docs/webdiplomacy-gameplay.md)
- How to work here, instruments and identity hygiene: [`AGENTS.md`](AGENTS.md)
- Current player (DumbBot port): [`webdip_bot/`](webdip_bot/README.md)
- Agent entry point: `uv run python webdiplomacy_lab/tools/wd.py --help`
- Current objective: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)
