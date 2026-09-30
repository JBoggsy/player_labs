# Paintbot PW field analysis: open questions answered from league data (2026-09-29)

Dated evidence report (not maintained as current truth; current facts live in
[field.md](../field.md) and [mechanics.md](../mechanics.md)). Produced by a lab research agent from
repo `personal_labs_paintbot_pw` at `c045253c`. Engine source
`~/coding/coworlds/paintbot-pw` tag `coworld-v0.3.79` = `d0728ab1`. Metta `main` pulled to
`29b22cc4d9` (2026-09-29 22:28 UTC) for the platform seed code.

## Sample

| | |
| --- | --- |
| Command | `uv run python paintbot_pw_lab/tools/pw.py scout fetch --max-episodes 80 --max-rounds 10 --out paintbot_pw_lab/episode_data/audit-2026-09-29 --json` |
| League | `league_b9458ff8-0854-4e21-82b8-3c99942902e0` (the round listing does not name the division; `pw.py leaders` for the Competition division `div_d1053eaf-…` resolves round 2388, the newest round in this sample, and names the same 8 policies) |
| Episodes | 80 public, completed, all hash-verified by `pw_trace` (guard ok, 0 failed, 0 excluded) |
| Rounds | 2382 (8 of its 12 episodes: the 80-episode cap cut it), 2383-2388 (12 each) |
| Version | **all 80 are `coworld_version` 0.3.79**, tape header rules 48 (the teams game plays rules 47). No older-version episodes, so there was nothing to split out. The earlier 12-episode download in `episode_data/scout/2026-09-29/` is 0.3.78 and was **not** pooled. |
| Glory config on the tape | `behindCogs 10, behindCogsSeconds 5, behindLives 5, behindLivesSeconds 5, heart 20, quietSupplies 10, quietSupplySeconds 30` in all 80. This settles the open item in WORKING_CONTEXT: live league episodes do pay `behind_cogs: 10`. |
| Entrants (8; each plays 20 episodes, 3 per round) | aaron-coplay-coach:v8, daveey-pw-neural:v26, aaron-paintbot-pw:v42, zhar:v1, daveey1-jevbot-v2:v14, richard-paintbot-pw:v1, relh-paintbot-pw:v1, paintbot-pw-basic-v22:v1 |

Tables were queried with DuckDB over the per-episode Parquet tables that `pw_episodes` writes
(`paintbot_pw_lab/episode_data/audit-2026-09-29/r*/pw_cache/tables/*.parquet`; open them with
`uv run python paintbot_pw_lab/tools/pw.py episodes <dir> --sql "..."`). The profile tables come
from `uv run python paintbot_pw_lab/tools/pw.py scout report paintbot_pw_lab/episode_data/audit-2026-09-29 --json`.
The ad hoc query scripts were scratch and are not kept; each section names its tables and joins.

Unit caveat for every table below: one episode is one sample per policy. The 8 seats of a
policy in one episode are not independent.

---

## 1. Engine seeds and duplicate games

### Method

- `episodes.engine_seed` (the tape seed, which `pw_trace` checks against the results seed),
  `episodes.final_hash`, initial `spawns`, and `states` at t = 6-48.
- Engine: `src/polyworld/coworld.nim:288-289` (hosted engine takes `seed: config.seed` from the
  config file the runner writes), `examples/paintbot/game.nim:495` (`newLiveWorld(options.seed, …)`,
  `recording.seed = options.seed`).
- Platform (metta `29b22cc4d9`):
  - `packages/observatory-api/src/observatory_api/v2/episode_requests.py:267-274`: if the episode
    request row has a `seed`, it **replaces** the variant's placeholder `game_config.seed` (2026).
  - League rounds: `packages/observatory-competitions/src/observatory_competitions/v2/tournaments/seating.py:214`
    `seed = seed_base + matchup_index * best_of + game_index`.
  - Experience requests: `packages/observatory-api/src/observatory_api/v2/experience_requests.py:573-593`.
    An explicit `game_config_overrides.seed` pins **every** episode of the request to that exact
    seed; without it each episode gets `sha256(parent_id:job_index) mod 2^31` (`:145-147`).

### Result

