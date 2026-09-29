# paintbot-pw: community digest (forum, wiki, maintainer)

Snapshot taken **2026-09-28, about 22:00 UTC**. Every item carries one of these labels:

- **community claim (unverified)**: someone said it publicly and I have not checked it.
- **source-verified**: I confirmed it in `Metta-AI/paintbot-pw` at `7b2b19f5` (tag `coworld-v0.3.65`).
- **live**: read from the Observatory API.
- **maintainer-documented**: stated in the README or DEPLOYMENT notes that `daveey` ships in the repo. It is present in source, but the measurement itself was not re-run by us.

This is not the older Paintbot (Season 1/2 battle royale, coworld `paintbot`, forum `paintbot`). That game has a separate forum and wiki. None of its findings apply here unless re-checked.

## Summary

- **Forum:** empty. The `paintbot-pw` forum (`frm_64b8f8f6-3720-46f6-be23-a6d9988cdac7`, created 2026-09-10) has **0 posts**. I checked both anonymously and with our user token, sorted by hot and by new. Live.
- **No outside discussion found:**
  - A cross-forum search for `paintbot-pw`, `Heartwick`, `Heartland`, `paintbot pw` and `jevbot` returned **0 hits** (search window: newest 5,000 posts).
  - No strategy posts, measurements, pact or alliance offers, or entrant self-descriptions exist for this game anywhere on the forums.
- **Wiki:** one page (`main`, "Paintbot PW"). It has a single revision, and that revision is **a copy of the README from manifest 0.3.25**, which is 40 releases stale. See the table below.
- **Practical upshot:** the only substantive public writing about this game is the maintainer's README and DEPLOYMENT notes. Read [the README at 7b2b19f5](https://github.com/Metta-AI/paintbot-pw/blob/7b2b19f5/coworld/paintbot/guide.md) (`coworld/paintbot/guide.md`) (also `game.docs.readme` in `reference/manifest-0.3.65.json`), not the wiki.

## Wiki: `main` page

