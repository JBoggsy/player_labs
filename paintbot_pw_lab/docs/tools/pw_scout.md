# pw_scout.py: opponent scouting and field survey (T11)

Builds a picture of the league field from **public** data only. It uses anonymous reads
and spends no credits. Source: `tools/pw_scout.py`. Procedure:
[paintbot-pw-scout skill](../../.claude/skills/paintbot-pw-scout/SKILL.md).

## Commands

```bash
# 0. who the current champions are, as --opponent refs (3 anonymous reads)
uv run python paintbot_pw_lab/tools/pw.py leaders [--division div_d1053eaf-...] [--top 3] --json
#    (same as: pw.py scout leaders ..., or pw_scout.py leaders ...)

# 1. pull recent public league episodes (gentle: default max 30 episodes, 6 rounds)
uv run python paintbot_pw_lab/tools/pw_scout.py fetch [--league league_b9458ff8-...] \
    [--max-episodes 30] [--max-rounds 6] [--out paintbot_pw_lab/episode_data/scout/<UTC date>]

# 2. report (then write reasons.json and run it again with --reasons)
uv run python paintbot_pw_lab/tools/pw_scout.py report DIR [DIR ...] [--out DIR] \
    [--reasons reasons.json] [--by version|name] [--ours KEY_OR_NAME] [--vis-every M] [--title T]
```

### leaders

Resolves the division's current champions to exact policy refs, for `--opponent` in
`pw.py ab-requests` or an experience request. Default division: the paintbot-pw Competition
division `div_d1053eaf-6e7d-4266-950a-a740d0b9bd7b`.

1. `GET /v2/rounds?division_id=<division>&limit=6`; the newest `status == completed` round.
   Its `round_config.entrant_attributions` maps each player (`subject_id`) to the exact
   `policy_version_id` that played.
2. `GET /v2/rounds/<id>/episodes` (first page): the episode `participants` name each
   `policy_version_id` (`policy_name`, `version`, `player_name`, `owner_name`).
3. `GET /v2/divisions/<division>/leaderboard`: rank and MMR (`score`) per player. If this read
   fails, the rows come back without rank/MMR and `result.leaderboard` says why.

Why not the leaderboard's `policy_label`: it is null for some champions (Alpha and richard on
2026-09-28), and the shared `experience_request.py resolve --division` skips those rows.
The round's attributions name every entrant.

Output rows, sorted by rank (unranked last), `--top N` keeps the first N:
`{rank, player, policy_ref ("name:vN"), policy_version_id, mmr, owner, player_id}`.
`result` also has `round_id`, `round_number`, `completed_at`, `leaderboard` (`ok`, `rate
limited` or `unavailable (...)`) and `not_in_round` (leaderboard players absent from that
round). An entrant whose `policy_version_id` is not in the first episode page gets
`policy_ref: null` and a `failures[]` entry `unnamed_entrant` (exit 1); pass its
`policy_version_id` as the opponent instead. `next[]` holds an `ab-requests` command with the
refs filled in: replace the NAME placeholders and drop your own player's row.

Politeness is pw_public's (1 s pause per request, back-off on 429/5xx, 3 retries). A 429 that
outlasts the retries is exit 1 with `failures[].code = "rate_limited"` and `next` = wait and
retry, never a traceback. Verified live 2026-09-29: round 2382, 8 entrants, all named
(including Alpha `daveey-pw-neural:v26`, whose leaderboard label is null), leaderboard ok.

### fetch

1. `GET /v2/rounds?league_id=<league>&limit=<max_rounds+2>`, keeping `status == completed`.
2. For each round, `GET /v2/rounds/<id>/episodes` (first page only; a warning is printed
   if there are more).
3. For each completed row with a `replay_url`, save `r<round>_<ereq>/episode.json` (the
   public row plus `round_id` and `round_number`) and `replay.gz` (the public S3 tape,
   gzip).
4. Write `index.json` with the league, rounds, episodes and exclusion counts.

Politeness lives in the shared fetcher [`tools/pw_public.py`](../../tools/pw_public.py) (also
used by `pw_winprob.py fetch`): a 1 s pause before every request, an explicit User-Agent (the API
answers urllib's default agent with 403), and on HTTP 429 or 5xx a wait for `Retry-After` (or
10 s, 20 s, 40 s), giving up after 3 retries: exit 1 with `failures[].code = "rate_limited"` when
it was still 429 (wait and rerun; saved episodes are skipped), exit 3 for other failures. It
never loops. `--max-episodes` above 100
is refused (exit 2). Episodes already on disk are skipped without a request. A replay that is
neither gzip nor a tape is skipped and counted as `bad_replay`.