| Check | Result |
| --- | --- |
| Distinct engine seeds | **80 of 80** (range 712,704,034-1,568,420,031) |
| Structure | inside a round the seeds are consecutive: `engine_seed − job_index` is one constant per round (7 of 7 rounds), matching `seed_base + matchup_index·best_of + game_index` |
| `game_config.seed` | not in public rows (`config_seed` is null for all 80); the platform overwrites the 2026 placeholder before the engine sees it, so 2026 never reaches the engine in league play |
| Distinct final hashes | **80 of 80**; no two episodes are the same game |
| Distinct initial spawn layouts (t = 0) | 80 of 80: the seed moves spawns, so games differ from tick 0 |
| Distinct world+command states at t = 6, 12, … 48 | 80 of 80 at every sampled tick |
| Same pairing, same sides, repeated | 39 distinct (even, odd) pairings in 80 episodes; 24 pairings recur on the same sides, all with different seeds and different games |

### What it means for A/B pairing by explicit seed

- Seeds are the only source of match-to-match variation for deterministic BASIC policies:
  same seed + same roster + same build = the same match. The engine's own deployment log
  confirms this also for a *sampling* neural bundle: two hosted runs at seed 2026 with the
  same body produced byte-identical replay files (`coworld/paintbot/DEPLOYMENT.md:538-544` at
  `d0728ab1`).
- **An experience request with an explicit `game_config_overrides.seed` and `num_episodes > 1`
  plays the same match `num_episodes` times** when every seat is deterministic. That is
  wasted credit, not replication. (Inference from the code paths above plus the deployment
  note; not tested with a hosted request.)
- Pairing A and B on the same world therefore needs **one request per seed per arm**
  (`num_episodes: 1`, same explicit seed in both), or accepting unpaired arms. Unpinned
  requests get seeds from `sha256(request_id:job_index)`, so two requests never share seeds.
- Given the local measurement that seed pairing barely reduced outcome variance (per-pair SD
  0.40 vs about 0.44 unpaired), the cheaper design is **unpinned, unpaired** requests with
  enough episodes. Pin a seed only for a deliberate replay of one world, and then set
  `num_episodes: 1`.
- The league itself never repeats a world, so a league-condition A/B should also vary seeds.

### Caveats

The seed-to-engine path is read from code at metta `29b22cc4d9`, not observed on a pinned
hosted request. A 1-request pilot with `seed: S, num_episodes: 2` would confirm (expect two
identical `final_hash` values).

---

## 2. Side asymmetry in the league

### Method

`q2.py`: winner and Elo outcome `clamp(0.5 + (own − other)/2000, 0, 1)` by side from
`episodes` + `seats` (seat 0 = even/Ember/"red", seat 1 = odd/Azure/"blue"). 95% Wilson
intervals for win rates. A strength-adjusted side effect from a Bradley-Terry logistic fit
(`logit P(odd wins) = h + s_odd − s_even`, light ridge 0.5 on policy strengths) and a linear
fit of the same form on the odd side's Elo outcome.

### Result, overall (n = 80, 0 draws)

| Measure | Even (Ember) | Odd (Azure) |
| --- | --- | --- |
| Wins | 37 | 43 |
| Odd win share | | **53.8% [42.9%, 64.3%]** |
| Mean Elo outcome | 0.477 | 0.523 (± 0.061) |
| Strength-adjusted P(odd wins, equal teams), Bradley-Terry | | **0.51 [0.35, 0.68]** (h = 0.045 ± 0.685 log-odds) |
| Strength-adjusted odd Elo outcome, linear | | **0.502 ± 0.043** |
| **Local base vs base** (earlier finding) | | **40/56 = 71.4% [58.5%, 81.6%]** |

My own 6 local base-vs-base games at 0.3.79 (seeds 1-6, see §6) went odd 5, even 1, in line
with the local finding.

### Per policy (n by side is not balanced: sides were not assigned evenly per policy)