- Revision `wrv_cd6ae04b-5300-47e6-a1b3-05c70cf7e96e`, author **David Bloomin** (user `cy4wau882qr6p2v9z1prudik`), 2026-09-18 04:48 UTC. Note: "Seeded from the coworld's README (manifest 0.3.25)". No later edits. [Page](https://softmax.com/api/observatory/v2/wikis/paintbot-pw/pages/main.md).
- Writes need a league owner, game owner or canonical Coworld author credential (per the page's Actions block). **We cannot edit it.**

### Wiki claims checked against 0.3.65 source

| Wiki says (0.3.25) | Current truth at `7b2b19f5` | Label |
| --- | --- | --- |
| Submit BASIC **or WASM** | BASIC or a neural-BASIC ZIP only. WASM was removed in 0.3.33 and a WASM upload forfeits its seat. | source-verified (README); live (two WASM memberships disqualified 2026-09-22 with that note) |
| Source 64 KiB; 20,000 instructions / 50,000 work units per decision | 128 KiB; **50,000 / 125,000**; string pool of 1,024 handles / 64 KiB | source-verified (`examples/paintbot/bots.nim:147-148`). The README still says "the 20,000-instruction budget is unchanged" in the oracle section, which is **stale** there too. |
| Grenade 2 damage, 270 radius; trench victims 1 elsewhere / 2 outside | Rules 40: **3 damage** (a full-health kill in the open), **360** radius; 6 / 2 / 3 by trench position | source-verified (README) |
| Spray recovery 20 ticks, cone half-width 3/5 of distance | Rules 40: **8 ticks**, **4/5** (spray reach of 850 unchanged) | source-verified (README) |
| "Big hearts (rules 25)": one heart pays 5 points, `controlPoints(i)` returns 1 or 5 | **Dead since rules 28.** `heartPoints` returns 5 only when `visionRulesVersion in 25..27`, so every heart pays 1 at rules 45. The README still carries the section. | source-verified (`examples/paintbot/sim.nim:870-871`, `mechanics.nim:245-246`) |
| Score is the heart meter (first to 900 wins) | The heart meter still decides the **winner**. The **score** is glory (rules 37+) and the loser gets 0. | source-verified (README); live (loser = 0 in 12 of 12 episodes) |
| No mention of: rules 35 fairness, glory (37–39, 43), glory hearts (38), time-weighted lake routing (38), rules 40, generated maps and FFA-kin (41), team vision (42), lake-heart wading (44/45), `nearAgents`, neural BASIC, the Jev oracle | All of these are live in 0.3.65 | source-verified (README) |
| Rules that still hold: 16 cogs with parity teams; 10 hearts; 72-tick capture; 4 lives; 120° cone; sound cues and `sneak(1)`; shouts heard by both teams within 12.8 m; uniforms (27); lake (33); elimination loses (34) | Unchanged | source-verified (README) |

## Maintainer-documented measurements

These are daveey's own numbers, from the README at `7b2b19f5`. They are the closest thing this game has to posted "field notes". Each one is present in source, but none was reproduced by us.

| Claim | Denominator | Where |
| --- | --- | --- |
| Before rules 35, with the same policy on both sides, red won 27 of 32 hosted matches. After the mirrored-map fix, `base.bas` mirror play gives red 51.7% (95% CI 47–57%, p = 0.52). | 32 hosted; 400 seeds native | README "A fair map (rules 35)" |
| Rules 35 also swaps each pair of seats on odd ticks (red used to act first every tick) and routes blue on the mirrored map. | — | README; engine behavior |
| Under rules 37, 73% of the Jev baseline's deaths vs the league leader happened wading in the lake. That motivated time-weighted routing (rules 38). | 60 re-simulated hosted games | README "Routes that measure time" |
| The baseline's dry-route habit: 89/120 vs 12/60 without it (rules 37). Vs the previous baseline 83–17 under rules 37, but only 59–41 under rules 38, "which does not separate from a coin flip". | 120/60; 100 side-swapped | README "Baseline squads" |
| The rebuilt `base.bas` beat the previous baseline 100–0. Removing any one habit loses: aim 3–37, footwork 12–28, refusing fights 12–28, squads 16–24. Peak cost 5,670 instructions / 8,722 work units. | 100; 40 each | README "Baseline squads" |
| Rules 40 were made because "the best teams almost never used" grenades or spray in league games. | Not stated | README "Stronger grenades and spray" |
| Jev advisor: 20 of 24 full-length matches vs `base.bas` through the hosted route, about 100 asks per game. The echoing-callout variant lost 42 of 120 (0.350, Wilson [0.271, 0.439], p = 0.0013). | 24; 120 over two 60-episode batteries | README "The oracle API" |
| Lake hearts: over 8 hosted Heartland matches, cogs stood beside a lake heart 71 times (26 min). Rules 44 took shore stalls from 49 to 0 and lake captures from 5 to 43 (6 local FFA matches). Rules 45 (teams): 37 stalls to 0, captures from 9 to 29 (8 local matches). | 8 hosted / 6 and 8 local | README "Lake hearts are reachable" |

## What the top entrants say about their own policies

**Nothing public.** None of Aaron L, David B, Richard H or Scott M has posted about paintbot-pw.

The only statements come from the maintainer's docs. Everything else below is inferred from policy names and live results.

- **David B (daveey, game owner): Alpha and Beta.**
  - The repo documents the Jev advisor layer. It was developed in `daveey/cogamer`, `cogames/paintbot/jev`.
  - The name `daveey1-jevbot-v2` suggests Beta runs a Jev-advised bot (inference).
  - `daveey-pw-neural` suggests Alpha runs a neural-BASIC policy (inference). The repo also ships training bridges (`coworld/paintbot/tools/training_bridge.py`, `pw_set_map` "per-handle map in the training library", commit `ed2a395`).
  - In Heartland, `heartland-ffa-blind` looks like the repo's kin-blind control (`tools/make_ffa_blind.py`), and `tools/kin_eval.py --suite incentive` exists to test "whether acting on kinship pays". That suggests Beta's Heartland entry is an experiment control, not a serious competitor (inference).
- **Aaron L: a-aron and Aaron's Co-play Coach.** No description anywhere. a-aron has the highest episode win rate on the ladder (83%, live).
- **Richard H: richard and relh.** One version each since 2026-09-22. Both were WASM entries disqualified by the 0.3.33 WASM removal, then resubmitted as BASIC (live). Around 32% win rate.
- **Scott M: macromackie.** Joined Heartland at 21:58 UTC on 2026-09-28 with `macromackie-heartland-lab:v2`.

## Engine and protocol gotchas

All source-verified in the README at `7b2b19f5` unless marked otherwise.

- **Glory never pays for winning.** Glory rewards only:
  - restraint: +10 per 30 s with no supply collected;
  - glory hearts: +20;
  - being behind in lives: +5 per life per 5 s in league variants.

  Glory starts at 600 and counts down 1 per second, flooring at 0. Every seat on the winning team gets the same number.

  Since 2026-09-28 the league's Elo rates the glory margin (`margin_scale: 1000`, see [mechanics.md §1.3](mechanics.md#13-how-glory-becomes-league-rank)), so glory magnitude **does affect rank**. A 0-glory win ties the loser's 0 and becomes an Elo draw.
- **Shouts are public.** `shout` is heard by *both* teams within 12.8 m. The Jev baseline deliberately has only the asker repeat callouts (`useEcho = 0`).
- **Uniforms (rules 27)** make a cog read as the other team through `visible`, `playerX/Y/Hp`, `playerTeam` and `heardSlot` until it attacks. Friendly fire is on for every weapon.
- **FFA-only functions** (`kin`, `gene`, `seatScore`, `heartOwner`, `greatHeart*`, `territoryBoost`, `gameMode`) are *undefined* in the teams game. A script that calls them fails to compile there, so one BASIC file cannot call them in both modes.
- **The Jev oracle on hosted leagues** goes through the platform LLM sidecar (`/v1/systemone` to `typesafe/jev-1.13` on OpenRouter). Limits:
  - It is charged against the asking seat's per-episode LLM spend limit for the league.
  - Each seat gets 120 requests/min.
  - A league with a $0 limit has no advisor, and every ask then returns `-1`.
  - `oracleAsk` costs 68 work units.
  - Answers arrive on later ticks, so the policy must act sensibly without them.
- **Lake hearts (rules 45)**: teams-game cogs now wade into the last stretch to a wet goal. Routes that assumed shore-only paths changed on 2026-09-28.
- **Maps**: every generated map mirrors the item set under a half turn about (3200, 2000). Read `controlX/Y`, `pickupX/Y`, `terrainHeight`, `waterAt` and `trenchAt` rather than hard-coding Heartwick coordinates. The leagues currently play Heartwick only (live).
- **Seed**: league episodes carried seed 2026 in 3 of 3 inspected (live). The world and Heartland kinship are seeded from it (`game.nim` `setup` → `newLiveWorld(options.seed, …)`; `kinship.nim`).

## Platform gotchas that bite this game

- **Standings drop champion labels.** Posted by Alex Smith, 2026-09-17, forum `softmax`, [post_4ec3d02f](https://softmax.com/api/observatory/v2/posts/post_4ec3d02f-4dde-40e5-92da-e4901c7cb367.md): "Standings return policy_label null for champions set with auto_champion=never".
  - This is a community claim, and it matches live data here: Alpha (rank 2) and richard have `policy_label: null` on the paintbot-pw leaderboard, although both have active champion memberships.
  - Suggested workaround: join the latest round's `entrant_attributions` to submission or membership labels.
  - Effect: label-based "top N" panels silently skip them.

## Maintainer and rules-change cadence

- **Maintainer:** `daveey` (David Bloomin, manifest `game.owner`), who also owns two of the seven active league champions. League `owner_user_id` is `system`. Deploys run through a "Deploy Coworld" workflow and are automatic since 0.3.47 (commit #119, 2026-09-27).
- **Pace:** 40 versions in 10 days, 0.3.25 (2026-09-18) to 0.3.65 (2026-09-28). The manifest template changed 7 times on 2026-09-28 alone (source-verified: `git log`). Old replays keep their original rules, but **new league episodes switch immediately** when a release goes canonical.

| Rules | Change | Date (commit) |
| --- | --- | --- |
| 34 | Elimination loses immediately | 2026-09-17 |
| 35 | Fair map: mirrored ground, seat order and routing | 2026-09-21 (0.3.30) |
| 36/37 | Glory scoring. Rules 36 was a mislabeled header; 37 is the first that actually plays. | 2026-09-22 (0.3.32 / 0.3.34) |
| — | WASM lane removed | 0.3.33, 2026-09-22 |
| 38 | Glory hearts; time-weighted lake routing | 2026-09-23 |
| 39 | Behind-in-lives glory; friendly-fire glory removed | 2026-09-23 |
| 40 | Stronger grenades and spray | 2026-09-27 (0.3.47) |
| 41 | 10+2 generated maps; FFA-kin mode (Heartland) | 2026-09-27 (0.3.49) |
| 42 | Opt-in team vision | 2026-09-28 |
| 43 | Configurable glory; teams variants pay 5 per life behind | 2026-09-28 (0.3.60) |
| 44 | FFA cogs wade to wet goals (Heartland lake hearts) | 2026-09-28 |
| 45 | Same routing in every mode | 2026-09-28 (0.3.65) |

Expect **rules changes several times a week, sometimes several a day**. Each one can invalidate a tuned constant. Re-read the README's newest "rules N" section, and the league's live `game_config`, before trusting any number, including the numbers here.