**Field-study guard.** The first newly downloaded episode goes through
`pw_episodes.load_episode`, a hash-checked `pw_trace`, before anything else is pulled. If
it fails, the fetch stops with exit 1. Build the right tag before continuing.

### report

Loads every episode with `pw_episodes.load_batch`. A failed episode is listed and makes the
exit code 1. The report writes to `--out` (default: the first root):

| File | Contents |
| --- | --- |
| `scout.md` | Human-readable report: sanity warnings, standings, matrix, profiles with shout tables, interesting episodes, thresholds |
| `scout.json` | Everything in `scout.md`, machine-readable, plus failures, exclusions and per-cell Wilson intervals |
| `scout.interesting.json` | The flagged episodes: `episode_id`, `flags`, `summary`, `detail_url`, `replay_viewer_url`, `reason` |

The agent's part: write `reasons.json` as `{"<episode_id>": "one specific sentence"}` for
the flagged episodes, then run the report again with `--reasons`. This is the
crewrift-survey pattern. Reasons for episodes that are not flagged are kept in
`scout.json` under `reasons_not_flagged`.

## Agent contract

`uv run python paintbot_pw_lab/tools/pw.py scout leaders|fetch|report ... --json` (`pw.py leaders` = `scout leaders`) (or the tool directly). Shared rules (envelope keys, exit codes, selector checks): [README.md § Agent contract](README.md#agent-contract), implemented once in `tools/pw_cli.py`.

| | |
| --- | --- |
| Inputs | `leaders`: `--division`, `--top N`. `fetch`: `--league`, `--max-episodes` (≤ 100), `--max-rounds`, `--out`, `--tag`. `report`: roots, `--out`, `--reasons FILE`, `--by version\|name`, `--ours KEY_OR_NAME`, `--vis-every`, `--title`, `--tag` |
| Outputs | `fetch`: `paintbot_pw_lab/episode_data/scout/<UTC date>/r<round>_<ereq>/{episode.json, replay.gz}` and `index.json`. `report`: `scout.md`, `scout.json`, `scout.interesting.json` in `--out` (default: the first root) |
| `--json` result | `leaders`: `{division, round_id, round_number, completed_at, leaderboard, leaders: [{rank, player, policy_ref, policy_version_id, mmr, owner, player_id}], not_in_round}`. `fetch`: `{league, out, saved, already_present, excluded, rounds, guard}`. `report`: `{report: path to scout.json, standings, sanity, interesting_without_reason}` |
| Exit codes | 0 ok; 1 the guard trace failed (fetch), some episodes did not verify (report), an entrant could not be named (leaders), or the public API was still rate-limited after retries (leaders, fetch: code `rate_limited`); 2 usage (more than 100 episodes, an `--ours` policy not in the batch with `result.valid`, roots with no episode, a division with no completed round); 3 the public API is unreachable, or `pw_trace` is not built (`next[0]`) |
| Idempotence / cache | fetch skips an episode whose two files exist, without a request; report reads the trace caches and rewrites its three files |
| Typical next step | write `reasons.json` for `result.interesting_without_reason` and rerun `report --reasons` (the envelope's `next[]`) |

## What each section means

- **Identity.** A side (team) belongs to one policy when all its seats share it. League
  episodes always do. The key is the exact `policy_version_id` (`--by version`, the
  default). `--by name` pools versions, and the report header says so. Mirror matches
  (the same policy on both sides) and mixed teams are excluded from the matrix and
  counted. Public rows carry no `game_config.slots`, so the team comes from seat parity
  (`episodes.notes = team_from_parity`). Parity is the engine's own team rule.
- **Standings.** Per policy: W-D-L, win rate with a 95% Wilson interval, mean Elo outcome
  (`clamp(0.5 + (ours − theirs)/2000, 0, 1)`, the ladder's per-episode score) ± a
  normal-approximation 95% half-width, mean winning glory, and median win time.
- **Matrix.** For each pair of row and column policy: W-L and the row's mean Elo outcome.
  Wilson intervals are in `scout.json`.
- **Profiles.** Hearts and pickups are named **in Ember's frame**: for an Azure side,
  feature k is reported as its point mirror through the midpoint of the two homes. So `h0`
  is always the side's own home and `h1` the enemy home. The report prints the Ember-frame
  positions.
  - Opening: each seat's first walk goal, labelled with the heart or pickup within 400
    units, else `field`, as seats per episode.
  - First heart reached within 30 s: the seat is within 140 units of the heart in a
    sample.
  - The team's first capture start, and its first 3 completed captures in order.
  - Weapon HP share, gun accuracy, grenade and spray use with effectiveness, pickups per
    episode.
  - Fights (from `pw_fights`), heart reach, hearts held, first-capture and win/loss times.
  - Glory composition per episode (start − countdown + awards − settled = final).
  - Shouts per seat-minute and the share within enemy earshot.
- **Shout decoder.** Each shout is tokenized. Numbers become `<n>`, including digits glued
  to a word (`FIRE22` → `FIRE<n>`), and shouts are grouped by the resulting template.
  - Per template: count, episodes, share heard by an enemy, and examples with episode,
    tick, seat and speaker position.
  - Slot hints: for each numeric slot with ≥ 5 values, the report names the speaker field
    it tracks, if the median absolute error is within tolerance. Candidate fields:
    position, walk goal, aim, the nearest enemy's position (≤ 100 units), tick (≤ 2),
    seat, hp, lives, and the raw engine index of the pickup or heart nearest the walk goal
    or speaker (exact). Positions come from sampled states (x and z interpolated), so a
    hint is an inference.
- **Interesting episodes.**
  - `upset`: the winner's batch mean Elo outcome is below the loser's. Both need ≥ 3
    episodes.
  - `zero_glory_win`.
  - `narrow_win`: winner glory ≤ 500.
  - `draw`.
  - `long_match` / `fast_win`: ≥ 2× or ≤ 0.5× the batch median ticks.
  - `vm_disabled_suspect`.
  - `friendly_kills`: ≥ 4 by one side.
  - `comeback`: ≥ 3 meter lead changes.
  - `ours_lost` with `--ours`.
  - Rarer flags are listed first, capped at 12. Links: the Observatory episode-request
    detail page and the coworld replay viewer. The viewer link is the durable format used
    in the crewrift lab; it has not been opened for paintbot-pw.
- **Sanity warnings.** Treat each one as a tooling bug until disproved:
  - mixed coworld or rules versions (do not pool);
  - every decided episode won by one side (side bias or a parity bug);
  - every policy with ≥ 3 episodes at a flat 0% or 100%;
  - shots, kills or engagements zero for every policy;
  - no pickups at all;
  - matrix exclusions.

## Verified (2026-09-29, build coworld-v0.3.78)

- `fetch --max-episodes 12 --max-rounds 2` pulled round 2373, 12 episodes on coworld 0.3.78.
  - Tape header: rules 48. The guard traced the first episode hash-exactly (local Nim
    2.2.6).
  - All 12 loaded with `results_check = participant_scores`.
  - 22 s wall time, no 429s.
- The report ran in ~6 s. It found no sanity warnings and flagged 3 episodes; the agent
  wrote reasons.
- Findings from that sample (n = 3–4 per policy, one round; descriptive only):
  - The two Aaron L policies (`aaron-coplay-coach:v8` 4-0, `aaron-paintbot-pw:v42` 3-0,
    Elo outcome ≈ 0.78) share a coded shout protocol.
    - `FIRE22 <x> <z>`: the slots track the shooter's aim point. Median error 54 / 41
      units (coach) and 96 / 69 (a-aron). There were 689 and 457 of these shouts over 4 and
      3 episodes, and 3–17% of them were within enemy earshot.
    - `ITEM23 <k>`: k equals the raw index of the pickup nearest the speaker's walk goal,
      exactly (median error 0).
    - Plain lines also appear: "Fanning out to objectives.", "Retrieving supplies.".
    - Both take about 14 grenades per episode and throw about 3.
  - `daveey-pw-neural:v26` (3-1) never shouts. It deals 100% of its damage by gun. Its
    captures start at h5 (Ember frame) in 4 of 4 episodes.
    - It lost its only game to the coach: 8 capture attempts, all reset, 0-656 in 154 s.
  - `richard`, `relh` and `jevbot` send 4–5 seats per episode first toward armor pickup
    #8 (Ember frame). The basic filler goes first toward the centre hearts h9/h8. These
    four use the base policy's plain phrases ("Contact! Cover this lane.", "Moving with
    the squad."). `jevbot` adds "Alpha/Bravo, carry on.".
- Tests: `tools/tests/test_pw_fights_flags_scout.py` covers Wilson, shout templates, slot
  hints, side identity and exclusion, and the mirror map on a real episode.

## Limits

- Only the league's first page of episodes per round is used, and only recent rounds
  (the rounds listing is not paged further).
- Small samples: a round has 12 episodes, and each policy plays 3–4 of them. Wilson
  intervals are wide. Say so when you quote results.
- Profiles pool a policy's Ember and Azure games through the mirror frame. That is only
  valid on point-symmetric maps. When the mirror does not match, indices show `(raw)`.
- Slot hints only test the candidate fields listed above. A slot that encodes something
  else (a message id such as the constant 22/23, a planned target) shows `?` with its
  range and distinct count.
- `replay_viewer_url` is built from the public row's `coworld_id` and `replay_url`. It
  has not been opened for this game.