| Policy | Side | n | W | Win rate [95% Wilson] | Mean Elo outcome |
| --- | --- | ---: | ---: | --- | ---: |
| aaron-coplay-coach:v8 | even | 13 | 9 | 0.69 [0.42, 0.87] | 0.611 |
| aaron-coplay-coach:v8 | odd | 7 | 7 | 1.00 [0.65, 1.00] | 0.811 |
| aaron-paintbot-pw:v42 | even | 7 | 5 | 0.71 [0.36, 0.92] | 0.570 |
| aaron-paintbot-pw:v42 | odd | 13 | 11 | 0.85 [0.58, 0.96] | 0.681 |
| daveey-pw-neural:v26 | even | 7 | 5 | 0.71 [0.36, 0.92] | 0.608 |
| daveey-pw-neural:v26 | odd | 13 | 11 | 0.85 [0.58, 0.96] | 0.688 |
| daveey1-jevbot-v2:v14 | even | 13 | 6 | 0.46 [0.23, 0.71] | 0.478 |
| daveey1-jevbot-v2:v14 | odd | 7 | 4 | 0.57 [0.25, 0.84] | 0.545 |
| zhar:v1 | even | 8 | 6 | 0.75 [0.41, 0.93] | 0.642 |
| zhar:v1 | odd | 12 | 8 | 0.67 [0.39, 0.86] | 0.588 |
| richard-paintbot-pw:v1 | even | 6 | 3 | 0.50 [0.19, 0.81] | 0.502 |
| richard-paintbot-pw:v1 | odd | 14 | 2 | 0.14 [0.04, 0.40] | 0.307 |
| relh-paintbot-pw:v1 | even | 13 | 3 | 0.23 [0.08, 0.50] | 0.362 |
| relh-paintbot-pw:v1 | odd | 7 | 0 | 0.00 [0.00, 0.35] | 0.228 |
| paintbot-pw-basic-v22:v1 | even | 13 | 0 | 0.00 [0.00, 0.23] | 0.226 |
| paintbot-pw-basic-v22:v1 | odd | 7 | 0 | 0.00 [0.00, 0.35] | 0.225 |

### Answer

The league shows **no detectable side advantage**: raw odd win share 54% (CI spans 50%),
strength-adjusted 51%. The local base-vs-base asymmetry (71% odd) is outside the league's
interval, so it is a property of the **mirror match** (two identical deterministic policies
amplify whatever small map or tie-break asymmetry exists), not of the game as the league plays
it. Per-policy side splits all have overlapping intervals; four of the stronger policies do
better on odd and richard does much worse on odd, but n = 6-14 per cell cannot separate that
from opponent mix (sides were confounded with opponents in this sample).

Practical: keep side-balanced local screens (the mirror asymmetry is real locally), but do not
model a side effect in league-condition analysis.

### Caveats

The side is from seat parity (`team_from_parity`), which is the engine's rule. The
Bradley-Terry interval is wide because 8 strengths are estimated from 80 games.

---

## 3. How matches end and what wins are worth

### Method

End type from `episodes`: draw if `winner = −2`; time limit if `ticks ≥ end_tick` (14,400);
elimination if the loser has `cogs_out = 8`; otherwise meter. Winner glory composition from the
`glory` table (awards to the winning team) plus `glory_countdown_*` and `glory_initial_*`.

### Result: endings (n = 80)

| Ending | n | Share | Mean length | Median | Range | Mean winning glory | Winner's cogs out (mean) |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| Elimination | 78 | **97.5%** | 85.9 s | 81.7 s | 56-145 s | 549 | 1.9 |
| Meter full | 2 | 2.5% | 195.8 s | | 182 s, 210 s | 763 (529, 996) | 6.0 |
| Time limit | 0 | 0% | | | | | |
| Draw | 0 | 0% | | | | | |

Both meter wins were aaron-coplay-coach vs aaron-paintbot-pw (same author), long attrition
games where the winner also had 6-7 cogs out; the 996-glory win (`ereq_350c67fe`) was paid
mostly by behind-in-cogs.

Distributions (all 80): match length p10/p25/p50/p75/p90 = 64 / 71 / 82 / 96 / 124 s.
Winning glory p10/p25/p50/p75/p90 = 521 / 528 / 544 / 555 / 579, mean 554 (SD 67). The mean
winner's Elo outcome is therefore about 0.777, the loser's about 0.223; a typical league episode
moves the outcome by about ±0.28 from a draw.

### Result: glory composition of the winning team (mean per win, n = 80)

| Part | Mean | Share of wins with any |
| --- | ---: | ---: |
| Start | +600.0 | |
| Countdown | −88.2 | |
| Quiet supplies | +3.0 | 20% |
| Glory hearts | +15.5 | 56% |
| Behind in lives | +16.0 | 34% |
| Behind in cogs | +7.9 | 16% |
| Friendly-fire glory | 0 | (not in rules 47) |
| **Final** | **554.2** | |

Speed carries nearly all of it: countdown is −88 on average; all awards together +42.

### Result: per winning policy, and mean Elo outcome per champion

Leaderboard from `pw.py leaders --top 10 --json` (round 2388, completed 22:58 UTC).

