# paintbot-pw: leagues, field and evaluation budget

Snapshot taken **2026-09-28, about 22:00 UTC**. Standings move every 10 minutes and champions
change several times a day, so the tables below are history, not current state. For today's
champions and exact `policy_ref`s run `uv run python paintbot_pw_lab/tools/pw.py scout leaders --json`;
for the running release run `pw.py deployed-ref --json`. On 2026-09-29 evening the main league ran
**0.3.79** (`d0728ab1`, rules 47 teams play), with champions such as `daveey-pw-neural:v26` (#1 Alpha,
MMR ~1,816), `aaron-coplay-coach:v8`, `aaron-paintbot-pw:v42` and `daveey1-jevbot-v2:v14`
(public round 2381, read by a verification agent).

> **Update 2026-09-29 (build and Heartland split; standings not re-snapshotted).** Read with
> `tools/deployed_ref.py` and the paintbot-pw repo, not a fresh standings pull:
>
> - The main league now runs coworld `paintbot-pw` **0.3.78**
>   (`cow_12867c2e-aca8-4755-980b-5ba668a04ad4`) = tag `coworld-v0.3.78` = `570174a2`. Live
>   games record rules **48**, whose only change is FFA-kin fog, so the teams game plays
>   **rules 47**: glory for being behind in cogs, and a per-match seat count (the paintbot-pw
>   config schema still fixes it at 16). The manifest's teams variants now set
>   `glory: {"behind_lives": 5, "behind_cogs": 10}`; that has not yet been seen in a live
>   episode's `game_config`, so the "Glory config" row below is the 2026-09-28 value.
>   Details: [mechanics.md §1.2](mechanics.md) and its currency block.
> - **Heartland is its own coworld now.** The `heartland` and `heartland-big` variants were
>   removed from the paintbot-pw manifest (0.3.71). The Heartland league (same league id as
>   below) points at game `game_73bfa882-779c-4f78-bb3d-75ecec0020a2` and coworld `heartland`
>   **0.1.9** (`cow_2ec4535a-d143-4e9e-a4a6-9fe057b8792e`), tagged `heartland-v0.1.9` at the
>   same commit `570174a2`. Heartland plays rules 48 (FFA-kin fog of war).
> - Rows below that name the coworld id, version 0.3.65, rules 45 or `bots.nim` line numbers
>   are therefore from the 2026-09-28 snapshot, not current. Current rule and API facts live in
>   [mechanics.md](mechanics.md) and [policy-surface.md](policy-surface.md).

Evidence labels:

- **documented**: stated in the game README (manifest 0.3.65) or a league guide.
- **source-verified**: checked in `Metta-AI/paintbot-pw` at `7b2b19f5` (tag `coworld-v0.3.65`), or in `~/coding/metta` at `18b4a69bdf`.
- **live**: read from the Observatory API at the snapshot time.
- **inference**: my conclusion from the items above. It is not verified.

Tooling used: project-local `coworld` 0.1.54 and `softmax-cli` 0.26.38. Both matched the latest PyPI releases on 2026-09-28.

## Game identity

| Item | Value | Label |
| --- | --- | --- |
| Coworld | `paintbot-pw` 0.3.65, `cow_5ac64504-6d4e-47c2-8476-9771d2d00cd9` (canonical for both leagues) | live |
| Game | `game_867ef763-0642-4259-82b0-e1a8c68fff42`, created 2026-09-10 | live |
| Owner | `daveey` (manifest `game.owner`), David Bloomin (David B) | documented |
| Player runtime | `game-hosted`. Upload one UTF-8 BASIC file, or a neural-BASIC ZIP (`manifest.json` + `policy.bas` + `model.bin`). WASM was removed at 0.3.33 and a WASM upload now forfeits its seat. | documented; live (two WASM memberships were disqualified on 2026-09-22 with that reason) |
| Bundled players | `baseline` (`players/base.bas`) and `basic-jev` (`players/jev.bas`, base plus the Jev LLM advisor). Heartland's baseline is `players/ffa.bas`, which is not in the manifest `player[]`. | documented |
| BASIC limits | 128 KiB source, 2 MiB memory, 50,000 instructions and 125,000 work units per decision (`examples/paintbot/bots.nim:147-148`) | source-verified |
| Rules version | 45 (`examples/paintbot/game.nim:122`) | source-verified |

The manifest's `1v1`, `2v2` and `competition` variants have **identical** game configs. The league scheduler decides how the 16 seats are filled; the variant does not.

## League 1: `paintbot-pw` (the main teams ladder)

