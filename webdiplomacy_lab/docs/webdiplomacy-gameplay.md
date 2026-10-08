# webDiplomacy: game, protocol and scoring reference

Self-contained reference for building and evaluating webDiplomacy players. Verified
against **webdiplomacy 0.7.7** (deployed source commit
[`e867197`](https://github.com/Metta-AI/coworld-webdiplomacy/tree/e8671977f3f259aa965033719e151dec3d0b9549),
recorded in the downloaded manifest's `source_url`) on 2026-10-06. The source repo
[Metta-AI/coworld-webdiplomacy](https://github.com/Metta-AI/coworld-webdiplomacy)
(AGPL-3.0) is the authority: `README.md`, `docs/write-a-policy.md`,
`docs/protocol.md`, `docs/players.md`, `docs/replay.md`, and `players/`.

## The game

Classic 7-power Diplomacy, run by the **real, unmodified webDiplomacy server**
(kestasjk/webDiplomacy) with its own adjudicator and gamemaster loop. The adapter
never submits actions or advances games itself.

- Powers (webDip `countryID`): 1 England, 2 France, 3 Italy, 4 Germany, 5 Austria,
  6 Turkey, 7 Russia. **Assignment is a seeded random permutation per episode** and
  differs from slot order. Powers differ a lot in strength, so every metric is split
  by power.
- 34 supply centres (SCs); 18 wins outright (solo).
- Orders resolve simultaneously. Phases: `Diplomacy` (movement; viewers label it
  "Movement"), `Retreats`, `Builds`. Turn numbers start at 0: year = `1901 + turn // 2`,
  even turns are Spring, odd turns Autumn. Winter adjustments happen in the `Builds`
  phase of the odd turn.
- **A phase ends early when every seat is Ready.** Bots that mark Ready make a full
  gunboat game take about 40 seconds locally.
- A silent seat gets upstream defaults (hold, disband, skip builds) and does not fail
  the episode.

### Variants

| Variant | Press | Phase minutes (diplomacy / retreat+build) | Year cap |
| --- | --- | --- | --- |
| `classic-gunboat` | none | 1 / 1 | 1910 |
| `classic-press` | public + private | 4 / 1 | 1908 |
| `classic-press-short` | public + private | 3 / 1 | 1904 |
| `classic-live-human` | public + private | 7 / 2 | 1904 |

The year cap ends play as a **draw** at the first observed state after that autumn
(including its retreats). Results record the actual final turn: it can be the cap
year's autumn (turn 19 for 1910) or the next spring (turn 20). The container also ends
play after 5910 s.

### Scoring

- Solo: winner 1, everyone else 0.
- Otherwise (default): each surviving power gets **SC² / Σ SC²** over survivors.
- Cancellation: 1/7 each. Zero-centre fallback: equal shares.
- So a draw rewards being **the largest** power, quadratically. 7 SCs among powers of
  4–5 already earns about 0.25–0.30.

## The leagues

Two platform ladders, each with **one episode per day** (`round_interval_minutes: 1440`),
balanced rotation, one player per user, ranked by **mean score** (`algorithm: score`,
`round_scoring_rule: mean`):

| League | ID | Variant |
| --- | --- | --- |
| `webDiplomacy Gunboat` | `league_428e91e5-ee25-4f9c-be5e-a4fc4f993f17` | `classic-gunboat` (no press) |
| `webDiplomacy` | `league_1bccc63d-cd0a-47d7-92d7-e762797b5f1c` | `classic-press` (public + private press) |

Empty seats are filled from each league's **filler roster**. The lab curates it through
`POST /v2/leagues/{id}/filler-policies`; our account passes the owner/commissioner gate,
and `display_name` hides the uploading player. Read the current roster with `GET` on the
same route (current lists in `WORKING_CONTEXT.md`). Read the live settings with
`uv run coworld leagues <league_id> --json` before relying on these.

## Player contract

A bot is an ordinary webDiplomacy API client. The bundled player image's `ENTRYPOINT`
is the launcher (`players.launcher`). It holds the Coworld WebSocket, archives private
press, and runs the image `CMD` as a child process with:

| Variable | Meaning |
| --- | --- |
| `WEBDIP_URL` | upstream base URL |
| `WEBDIP_API_KEY` | seat Bearer credential (never log it) |
| `WEBDIP_GAME_ID`, `WEBDIP_COUNTRY_ID` | game and our power |
| `WEBDIP_SEED` | `episode_seed * 7 + slot` |

Routes: `$WEBDIP_URL/api.php?route=ROUTE` with `Authorization: Bearer KEY`:

| Route | Use |
| --- | --- |
| `game/playercontext` (GET `gameID`, `orders=1`, `messages=1`) | current turn/phase, our order slots (`orders.orders[].unitID`), messages, refs to public files (`files.game`, `files.variant`, ...) |
| public files | `variant.json`: territories with `borders`/`coastalBorders` (army/fleet flags), `coast` (`No`/`Parent`/`Child`), `coastParentID`, `supply`, `homeCountryID`. `game.json`: `units` (with `id`, `retreating`), `territories` (`ownerCountryID`, `unitID`, `standoff`, `occupiedFromTerrID`) |
| `game/orders` (POST `gameID`, `countryID`, `turn`, raw `phase`, `orders`, `ready`) | saves orders; returns the saved list |
| `game/sendmessage` | press (press variants only; `toCountryID` 0 = public) |
| `game/setvote` | `Draw`/`Pause`/`Cancel`; returns plain text. A draw needs every survivor's vote |

Order dicts: `{type, terrID, toTerrID, fromTerrID, viaConvoy, [convoyPath]}`. Types
`Hold`, `Move`, `Support hold`, `Support move`, `Convoy`, `Retreat`, `Disband`,
`Build Army`, `Build Fleet`, `Destroy`, `Wait`. Support targets use the **parent
province** id; fleet moves into split-coast provinces use the **child coast** id.

**Gotchas (verified):**

- **Invalid orders are silently dropped or rewritten.** HTTP 200 proves nothing. Diff
  the saved orders against the request (`players.api.order_difference`).
- There is no legal-order route. `players/legal_orders.py` in the image is a tested
  generator that follows upstream's validators. Our bot reuses it as a legality check.
- `game.json` marks **unowned supply centres as `ownerCountryID: 0`**. Untouched
  neutral provinces may be missing from its `territories` list entirely (treat them as
  empty and unowned).
- A stale turn/phase request returns 400. Re-read context after acting.
- Empty `orders` + Ready keeps defaults (holds) in movement.
- A bot that crashes leaves the seat silent for the rest of the game. Catch per-phase
  errors and keep playing.

## Evidence formats

- `results.json`: slot-ordered `scores` and `countries`, `outcome`
  (`drawn`/`won`/`cancelled`), `reason` (e.g. `end_year`), `seed`, `members[]`
  (`countryID` and `supplyCenterNo` are **strings**), `final_state`, `transitions`.
- Replay (`replay.json` hosted, `replay` local): JSON array of public frames, each with
  `variant`, `game`, `status`, `history`, `messages`, `lifecycle`, `episode.seed`,
  optional `map` PNG, and `ending` on the last frame. The last frame's
  `history.phases[]` has, per phase, `units`, `centers` (all owned territories, not only
  SCs) and adjudicated `orders` with `success`/`dislodged`. **Its `Finished` entry shows
  pre-final-autumn ownership.** Use `results.members` for the final count.
- Private press never appears in public replays. Each seat's own private press is in
  its log (`private_press` record) and artifact ZIP.
- Hosted seat logs sometimes arrive as a Python bytes literal (`b'...'`). The lab loader
  decodes them.
- Hosted artifact downloads are sometimes missing (rate limits during the first
  fetch). Re-running the fetcher resumes. Report coverage instead of imputing it.

## LLM players (press variants)

Upload with `--use-llm --llm-model <OpenRouter slug>`. The pod gets
`COWORLD_LLM_ENDPOINT` (OpenAI `/v1/chat/completions` or Anthropic `/v1/messages`, no
streaming) and `COWORLD_LLM_MODEL`. The default rate limit is about 30 requests per
minute per seat; honour 429 `Retry-After`. Experience requests set
`episode_player_llm_spend_limit_usd` per episode (split over seven seats; 0 disables).
The press player (`webdip_bot/press/`) uses this channel only; the verified sidecar
contract, local parity setup and log schema are in
[`designs/press-agent-design.md`](designs/press-agent-design.md).

## Local runs

`uv run coworld download webdiplomacy -o webdiplomacy_lab/coworld_pkg` fetches the
published manifest and images (gitignored). `uv run python webdiplomacy_lab/tools/wd.py
local --image IMG --episodes N` runs IMG in all seven seats. That is own-policy
self-play: allowed locally, never hosted.