| Policy (leaderboard rank, MMR) | W-L | Mean Elo outcome (all 20 eps) | Median win | Winner glory: countdown / quiet / hearts / behind lives / behind cogs | Mean winning glory |
| --- | --- | --- | ---: | --- | ---: |
| aaron-coplay-coach:v8 (1, 1820) | 16-4 | 0.68 ± 0.10 | 91 s | −103 / 1.3 / 20.0 / 48.4 / 17.5 | 584 |
| daveey-pw-neural:v26 (2, 1799) | 16-4 | 0.66 ± 0.10 | 74 s | −81 / 12.5 / 7.5 / 1.3 / 1.3 | 542 |
| aaron-paintbot-pw:v42 (3, 1796) | 16-4 | 0.64 ± 0.12 | 83 s | −92 / 0 / 15.0 / 14.7 / 4.4 | 542 |
| daveey1-jevbot-v2:v14 (4, 1676) | 10-10 | 0.50 ± 0.12 | 80 s | −80 / 2.0 / 16.0 / 1.0 / 9.0 | 548 |
| zhar:v1 (5, 1640) | 14-6 | 0.61 ± 0.11 | 89 s | −83 / 0 / 18.6 / 5.7 / 3.6 | 544 |
| relh-paintbot-pw:v1 (6, 1573) | 3-17 | 0.31 ± 0.09 | 85 s | −78 / 0 / 6.7 / 33.3 / 20.0 | 582 |
| richard-paintbot-pw:v1 (7, 1571) | 5-15 | 0.37 ± 0.11 | 90 s | −88 / 0 / 24.0 / 12.0 / 12.0 | 560 |
| paintbot-pw-basic-v22:v1 (8, 1485) | 0-20 | 0.23 ± 0.00 | - | - | - |

(± = normal-approximation 95% half-width from the scout report.) Note zhar ranks below jevbot on
MMR but out-scored it here (14-6, 0.61 vs 10-10, 0.50, and 2-0 head to head): the MMR carries
older rounds.

The neural policy is the only one that earns quiet-supplies glory at a real rate (12.5/win): it
takes almost no pickups (medkit 0.2, grenade 1.4 per episode vs about 15 grenades for the aaron
and base-derived policies), so its quiet stretches survive.

### Caveats

"Meter" wins are defined as wins without the loser eliminated; elimination fills the survivor's
meter first, so the meter columns cannot distinguish them. The per-policy composition rows for
relh and richard rest on 3 and 5 wins.

---

## 4. Contested captures

### Method

