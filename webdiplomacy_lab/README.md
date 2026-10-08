# webdiplomacy_lab

Lab for the `webdiplomacy` Coworld: classic 7-power Diplomacy on the real, unmodified
webDiplomacy server. Two leagues, one episode a day each, ranked by mean score (SC²-share
draws, solo = 1): `webDiplomacy Gunboat` (no-press `classic-gunboat`) and `webDiplomacy`
(full-press `classic-press`).

- Game, player contract, gotchas and evidence formats:
  [`docs/webdiplomacy-gameplay.md`](docs/webdiplomacy-gameplay.md)
- How to work here, instruments and identity hygiene: [`AGENTS.md`](AGENTS.md)
- Players (Kissinger search bot, personalities, the LLM press player): [`webdip_bot/`](webdip_bot/README.md)
- Designs: [Kissinger search policy](docs/designs/kissinger-search-policy-2026-10-08.html),
  [press agent](docs/designs/press-agent-design.md)
- Agent entry point: `uv run python webdiplomacy_lab/tools/wd.py --help`
- Current objective: [`WORKING_CONTEXT.md`](WORKING_CONTEXT.md)
