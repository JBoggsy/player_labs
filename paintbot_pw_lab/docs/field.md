# paintbot-pw: league, field and evaluation budget

The reference for where paintbot-pw is played, how an episode is configured and ranked, who
is in the field, and what an experience request (XP) can do and cost. Verified **2026-09-29,
about 23:00 UTC**.

Standings and champions change several times a day. The live sources are:

```bash
uv run python paintbot_pw_lab/tools/pw.py leaders --json        # champions, policy_refs, MMR (public API)
uv run python paintbot_pw_lab/tools/pw.py deployed-ref --json   # coworld version and repo tag each league runs
uv run python paintbot_pw_lab/tools/pw.py doctor --json         # release pin, builds, active player session
```

Evidence labels:

- **documented**: stated in the game guide (`coworld/paintbot/guide.md`) or `DEPLOYMENT.md`.
- **source-verified**: read in `Metta-AI/paintbot-pw` at `d0728ab1` (tag `coworld-v0.3.79`), or in
  `~/coding/metta` at `29b22cc4d9` (pulled 2026-09-29). Line numbers are at those commits.
- **live**: read from the Observatory API or a public replay on 2026-09-29.
- **inference**: a conclusion from the items above that has not been checked directly.

Tooling: project-local `softmax-cli` 0.26.38 (latest) and `coworld` 0.1.54 (0.1.55 is on PyPI;
nothing in this audit used the `coworld` CLI).

## Game identity

| Item | Value | Label |
| --- | --- | --- |
| Coworld | `paintbot-pw` **0.3.80**, `cow_1cce8736-a84e-4107-ba05-0478ce99602c`, = tag `coworld-v0.3.80` = `c8dd1def` (2026-09-29 evening; 0.3.79 = `d0728ab1` differs only in the web viewer). Each release is a new coworld record; `pw.py deployed-ref --json` gives the current one | live (`pw.py deployed-ref`) |
| Game | `game_867ef763-0642-4259-82b0-e1a8c68fff42`, created 2026-09-10; Game of the Week (`is_game_of_week: true`) | live |
| Owner | manifest `game.owner` = `daveey` (David Bloomin, "David B"). The league's game row says `owner_user_id: system`. | documented + live |
| Player runtime | `game-hosted`. Upload one UTF-8 BASIC file, or a neural-BASIC ZIP (`manifest.json` + `policy.bas` + `model.bin`). WASM was removed at 0.3.33; a WASM upload forfeits its seat. | documented |
| Bundled players | `baseline` (`players/base.bas`) and `basic-jev` (`players/jev.bas`, base plus the Jev LLM advisor) | documented (`reference/manifest-0.3.80.json`) |
| BASIC limits | 128 KiB source, 2 MiB memory, 50,000 instructions and 125,000 work units per decision (`examples/paintbot/bots.nim:154-155`) | source-verified |
| Rules | Live recordings are stamped **48** (`sim.nim:237`, `LiveRules`). Rules 48 changed only FFA-kin fog, so the teams game plays rules 47. See [mechanics.md](mechanics.md). | source-verified + live (3 tapes of round 2388) |
| Variants | `competition`, `1v1`, `2v2` (identical teams configs) and 12 `map-*` variants. The league plays `1v1` only. | documented |

**Heartland is out of scope for this lab.** FFA-kin was split into its own coworld on
2026-09-28: coworld `heartland` 0.1.10 (`cow_a7182349-1dea-4ac0-991f-9dbbdf0a3ef7`, tag
`heartland-v0.1.10`, same commit `d0728ab1`). It has two leagues, **Heartland**
(`league_40996eb3-4a80-457d-86d5-866f72882995`, variant `heartland`) and **Heartland Big**
(`league_c463b65f-99f1-43ae-bb03-2d4f7f094f1b`, variant `heartland-big`, 50 seats), both
scored by an EWMA `score` ranking with 30-minute rounds, and its own forum and wiki under the
name `heartland` (live, `/v2/leagues`). FFA starters for reference only are in
[`reference/heartland/`](../reference/heartland/). `BOTPAINT`, `paintbot-cdx` and the older
`paintbot` leagues are different coworlds.

## The league: `paintbot-pw` (the only league on this coworld)

`league_b9458ff8-0854-4e21-82b8-3c99942902e0`, division `div_d1053eaf-6e7d-4266-950a-a740d0b9bd7b`
(Competition). Participation guide:
`https://softmax.com/api/observatory/v2/leagues/league_b9458ff8-0854-4e21-82b8-3c99942902e0.md`.
The league detail route now needs authentication; the `.md` guide, `/v2/leagues`, rounds, round
episodes and the leaderboard are public (live).