`league_b9458ff8-0854-4e21-82b8-3c99942902e0`, division `div_d1053eaf-6e7d-4266-950a-a740d0b9bd7b` (Competition, level 1).

### Match configuration

| Item | Value | Label |
| --- | --- | --- |
| Variant | `1v1` "Two policy teams" (the only entry in `variant_rotation`) | live (league settings) |
| Mode / map | Teams game on Heartwick island. The config has no `mode` or `map` key. | live (episode `game_config`) |
| `max_ticks` | 14,400 (10 min at 24 ticks/s) | live |
| Vision | Per-cog 120° forward cone with unlimited range and wall occlusion. No `vision` key, so opt-in team vision is off. | live + documented |
| Glory config | `{"behind_lives": 5}`; other awards at defaults | live |
| Seed | **2026** in the inspected episode (the variant default) | live (1 of 1 teams episode inspected) |
| Roster | `team_n` scheduler with 2 teams, `interleaved` layout. Each episode pairs **two champion policies**. One fills all 8 even (red) seats and the other fills all 8 odd (blue) seats. The API flags 7 of each 8 copies as `is_filler: true`. Both side orders occur. | live (league settings + 12 episodes of round 2238) |
| Round cadence | Every 10 minutes, 12 episodes per round. All current champions are seated (7 entrants in round 2238). About 1,700 episodes/day. Round numbers reached 2238 on 2026-09-28. | live |
| Filler | `paintbot-pw-basic-v22:v1` (`c51834df…`), a system-owned basic policy. It also ranks as a player. | live |
| Qualification | `commissioner_key: platform`. Disqualified after 3 consecutive failures. `allowed_failures` 0.34, 2 retries. | live (settings) |
| Episode score | The winning team's glory goes to each of its seats. The loser scores **0**. Live: all 12 episodes of round 2238 had winner 428–577 and loser 0. | documented + live |
| Ranking | **Elo**: K = 32, initial 1500, `round_scoring_rule: mean`, **`margin_scale: 1000`** (set 2026-09-28 evening; read live 2026-09-29). The leaderboard labels this "MMR". | live (settings) |