`captures` rows with `kind in (contest_start, contest_end)` and `seats.contested_reach_ticks`,
all 80 league episodes; the same on the 6 local base-vs-base games from §6. Engine:
`examples/paintbot/mechanics.nim:331-352` at `coworld-v0.3.79`. Tools: `pw_trace.nim:451-452`
(emits `contest_start/_end` when the engine's `heartCaptures[k].contested` flag changes),
`pw_trace.nim:483-489` (`contestedReachTicks`), `pw_metrics.py:403`.

### Result

| Data | Contest starts | Episodes with any | Total contested time | Capture starts (for scale) |
| --- | ---: | ---: | --- | ---: |
| League, 80 episodes | **12** | **9 of 80** (11%) | 227 heart-ticks (9.5 s over all 80 matches); per contest 1-37 ticks, median about 20 ticks (under 1 s) | 1,253 |
| League, seat level | `contested_reach_ticks` 468 vs `heart_reach_ticks` 100,051 (0.47%) | | | |
| Local base vs base at 0.3.79, 6 games | **4** | 2 of 6 | `contested_reach_ticks` 118 vs 12,059 reach ticks | 211 |

Contested hearts in the league (engine heart index, not the scout's Ember-frame label): 9 (7 of 12), 4 and 5 (2 each), 8 (1).

### Engine logic

A heart is contested when a living cog of **each** team is within **140 units** of it with a
traversable line (`touching[0] and touching[1]`, `mechanics.nim:333-338`). While contested,
nothing changes: the capture progress freezes (`continue` at `:339`) and ownership does not
move. Everything else is two-team exclusive: the lone team in reach either advances its
capture or, if it already owns the heart, clears any enemy progress.

### Verdict: genuinely rare, not a detection gap

The trace reads the engine's own `contested` flag every tick, so it cannot miss a contest. The
state is rare because it needs two enemies inside 140 units of the same point at once, while
guns reach 5,250 units: fights resolve long before both sides stand on the heart, and when both
do, one usually dies within a second. 12 contests in 80 games means 11% of episodes have one;
the probability of seeing none in 15 episodes is about (1 − 9/80)^15 ≈ 0.17, so the fights
agent's 0-in-15 is consistent with this rate.

**One small real gap, in the metric not the trace:** `pw_metrics.py:403` counts
`contests` as `contest_start` rows whose `team` equals the capturing team. When a contest starts
with no capture in progress (a defender and an attacker both arrive before any progress), the
engine's capture team is −1 and the row's `team` is null, so it is counted for **neither** team.
That was 3 of the 12 league contests (25%). The `base vs base contests = 0` reading may also
simply be a small sample (4 contests in 6 local games here).

### Caveats

The "fights resolve at range" explanation is an inference from geometry and the 140/5,250
numbers; it was not measured directly (e.g. by distance-to-heart at the kill).

---

## 5. Leaders' profiles (who does what)

### Method

`pw.py scout report …` (profiles in the scout report; hearts in Ember's frame: h0 own home,
h1 enemy home), plus SQL checks on the shout protocols (`shouts` joined to `states` and
`pickups`). Base-derived identification by shout text against `reference/base.bas:438-443,662`
and `reference/jev.bas`.

### Lineages

| Lineage | Policies | Evidence |
| --- | --- | --- |
| aaron custom | aaron-coplay-coach:v8, aaron-paintbot-pw:v42 | identical shout protocol (`FIRE22`, `ITEM23`, "Fanning out to objectives.") and identical openings |
| neural | daveey-pw-neural:v26 | silent, gun only |
| jev.bas derivative | daveey1-jevbot-v2:v14 | jev squad relay shouts ("Alpha, carry on.", "Bravo, carry on.") plus base shouts |
| base.bas derivatives | zhar:v1, richard-paintbot-pw:v1, relh-paintbot-pw:v1 | exactly base.bas's shouts ("Moving with the squad.", "Contact! Cover this lane.", "Grenade out!") and the same armor-first opening |
| older system starter | paintbot-pw-basic-v22:v1 (leaderboard label "paintbot-pw-basic-r22", no owner) | different shout set ("Moving on the flank.", "Holding high ground.") |

### Profiles (per episode unless noted; 20 episodes each)

| | aaron-coplay-coach:v8 | daveey-pw-neural:v26 | aaron-paintbot-pw:v42 | zhar:v1 | daveey1-jevbot-v2:v14 | richard / relh (base-like) | basic-v22 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| First capture started | h6 12, h4 8 | **h5 20/20** | h6 13, h4 6, h9 1 | h4 12, h9 8 | **h4 20/20** | h4/h9 split | **h9 20/20** |
| Usual capture order | h6 > h4 > h2 (11), h4 > h6 > h2 (6) | h5 only (15/20) | h6 > h4 > h2 (11) | h4 > h8 > h6 (6) | h4 > h6 (5) | h4 > h9 > h8 | varied |
| First walk target | own home h0, then field | field / h0 | h0, field | **armor #8** (3.75 seats), grenade #2 | **armor #8** (3.15 seats) | armor #8, h0, grenade #2 | h9, h8 |
| First capture, median | 12 s | **51 s** | 12 s | 16 s | 15 s | 13 / 11 s | 9 s |
| Hearts held (mean) | 3.53 | **1.34** | 3.62 | 3.17 | 2.24 | 3.36 / 3.25 | 4.15 |
| HP share gun / grenade / spray | 97 / 2.4 / 0.2% | **100 / 0 / 0%** | 97 / 2.4 / 0.9% | 96 / 4.1 / 0.1% | 99 / 0.3 / 0.3% | 94 / 4 / 2% | 91 / 6 / 3% |
| Gun accuracy, shots | 37%, 265 | 36%, 282 | 39%, 252 | 36%, 224 | 40%, 211 | 37% / 33%, 199 | 27%, 174 |
| Grenades thrown (% hurting an enemy) | 2.4 (40%) | 0 | 3.0 (38%) | 4.6 (35%) | 0.3 | 3.8 / 3.5 | 2.8 (46%) |
| Spray bursts (% effective) | 0.3 | 0 | 0.5 (80%) | 0.1 | 0.7 (14%) | 0.7 / 0.6 | 0.8 |
| Pickups: grenade / spray / medkit / armor / uniform | 15.1 / 1.8 / 3.0 / 3.1 / 1.6 | **1.4 / 0.5 / 0.2 / 1.7 / 0.1** | 15.2 / 2.0 / 3.5 / 3.4 / 1.4 | 15.1 / 1.5 / 6.5 / 2.7 / 0.7 | 1.4 / 1.6 / 3.2 / 2.6 / 0.5 | 11.8 / 1.5 / 4 / 2.3 / 1.1 | 10.7 / 2.2 / 4.5 / 1.9 / 0.7 |
| K/D; engagements won; opening duels won | 1.24; 51%; 76% | **1.53; 62%**; 68% | 1.38; 52%; **77%** | 0.95; 50%; 53% | 0.91; 43%; 61% | 0.74 / 0.61 | 0.42 |
| Median win / loss time | 91 / 108 s | **74** / 104 s | 83 / 142 s | 89 / 101 s | 80 / 80 s | 90, 85 / 80, 86 s | - / 71 s |
| Shouts per seat-minute | 16.6 | 0 | 16.5 | 3.1 | 9.2 | 3.1 / 2.9 | 2.7 |

### Shout protocols decoded

| Template | Who | Meaning (verified) |
| --- | --- | --- |
| `FIRE22 <x> <z>` | both aaron policies (about 170 per episode) | **enemy position call-out**. The coordinates equal the shouter's own aim point at that tick in 1,112 of 1,112 sampled shouts, the shouter is firing (`cmd_shoot = 1` in all), and a living enemy is within 150 units of the point in 96% (median 28 units). `22` is a constant message-type tag. Only 4-5% are heard by an enemy. |
| `ITEM23 <k>` | both aaron policies (about 21 per episode) | **"I just took pickup k"**: in 845 of 845 the shouter took pickup `k` within 2 ticks before the shout. Kinds: 594 grenade, 126 armor, 125 medkit. Presumably tells teammates the item is on cooldown. |
| "Fanning out to objectives." / "Retrieving supplies." / "Claiming this heart." | aaron | plain-text status lines (tick 1 fan-out; supply trips; claims) |
| "Alpha/Bravo, carry on." | jevbot | jev.bas squad relay (the squad voice repeats the current directive) |
| "Moving with the squad." / "Contact! Cover this lane." / "Grenade out!" | base.bas and its three derivatives, jevbot | base.bas flavour lines; "Grenade out!" is heard by enemies 93-100% of the time (it is shouted in grenade range) |

Opponents cannot exploit `FIRE22` much: 95%+ of these shouts are out of enemy earshot. The ITEM
tag does leak pickup timing to any enemy within 12.8 m, but 0% were heard by enemies.

### Takeaways

- The top three are built very differently. The neural policy barely captures (first capture
  51 s, 1.3 hearts held), never throws grenades and takes almost no pickups, yet has the best
  K/D (1.53), the best engagement win rate (62%) and the fastest wins (74 s median): it wins by
  killing, which ends matches by elimination.
- Both aaron policies take the h6 > h4 > h2 flank chain with 15 grenade pickups per episode
  and a team fire-call protocol; they win the most opening duels (76-77%).
- Every base.bas derivative goes for armor #8 first; base.bas itself is last-tier here.

### Caveats

Opening and capture labels are the scout's heuristics (radius thresholds listed in the report).
Shout decoding used `states`, which is sampled every 6 ticks (`state_every 6`), so the FIRE
check covers 1,112 of 6,757 FIRE shouts (the ones landing on a sampled tick).

---

## 6. Friendly fire and disguises

### Method

League: `q6.py` over `damage` (friendly = same true team, excluding self-damage), disguise
intervals per seat rebuilt from `events` `disguise_on` / `disguise_off`, and per-seat
`disguised_ticks` / `alive_ticks`. Local: wrote the instrumented copy with
`uv run python paintbot_pw_lab/reference/wire_intent_base.py paintbot_pw_lab <scratch>/base_intent.bas`,
recorded `uv run python paintbot_pw_lab/tools/pw.py intent record <scratch>/base_intent.bas paintbot_pw_lab/reference/base.bas --seeds 1-6 --out <scratch>/intent_eps --json`
(12 recordings, league glory config, 0 failures, no disabled seats), audited with
`pw.py intent audit … --out <scratch>/intent_audit --json`, then
joined every `target_is_ally` line (seat s aims at an identity that is really a disguised
teammate) to that seat's commands and `damage` rows over the next 24 ticks (`q6b.py`).

The instrumented policy issues the same commands as base.bas, so each seed's two recordings
(a0, a1) are the same game with prints on the other team; totals for the game use a0 only (6
unique games).

### League result (80 episodes)

| Policy | FF hits / ep | FF share of all HP it dealt | FF kills / ep | FF hits on **disguised** teammates (of all FF hits) | FF weapon mix |
| --- | ---: | ---: | ---: | --- | --- |
| aaron-coplay-coach:v8 | 3.4 | 3.7% | 1.45 | 18 of 68 | gun 58, grenade 9, spray 1 |
| aaron-paintbot-pw:v42 | 2.8 | 2.9% | 0.80 | 11 of 57 | gun 49, grenade 7, spray 1 |
| daveey-pw-neural:v26 | 7.2 | 6.6% | 1.95 | 1 of 143 | gun 143 |
| daveey1-jevbot-v2:v14 | 4.8 | 5.6% | 1.20 | 8 of 97 | gun 95, spray 2 |
| zhar:v1 | 7.8 | 8.7% | 1.55 | 5 of 157 | gun 149, grenade 8 |
| richard-paintbot-pw:v1 | 7.6 | 9.5% | 1.95 | 7 of 153 | gun 140, grenade 11, spray 2 |
| relh-paintbot-pw:v1 | 7.1 | 11.0% | 1.85 | 14 of 142 | gun 131, grenade 8, spray 3 |
| paintbot-pw-basic-v22:v1 | 9.3 | 15.5% | 2.20 | 10 of 186 | gun 184 |
| **All** | 6.3 per team-episode | 7.1% (1,003 FF vs 13,175 enemy hits) | | **74 of 1,003** (66 by gun) | |

Disguise exposure, all seats: 144 disguises in 67 of 80 episodes, 4,986 disguised seat-ticks
of 1,924,413 alive seat-ticks (0.26%).

| Hit rate per alive tick | While disguised | While not disguised | Ratio |
| --- | ---: | ---: | ---: |
| Hit by a **teammate** | 74 / 4,986 = 0.0148 | 929 / 1,919,427 = 0.00048 | **about 31×** |
| Hit by an **enemy** | 15 / 4,986 = 0.0030 | 13,160 / 1,919,427 = 0.0069 | about 0.44× |
| Hit by anyone | 0.0178 | 0.0073 | about 2.4× |

A disguised cog in the league is hit by its own team five times as often as by the enemy (74
vs 15). The HP it saves from enemies it more than loses to teammates.

### Local base.bas result (6 unique games, base vs base, 0.3.79)

| | Value |
| --- | --- |
| FF hits per game (both teams) | 17.8 (107 total), 8.7% of all hits, 27 FF kills (4.5 per game) |
| FF hits on disguised teammates | 5 of 107 (disguised 957 of 168,667 alive seat-ticks: about 9× the undisguised FF rate) |
| Intent lines aiming at a disguised teammate (`target_is_ally`) | 39 lines (of 9,052 with a target), in 11 distinct (seat, teammate) cases across 4 games |
| Of those lines: a shoot command on the next tick | 7 of 39 |
| Of those lines: a hit on that teammate within 24 ticks | **6 of 39**, in 3 of the 11 cases (1-3 HP each) |
| Consistency divergences in the audit | 0 (the telemetry and joins are sound) |

**Answer: yes, base.bas does fire on disguised teammates it targets, and hits them.** In 3 of 11
target-a-disguised-teammate episodes the shots landed. It is not the main source of base.bas
friendly fire (5 of 107 FF hits); most FF is ordinary crossfire, which base.bas's "clear line"
check (`intR = 7`, teammate in the line of fire) does not prevent.

### Takeaways

- **Uniforms are a net liability in this field**: a disguise roughly triples a cog's hit rate,
  almost all from its own team. The base-derived policies and aaron pick up 0.7-1.6 uniforms
  per episode; the neural policy 0.1.
- The aaron pair has the lowest FF (3% of HP), yet the largest share of its FF on disguised
  teammates (25% and 19%): its fire discipline handles crossfire but not disguises.
- Our policy should (a) never pick up uniforms unless it tracks its own disguised teammates, and
  (b) treat an "enemy" at a teammate's last known position as suspect (a disguised body answers
  to `slot xor 1`).

### Caveats

FF counts are damage events past shields; `hp_removed` is about 1 per hit, so hits and HP are
nearly the same numbers. The disguise-interval join treats a hit on the tick the disguise ends
as disguised. The disguised hit-rate ratio is not adjusted for where disguised cogs are (they
are likely nearer fights), so treat 31× as an upper-range figure. The per-policy split of disguised-victim hits by attacker team was not computed.

---

## 7. Heartwick pickup layout by kind

### Method

`uv run python paintbot_pw_lab/tools/pw.py map --rules 48 --json` (the engine-built `pw_map`,
which reads `w.pickups[k].kind` from the world, `tools/pw_map.nim:87`; cache
`tools/.cache/maps/coworld-v0.3.79/heartwick-r48-s25.json`), cross-checked against every take in
the 80 league traces (`pickups.pickup_kind` is also read from the engine per take).

### Result: **verified, 2 uniforms / 4 grenades / 2 sprays / 2 armors / 6 medkits** (16 pickups, 6 trenches, 10 hearts)

| idx | Kind | Position (x, z) | League takes (80 eps) |
| ---: | --- | --- | ---: |
| 0 | uniform | 2000, 1000 | 77 |
| 1 | uniform | 4400, 3000 | 67 |
| 2 | grenade | 300, 300 | 465 |
| 3 | grenade | 6100, 3700 | 472 |
| 4 | grenade | 300, 3700 | 343 |
| 5 | grenade | 6100, 300 | 370 |
| 6 | spray | 600, 1000 | 137 |
| 7 | spray | 5800, 3000 | 115 |
| 8 | armor | 600, 3000 | 201 |
| 9 | armor | 5800, 1000 | 199 |
| 10 | medkit | 3200, 1333 | 98 |
| 11 | medkit | 3200, 2667 | 105 |
| 12 | medkit | −1700, 2000 | 80 |
| 13 | medkit | 8100, 2000 | 71 |
| 14 | medkit | 3200, −650 | 127 |
| 15 | medkit | 3200, 4650 | 123 |

Every pickup index had exactly one kind across all 3,050 league takes. Pairs are point-mirrored
through the map centre (3200, 2000). mechanics.md §5 can drop "inferred" for the per-kind split.

---

## 8. base.bas budget peaks at 0.3.79

### Method

```sh
PW_BASIC_PEAKS=1 paintbot_pw_lab/tools/bin/coworld-v0.3.79/paintbot-headless \
  --bot paintbot_pw_lab/reference/base.bas:16 --seed S --ticks 14400 \
  '--glory:{"behind_lives":5,"behind_cogs":10}'
```

for seeds 2026 and 1-10, the same for `reference/jev.bas` (results in
`<scratch>/peaks.txt`). Printed per-seat
`peak_instructions`, `peak_work`, `peak_strings` (the arrays are padded to 256 seats; the first
16 are real). Max over the 16 seats per run.

### Result

| Policy ×16 | Runs | Peak instructions: max (range of per-run max) | % of 50,000 | Peak work units: max (range) | % of 125,000 | Peak string handles |
| --- | ---: | --- | ---: | --- | ---: | ---: |
| base.bas | 11 | **9,116** (8,662-9,116) | 18% | **15,538** (14,769-15,538) | 12% | 2 |
| jev.bas (no oracle) | 11 | **13,909** (13,188-13,909) | 28% | **21,140** (20,050-21,140) | 17% | 3 |

Match lengths were 1,989-4,615 ticks (all ended by elimination). jev.bas without an oracle plays
the **identical** match to base.bas (same ticks and same hash, e.g. seed 1 `hash=3363981069` for
both), as the engine's own test requires; it just spends about 50% more instructions doing it.

### Answer and doc findings

base.bas uses under a fifth of the instruction budget and an eighth of the work budget at its
worst decision: about 40,000 instructions and 110,000 work units of headroom per decision.

- **Stale number:** `docs/policy-surface.md` says "`base.bas` peaks near 5,670 instructions and
  8,722 work units (guide line 720; not re-measured here)". At 0.3.79 the measured peaks are
  9,116 / 15,538, about 1.6-1.8× higher. The orchestrator should replace that line.
- The engine's `DEPLOYMENT.md` (around line 402) still quotes limits of 20,000 / 50,000 in its
  jev paragraph; the lab's 50,000 / 125,000 (`bots.nim:147-148`) is the current code, so the
  lab doc is right and that upstream note is old.

### Caveats

Headless runs have no oracle, so jev.bas's oracle-on peak (the upstream note says about
12,600 / 26,700 at an older version) was not measured. Peaks are per match on the local field
(base vs base); a policy's peak depends on how many cogs it sees, so a crowded league match could
run somewhat higher.

---

## Open follow-ups

1. One cheap hosted pilot to confirm §1: an XP request with `game_config_overrides.seed: S`
   and `num_episodes: 2`; expect identical `final_hash`.
2. Fix the `contests` metric (`pw_metrics.py:403`) to count contest starts without a capturing
   team (for example, attribute them to both teams or count per heart).
3. Update `docs/mechanics.md` §5 (pickup split verified), `docs/policy-surface.md` (base.bas
   peaks), and WORKING_CONTEXT (behind_cogs 10 observed live; league shows no side advantage;
   disguise cost measured).