### Match configuration

| Item | Value | Label |
| --- | --- | --- |
| Variant | `1v1` "Two policy teams": the only entry in `variant_rotation`; `commissioner_config.default_variant_id: 1v1` | live (league settings) |
| Episode `game_config` | `{"seed": 2026, "glory": {"behind_cogs": 10, "behind_lives": 5}, "max_ticks": 14400, "slots": [red, blue, …], "players": [16]}`. No `mode`, `map` or `vision` key: teams game on Heartwick, per-cog 120° sight cones, team vision off. | live (`ereq_86732f82…`, round 2388, 0.3.79) |
| Glory awards | **`behind_cogs: 10` and `behind_lives: 5` are live**, every other award at the engine default. The replay tapes agree: `quietSupplies 10/30 s, behindLives 5/5 s, heart 20, behindCogs 10/5 s`. Values and meaning: [mechanics.md §1.2](mechanics.md). | live (episode config + 3 tapes, 2026-09-29) |
| Seed | The `seed: 2026` shown in `game_config` is **not** the engine seed. Each league episode's engine seed is `crc32("<division_id>:<round_index>") mod (2^31 − MAX_PLANNED_EPISODES) + job_index`, so every episode of every round is a different world. See [Seeds](#seeds-what-actually-reaches-the-engine). | source-verified + live |
| `max_ticks` | 14,400 (10 min at 24 ticks/s) | live |
| Roster | `team_n` scheduler, 2 teams, `interleaved` layout, `allied_teams [[0],[1]]`. Each episode pairs **two champion policies**: one fills all 8 even (red) seats, the other all 8 odd (blue) seats. The API flags 7 of each 8 copies `is_filler: true`. Both side orders occur. `insufficient_players: filler_policy`. | live (settings + round 2388) |
| Round cadence | Every **10 minutes**, **12 episodes** per round. With 8 champions each plays 3 episodes per round, and pairings can repeat inside a round. About 1,700 episodes a day. Round 2388 completed 2026-09-29 22:58 UTC. | live |
| Filler | `paintbot-pw-basic-v22:v1` (`c51834df…`), system-owned. It also ranks as a player. | live |
| Qualification | `commissioner_key: platform`. Disqualified after **3 consecutive failures**. Fulfillment: `retry_times 2`, `allowed_failures 0.34`. | live (settings) |
| Episode score | The winning team's glory goes to each of its seats; the loser gets **0**. Round 2388: every winner 520–569, every loser 0. | documented + live |
| LLM spend | **No per-seat LLM spend cap.** The league settings carry neither `episode_player_pod_llm_spend_limit_usd` nor `llm`, so both default to `null` (no cap, platform default model allowlist). See [LLM budget for the Jev oracle](#llm-budget-for-the-jev-oracle). | live + source-verified |
| Compute cost | `cost_usd` 0.021 for one 0.3.79 league episode (16 BASIC seats), about 0.2 credits | live (1 episode) |
| Campaign | A `campaign` block exists in settings but `enabled: false` | live |

### Ranking

Elo, labelled "MMR" on the leaderboard: `k_factor 32`, `initial_rating 1500`,
`round_scoring_rule: mean`, **`margin_scale: 1000`** (live, 2026-09-29). With `margin_scale` set,
each episode counts as the glory margin, `clamp(0.5 + (our glory − their glory) / 2000, 0, 1)`,
not as a plain win or loss. The full, source-cited rule with worked examples is in
[mechanics.md §1.3](mechanics.md#13-how-glory-becomes-league-rank); do not restate it here.

**Ratings belong to the player, not to the policy version** (source-verified,
`packages/observatory-competitions/src/observatory_competitions/v2/ladders/`):

- The ladder refuses any standing or entrant whose `subject_type` is not `"player"`
  (`updater.py:134-135`, `150-151`, `269-270`). Standings are keyed by
  `(subject_type, subject_id)` = the player id (`updater.py:566-567`; `rankings/base.py:18-26`).
- A player with no standing starts at the initial rating (`updater.py:387-390`; `rankings/elo.py:41`).
  Every version that scores in a round is appended to the same standing's
  `contributing_policy_version_ids` (`updater.py:426-431`).

Consequence for us: a new champion version **inherits its player's MMR** and moves that same
number; there is no fresh start per version. A weak version submitted under a player drags that
player's rating, and a strong one has to climb from wherever the player already is. Our two
players (James Botts, Games Bond) have never entered, so each would start at 1500 and is rated
independently. Using one player for the main line and the other for risky experiments keeps the
main rating clean (inference).

MMR values from before 2026-09-29 are not comparable with today's: the filler rose from 559
(2026-09-28) to 1485 and the top fell from 2373 to 1820, which suggests a re-rating after the
`margin_scale` change (inference; not verified in source).

### Champions: 2026-09-29 22:58 UTC (round 2388)

Live source: `pw.py leaders --json`. This table is a dated reading.

| # | Player (owner) | Champion `policy_ref` | MMR | Round 2388 W–L (mean winning glory) |
| --- | --- | --- | ---: | --- |
| 1 | Aaron's Co-play Coach (Aaron L) | `aaron-coplay-coach:v8` | 1820 | 2–1 (533) |
| 2 | Alpha (David B) | `daveey-pw-neural:v26` | 1799 | 2–1 (550) |
| 3 | a-aron (Aaron L) | `aaron-paintbot-pw:v42` | 1796 | 3–0 (540) |
| 4 | Beta (David B) | `daveey1-jevbot-v2:v14` | 1676 | 2–1 (526) |
| 5 | Andre von Auto (Andre H) | `zhar:v1` | 1640 | 3–0 (541) |
| 6 | relh (Richard H) | `relh-paintbot-pw:v1` | 1573 | 0–3 |
| 7 | richard (Richard H) | `richard-paintbot-pw:v1` | 1571 | 0–3 |
| 8 | paintbot-pw-basic-r22 (system filler) | `paintbot-pw-basic-v22:v1` | 1485 | 0–3 |

One round is 12 episodes; treat the W–L column as colour, not evidence. The top three are within
24 MMR of each other.

### Entrants

Eight active champions from **four human owners** plus the system filler:

- **Aaron L**: a-aron (`aaron-paintbot-pw`, v42) and Aaron's Co-play Coach (v8).
- **David B** (the game's maintainer): Alpha (`daveey-pw-neural`, v26) and Beta (`daveey1-jevbot-v2`, v14).
- **Richard H**: richard and relh, one version each since 2026-09-22.
- **Andre H**: Andre von Auto (`zhar:v1`), new since 2026-09-28.

The version numbers show pace: Aaron L's a-aron went v33 → v42 and Alpha v24 → v26 in one day.
What the names suggest (inference; nobody has posted about it): `daveey-pw-neural` uses the
neural-BASIC lane and `daveey1-jevbot-v2` uses the Jev LLM advisor.

The leaderboard has returned `policy_label: null` for some champions (the
`auto_champion=never` label gap, see [community.md](community.md#platform-gotchas-that-bite-this-game));
`pw.py leaders` resolves labels from the round's entrant attributions instead.

### Seeds: what actually reaches the engine

The `seed` in an episode's `game_config` (API field) is the stored *public* config, which keeps
the variant's placeholder 2026. The engine gets the per-episode seed stored on the episode
request row. Source path (metta `29b22cc4d9`, paintbot-pw `d0728ab1`):

1. **League rounds.** The round plan seed is
   `zlib.crc32(f"{division_id}:{round_index}") % MAX_PLAN_SEED_EXCLUSIVE`
   (`observatory-competitions/.../orchestration/workflows.py:1368-1375`;
   `MAX_PLAN_SEED_EXCLUSIVE = 2**31 - MAX_PLANNED_EPISODES`,
   `observatory-core/.../v2/ladders/config.py:160`). Episode *i* gets `plan seed + i`
   (`observatory-api/.../v2/round_lifecycle.py:2119`), stored as `EpisodeRequest.seed`
   (`round_lifecycle.py:2345`).
2. **Experience requests.** With an explicit integer `game_config_overrides.seed`, every episode's
   row seed is that value. Without one, each episode gets
   `sha256(f"{request_id}:{job_index}")[:8] mod 2^31` (`observatory-api/.../v2/experience_requests.py:145-147`,
   `568-593`).
3. **Dispatch.** When the row has a seed and the config's `seed` is an integer (it always is
   here: the schema requires it), the job's `game_config.seed` is replaced by the row seed
   (`observatory-api/.../v2/episode_requests.py:268-274`).
4. **Runner to engine.** The coworld runner writes `job.game_config` (plus tokens) to
   `COGAME_CONFIG_URI` (`packages/coworld/src/coworld/runner/runner.py:427-431`,
   `init_config.py:86-91`). The paintbot-pw host passes its environment through to the engine
   unchanged (`coworld/paintbot/runtime/host.py:129-138`). The engine reads `config.seed` into
   `GameOptions` (`src/polyworld/coworld.nim:273`, `289`), seeds the world with it and records it
   in the tape (`examples/paintbot/game.nim:495`: `newLiveWorld(options.seed, …); recording.seed = options.seed`).

Live check (2026-09-29): round 2388 is `round_index` 2387. Its jobs 9, 10 and 11 have tape seeds
1511126198, 1511126199 and 1511126200, exactly `crc32("div_d1053eaf-6e7d-4266-950a-a740d0b9bd7b:2387") mod 2^31 + job_index`,
while their API `game_config` says 2026.

Consequences:

- League play is **not** a fixed world. Every episode is a different seed; seed 2026 has no special
  status. Robustness across seeds is what the league tests.
- In an XP, an explicit `game_config_overrides.seed` **does** fix the engine seed, so every episode
  of that request plays the same world. A paired A/B that gives the baseline request and the
  candidate request the same explicit seed list pairs identical worlds. Omitting the seed gives
  every episode a distinct derived seed.
- The API's `game_config.seed` cannot tell you which world an episode played; read the tape
  (`pw_trace` reports `seed`; `pw_episodes` exports `engine_seed` next to `config_seed`).

### LLM budget for the Jev oracle

- **League: no cap.** The per-seat, per-episode limit comes from the league setting
  `episode_player_pod_llm_spend_limit_usd` (`observatory-core/.../v2/league_settings_schema.py:205-216`,
  default `null` = no cap). The paintbot-pw league does not set it (live settings), and the
  dispatcher takes the minimum of the league and requester limits, `null` when neither is set
  (`observatory-core/.../v2/llm_spend_limits.py:1-8`; `observatory-execution/.../job_runner/dispatcher.py:505-530`),
  exporting `BEDROCK_SIDECAR_SPEND_LIMIT_USD` only when a limit exists (`dispatcher.py:1269-1272`).
- **The Jev oracle is billed per seat.** The paintbot-pw host sends each ask with
  `X-Coworld-Player-Slot` (`coworld/paintbot/runtime/oracle.py`), and the sidecar re-attributes a
  game-pod call carrying that header to `role: player` for that slot
  (`bedrock_sidecar.py:1481-1511`), so a player spend limit would apply to it (`bedrock_sidecar.py:1478-1479`).
  The request-rate bucket (120/min per seat, documented) still applies.
- **Model allowlist:** the league has no `llm` block, so `player_model_allowlist` is `null`, which
  means the platform default allowlist (`league_settings_schema.py:139-148`). Whether that list
  admits the oracle's `typesafe/jev-1.13` route was not checked.
- **XP requests:** `episode_player_llm_spend_limit_usd` (optional, default `null`) is a combined
  per-episode cap split evenly across seats (`observatory-api/.../v2/api_types.py:275-281`;
  `routes/app/v2/experience_requests/service.py:978-982`). When a request targets the league, the
  stricter of the two limits wins. A limit of **0** makes the sidecar refuse every call with a
  429 `ThrottlingException` (`bedrock_sidecar.py:2083-2121`), so the oracle answers `-1`.
- `llm_routing_override` (`openrouter` / `bedrock`) only picks the provider, is **team-only** (403
  otherwise) and `openrouter` needs `num_episodes == 1` (`service.py:805-811`). It does not change
  any spend limit.
- Live: a league episode reports `llm_spend_limit_rejections: null`. Whether Beta's asks actually
  succeed in league play needs a seat log (not checked).

## How the field plays (80 league episodes, 2026-09-29)

Measured on 80 hash-verified main-league episodes at 0.3.79 (rounds 2382-2388). Method, tables
and caveats: [reports/2026-09-29-league-field-analysis.md](reports/2026-09-29-league-field-analysis.md).
The field changes daily; re-run `pw.py scout fetch` / `scout report` before relying on it.

- **Matches end by elimination and fast.** 78 of 80 ended by elimination (median 82 s, p10-p90
  64-124 s), 2 by a full meter, none at the time limit or drawn. Winning glory median 544 (mean
  554): start 600, countdown −88, all awards together +42 (glory hearts +15.5, behind in lives
  +16, behind in cogs +7.9, quiet supplies +3). A typical winner's Elo outcome is about 0.78.
- **No side advantage in the league.** Odd seats won 43 of 80 (54%, Wilson 43-64%; 51% adjusted for
  policy strength). The 71% odd-side win rate in local base-vs-base runs is a mirror-match effect.
- **Mean Elo outcome per champion** (20 episodes each, ±95% half-width): aaron-coplay-coach:v8
  0.68 ±0.10, daveey-pw-neural:v26 0.66 ±0.10, aaron-paintbot-pw:v42 0.64 ±0.12, zhar:v1 0.61 ±0.11,
  daveey1-jevbot-v2:v14 0.50 ±0.12, richard-paintbot-pw:v1 0.37 ±0.11, relh-paintbot-pw:v1
  0.31 ±0.09, paintbot-pw-basic-v22:v1 0.23.
- **Lineages and styles.**

  | Lineage | Policies | Style |
  | --- | --- | --- |
  | Aaron custom | aaron-coplay-coach, aaron-paintbot-pw | h6 > h4 > h2 flank opening, ~15 grenade pickups per episode, team fire-call protocol; win 76-77% of opening duels |
  | Neural | daveey-pw-neural | silent, gun only, almost no pickups, barely captures (first capture 51 s, 1.3 hearts held) yet best K/D 1.53 and fastest wins (74 s): wins by killing |
  | jev.bas derivative | daveey1-jevbot-v2 | base.bas play plus squad relay shouts |
  | base.bas derivatives | zhar, richard, relh | base.bas shouts and armor-first opening |
  | Older system starter | paintbot-pw-basic-v22 (league filler) | different shout set, last place |

- **Shout protocols** (text is in every tape). The Aaron policies shout `FIRE22 <x> <z>` — an
  enemy-position call at the shooter's aim point (a living enemy within 150 units in 96%) — about
  170 times per episode, and `ITEM23 <k>` — "I just took pickup k" (845 of 845). 95%+ are out of
  enemy earshot. base.bas lines ("Grenade out!") are heard by enemies 93-100% of the time.
- **Friendly fire and disguises.** 7.1% of all hits are on teammates (about 3% of damage for the
  Aaron policies, up to 15.5% for the filler). A disguised cog is hit about 31 times as often per
  tick as an undisguised one, mostly by its own team (74 teammate hits vs 15 enemy hits):
  uniforms cost more than they save in this field. Grenades: 100 grenade self-kills against 164
  grenade enemy kills across the sample.
- **Contested captures are real but rare**: 12 in 9 of 80 episodes (both teams must be within
  140 units of the heart at once).

## Replay links

The durable watch link is the Observatory wrapper
`https://softmax.com/observatory/coworld-replays/<coworld_id>?replay_uri=<url-encoded replay_url>`.

**The wrapper does not forward a tick (`t=`) to the game's viewer** (source-verified, metta
`29b22cc4d9`, under `web/softmax.com/src/`):

- The page parses only `achievement`, `episode_id`, `game`, `game_version` and `replay_uri`
  (`app/(observatory)/observatory/(application)/coworld-replays/[coworldId]/page.tsx:6-14`).
- The frame gets the viewer URL from `POST /v2/coworlds/replays/session` and adds only `chrome`,
  `achievement` and `bg` to it (`observatory/components/CoworldReplayFrame.tsx:1248-1272`). Ticks flow
  from the viewer to the page by `postMessage`, never the other way.

The paintbot-pw viewer itself does honour `?t=<tick>` in **its own** query string: it seeks there and
pauses (`coworld/paintbot/viewer.js:1748-1749` at `c8dd1def`, 0.3.80, `seek` at `373-377`). paintbot-pw ships a static
viewer bundle (`replay_viewer.bundle` in the manifest), so a tick deep link needs the raw viewer URL
from the replay-session call, which is signed and short-lived (inference: not a durable link). Match
reports should link the wrapper and state the tick in text.

## Our account

- **User**: James Boggs (`xhkpr7aw1f0gwjvc2yl0c5sa`).
- **Players**: **James Botts** `ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce` (the selected player) and
  **Games Bond** `ply_f39295d0-ac38-4a62-ac4f-e1d62d7dc9d1` ("Games", not "James"). No player named
  "James Boggs" or "James Bond" exists.
- **The James Botts session expired on 2026-09-16** (`pw.py doctor`, 2026-09-29). Until
  `uv run coworld player use` refreshes it, commands act as the main user, and an upload would not
  bind to James Botts. See the `coworld-player-swap` skill.
- **In this league: nothing.** None of the eight current champions is ours (public leaderboard,
  2026-09-29). The authenticated `mine=true` membership check was rate-limited on 2026-09-29; the
  last successful one (2026-09-28) found zero memberships and zero submissions.

## Experience requests (XP)

Contract: lab `.claude/skills/coworld-experience-requests/references/api.md` and metta
`packages/observatory-api/src/observatory_api/v2/experience_requests.py`.

- **Target**: `league_id` / `division_id` (resolves the league's canonical coworld, now 0.3.79), or
  `coworld_id` + `variant_id`. Omitting the variant resolves to the first manifest variant
  (`competition`, same teams config as `1v1`).
- **Roster**: one entry per seat, **16** (the schema pins `players`, `tokens` and `slots` to exactly
  16). Each entry is exactly one of `policy_ref` (`name:vN` or a version UUID), `top_n: N` or
  `random: true`, with an optional `slot` (`-1` rotates through open seats by episode index).
- **Roles**: the only role is the **team, set by seat parity** (even = red, odd = blue).
- **Count**: `num_episodes` 1 to 100 per request.
- **Other fields**: `private` (default false), `included_players` / `excluded_players`,
  `episode_player_llm_spend_limit_usd`, `llm_routing_override` (team-only), `reporters`, `state`,
  and `game_config_overrides`, validated against the 0.3.79 schema: `seed` (int32), `max_ticks`
  (≤ 28,800), `map` (13 values, `""` = Heartwick), `mode` (`teams` / `ffa_kin`), `vision`
  (`""` / `team`), `glory` (7 keys: `quiet_supplies`, `quiet_supplies_seconds`, `behind_lives`,
  `behind_lives_seconds`, `heart`, `behind_cogs`, `behind_cogs_seconds`), `kin_layout` (FFA only),
  `slots`. Overrides are shallow-merged over the variant config, so a `glory` override replaces the
  whole object: include `behind_lives: 5` and `behind_cogs: 10` to keep league values.

Gotchas for this game:

- **Team-game seat sampling**: `top_n` / `random` are drawn **per seat**, rank-weighted without
  replacement, so eight sampled "opponent" seats are mostly different policies on one team. The
  league never plays that. For league-like evidence, pin all 8 opponent seats to one explicit
  `policy_ref` and swap sides between halves.
- **Resolving opponents by label**: use `pw.py leaders` (entrant attributions), not leaderboard
  `policy_label`, which can be null for champions.
- **Private requests**: explicit opponent refs can return `409 policy_selection_not_allowed`. Do not
  switch the request to public to get around it.
- **Seed**: see [Seeds](#seeds-what-actually-reaches-the-engine). An explicit seed fixes the world
  for the whole request; the league uses a different seed every episode, so spread A/B seeds.

**Credits** (live, 2026-09-29 23:00 UTC, `GET /usage/me/credits`):

| Field | Value |
| --- | --- |
| Balance | **20,000** (at the 20,000 cap) |
| Refill | **1,428.57/day** (10,000/week), next at 2026-09-30 00:00 UTC |
| Spent this period | 0 |
| Conversion | 10 credits = $1 |
| `enforced` | true |

That is the Softmax-team schedule ([xp-credits.md](../../docs/xp-credits.md)). The allowance is
shared across James Botts and Games Bond and across every lab on this account. Cost scale: about
0.2 credits of compute per 16-seat BASIC episode (one 0.3.79 league episode at $0.021), so roughly
20 credits for a 100-episode request **before** any Jev/LLM spend (inference; the real number is the
`cost_preview` returned at creation).

## Rate limits

The account's hourly budget is shared with other agents and is often nearly spent: on
2026-09-29 the user token had 12 of 12,500 requests and 183 of 125,000 complexity left in the hour,
and a membership read returned 429 (live response headers `x-ratelimit-*-hour-remaining`).

Anonymous reads have their own budget and cover rounds (`/v2/rounds?division_id=…`), round episodes
(`/v2/rounds/{id}/episodes`, with scores, participants and `replay_url`), the leaderboard, the
league list (`/v2/leagues`), the league guide (`.md`), forum and wiki `.md`, and replays on
`softmax-public.s3.amazonaws.com`. Save authenticated calls for league detail, episode detail
(`game_config`, `cost_usd`), memberships, credits and XP.