How Elo reads an episode: with `margin_scale` set, each episode counts as the glory margin, `clamp(0.5 + (our glory - their glory) / 2000, 0, 1)`, not win/draw/loss. The full, source-cited rule with worked examples is in [mechanics.md §1.3](mechanics.md#13-how-glory-becomes-league-rank).

Ratings are kept per player (`entrant_attributions` uses `subject_type: player`). Inference: a new champion version inherits the player's rating.

### Standings: 2026-09-28 22:00 UTC

| # | Player (owner) | Current champion | MMR | Rounds | Episode wins | Win rate | ≈ Episodes* |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Aaron's Co-play Coach (Aaron L) | `aaron-coplay-coach:v7` | 2373 | 861 | 2,060 | 70.0% | ~2,940 |
| 2 | Alpha (David B) | `daveey-pw-neural:v24`, promoted 21:58 UTC (v23 played round 2238) | 2317 | 2,105 | 3,890 | 68.4% | ~5,690 |
| 3 | a-aron (Aaron L) | `aaron-paintbot-pw:v33` | 2305 | 870 | 2,466 | 83.1% | ~2,970 |
| 4 | Beta (David B) | `daveey1-jevbot-v2:v14` | 1858 | 1,002 | 1,974 | 63.3% | ~3,120 |
| 5 | richard (Richard H) | `richard-paintbot-pw:v1` | 1228 | 976 | 1,007 | 32.5% | ~3,100 |
| 6 | relh (Richard H) | `relh-paintbot-pw:v1` | 1219 | 971 | 978 | 31.5% | ~3,100 |
| 7 | paintbot-pw-basic-r22 (system) | `paintbot-pw-basic-v22:v1` (league filler) | 559 | 2,054 | 2,339 | 42.2% | ~5,550 |

\* `episodes_played` is null in the API. The ≈ column is wins ÷ win rate, so treat it as approximate.

The leaderboard returns `policy_label: null` for Alpha and richard. Their champions above come from `/v2/league-policy-memberships`. This is the known "auto_champion=never" label gap (see [community.md](community.md#platform-gotchas-that-bite-this-game)).

**Round 2238 (21:54 UTC) results**, one round (n = 12 episodes, one seed):

| Policy | W–L |
| --- | --- |
| `aaron-paintbot-pw:v33` | 3–0 |
| `daveey-pw-neural:v23` | 3–0 |
| `aaron-coplay-coach:v7` | 2–1 |
| `daveey1-jevbot-v2:v14` | 2–1 |
| `richard-paintbot-pw:v1` | 1–3 |
| `relh-paintbot-pw:v1` | 0–4 |
| basic filler | 0–3 |

### Entrants

Membership history holds **11 distinct players** (64 memberships). Seven are currently active champions, from **3 human owners** plus the system filler:

- **Aaron L**: a-aron and Aaron's Co-play Coach.
- **David B (game owner)**: Alpha and Beta.
- **Richard H**: richard and relh.
- **Inactive**: docxology (Daniel F, disqualified 2026-09-11) and three retired or disqualified system WASM/basic seeds.

Iteration pace, from submission counts:

- David B: Alpha ~20 versions, Beta 14.
- Aaron L: a-aron 33 versions, coach 7.
- Richard H: one version each since 2026-09-22.

Both leaders submit several times a day.

What the names suggest (inference; nobody has posted about it):

- `daveey-pw-neural` uses the neural-BASIC lane (a MinGRU actor).
- `daveey1-jevbot-v2` uses the Jev LLM advisor.

## League 2: Heartland (FFA-kin)

`league_40996eb3-4a80-457d-86d5-866f72882995`, division `div_2655c807-a54c-4dbb-9c21-3ecaae71eca8`. **Created 2026-09-28 14:57 UTC**, the day of this snapshot. The "~110 episodes/7d" is 14 rounds × 8 episodes over about 7 hours.

### Match configuration

| Item | Value | Label |
| --- | --- | --- |
| Variant | `heartland`: `{"mode":"ffa_kin","kin_layout":"cousins","max_ticks":8640,"seed":2026}` | live (episode `game_config`) |
| Map | Heartwick (no `map` key) | live |
| `max_ticks` | 8,640 (6:00). The match ends early when at most one cog is left. | live + documented |
| Vision | Per-cog cone. Team vision is not allowed in FFA. | documented |
| Rules | 16 independent seats in hidden families (with `cousins`: four families of four, in two cousin-linked pairs). One life, 10 HP, 20 m gun range. Solo heart captures pay 1 point/s. Two "great hearts" need three cogs and pay 60 points, split among the cogs present. | documented |
| Seed | **2026 in 2 of 2 inspected episodes** | live |
| Roster | `balanced_rotation` scheduler, 8 episodes per round. Each entrant got **one seat**, rotated. The other **14 seats** were the filler `heartland-filler-ffa:v1` (`7567c329…`, owned by Beta/David B). | live (round 14) |
| Round cadence | Every 30 minutes, 8 episodes | live |
| Episode score | Per seat, the kin-weighted `R_i = Σ_j r_ij · s_j` in points. A policy's episode score is the mean over its seats. | documented + live |
| Ranking | `score` algorithm, maximize. EWMA of mean round score with a 24 h half-life; initial standing 0. | live (settings) |
| Coworld version seen | Round 14 (21:40 UTC) ran on **0.3.64** (`cow_35f32fb7…`). The league now points at 0.3.65. The rules-45 change only touches the teams game, because Heartland already had it as rules 44. | live + documented |

The fixed seed matters here (source-verified). `game.nim` `setup` seeds the world from the config seed (`newLiveWorld(options.seed, …)`). Families and genomes come from that seed (`kinship.nim` `kinshipFor`/`sampleKinship`). Inference: while league episodes keep seed 2026, **which seats are related, the spawn anchors and the glory/great-heart timing are identical in every Heartland match**. Only your seat changes. Kinship is public anyway through `kin(slot)`, so this gives no information edge. It does make the environment close to fixed.

### Standings: 2026-09-28 22:00 UTC

| # | Player (owner) | Champion | Score (EWMA) | Rounds |
| --- | --- | --- | ---: | ---: |
| 1 | Alpha (David B) | `heartland-kin:v1` | 688.5 | 9 |
| 2 | Beta (David B) | `heartland-ffa-blind:v1` | 469.8 | 14 |
| — | macromackie (Scott M) | `macromackie-heartland-lab:v2`, submitted 21:58 UTC, not yet ranked | — | 0 |

Entrants: **3 players from 2 owners** (David B, Scott M). Beta's earlier `heartland-ffa:v1` is benched.

Round 14, one round (n = 8):

| Policy | Mean seat score |
| --- | ---: |
| `heartland-kin` | ≈1,080 |
| filler seats | ≈730 |
| `heartland-ffa-blind` | ≈290 |

Inference: `ffa-blind` looks like the repo's kin-blind control (`tools/make_ffa_blind.py`: `ffa.bas` with every `kin()` read as "stranger"). In this one round it scored far below the kin-aware filler. That fits "acting on kinship pays", but n is tiny.

## Our account

- **User**: James Boggs (`xhkpr7aw1f0gwjvc2yl0c5sa`).
- **Players**:
  - **James Botts** `ply_53fb05a6-73d1-494d-ab6c-8d566660d7ce` (default, active identity).
  - **Games Bond** `ply_f39295d0-ac38-4a62-ac4f-e1d62d7dc9d1`. Note the name is "Games", not "James".
  - No player named "James Boggs" or "James Bond" exists.
- **In this game: nothing** (live):
  - Both leagues: zero memberships (`mine=true`) and zero submissions.
  - None of our 1,266 policy versions has a paintbot-pw-looking name.
  - I spot-checked the September-dated uploads with ambiguous names. For example, `glory-warden` played `paintbot` 0.7.392, the older game, not paintbot-pw.
  - A first upload would bind to James Botts unless we switch identity (see the `coworld-player-swap` skill).

## Experience requests (XP)

Contract (lab `.claude/skills/coworld-experience-requests/references/api.md`; metta `observatory_api/v2/experience_requests.py`):

- **Target**: `league_id` / `division_id` (resolves the canonical coworld, now 0.3.65), or `coworld_id` + `variant_id`. Omitting the variant resolves to the first manifest variant (`competition`, which has the same config as `1v1`).
- **Roster**: one entry per seat, so **16** here (the schema pins `players` and `tokens` to exactly 16). Each entry is exactly one of:
  - `policy_ref` (`name:vN` or a version UUID)
  - `top_n: N`
  - `random: true`

  Each entry also takes an optional `slot`. `-1` rotates through open seats by episode index.
- **Roles**: the only role is the **team, set by seat parity** (even = red, odd = blue). There are no other roles. In the teams game, pin 8 seats per side with `slot`.
- **Count**: `num_episodes` from 1 to 100 per request.
- **Other fields**:
  - `private` (default false)
  - `included_players` / `excluded_players`
  - `llm_routing_override`
  - `reporters`
  - `state`
  - `game_config_overrides`, validated against the manifest schema: `seed`, `max_ticks` (≤ 28,800), `map` (13 values), `mode` (`teams`/`ffa_kin`), `vision` (`""`/`team`), `glory` (5 keys), `kin_layout` (FFA only), `slots`.

Gotchas for this game:

- **Team-game seat sampling**: `top_n`/`random` are drawn **per seat**, rank-weighted without replacement. Eight sampled "opponent" seats will be mostly *different* policies on the same team (7 champions for 8 seats). That is not what the league plays. For league-like 1v1 evidence, pin all 8 opponent seats to one explicit `policy_ref`, and swap sides between halves.
- **Resolving opponents by label**: the lab resolver (`experience_request.py resolve --division … --top N`) reads leaderboard `policy_label`, which is null for Alpha and richard. It would silently skip rank-2 Alpha. Use the membership labels in the standings table instead.
- **Private requests**: explicit opponent refs can return `409 policy_selection_not_allowed`. Do not switch the request to public to get around it.
- **Seed**: league episodes ran seed 2026. Setting `game_config_overrides.seed: 2026` reproduces league conditions. Varying the seed measures robustness that the league does not currently test (inference).

**Credits (live, 2026-09-28 22:00 UTC, `GET /usage/me/credits`)**:

| Field | Value |
| --- | --- |
| Balance | **20,000** (at the 20,000 cap) |
| Refill | **1,428.57/day** (10,000/week), next at 2026-09-29 00:00 UTC |
| Spent this period | 0 |
| Conversion | 10 credits = $1 |
| `enforced` | true |

That is the Softmax-team schedule. `whoami` reports `team member: False` for this user, so it is unclear why the account is on the team schedule. The allowance is shared across James Botts and Games Bond.

Cost scale (live, derived): league episodes report `cost_usd` of about $0.034 (teams, 16 BASIC seats) and $0.021 (Heartland). That is about **0.3 credits per episode**, or about 35 credits for a 100-episode request, **before** any Jev/LLM advisor spend. It is compute only; the real number is the `cost_preview` returned at creation. No request was created.

## Rate-limit note

On 2026-09-28 the user token's **hourly complexity budget** was nearly used up (6–131 remaining out of 125,000), presumably by other agents sharing the account. Several reads returned 429.

Public reads (`/v2/leagues`, `/v2/rounds`, `/v2/rounds/{id}/episodes`, `/v2/divisions/{id}/leaderboard`, forum/wiki `.md`) work **anonymously**, with a separate budget. Reserve authenticated calls for `mine`, credits and episode-request detail.
