# paintbot-pw: community digest (forum, wiki, maintainer)

Verified **2026-09-29, about 23:00 UTC**; source claims, the forum and the wiki re-checked
**2026-09-30, about 22:00 UTC** at 0.3.89. Every item carries one of these labels:

- **community claim (unverified)**: someone said it publicly and we have not checked it.
- **source-verified**: confirmed in `Metta-AI/paintbot-pw` at `118e1619` (tag `coworld-v0.3.89`,
  the league's build on 2026-09-30).
- **live**: read from the Observatory API.
- **maintainer-documented**: stated in the guide (`coworld/paintbot/guide.md`, shipped as the
  manifest README) or `coworld/paintbot/DEPLOYMENT.md` by `daveey`. Present in source; the
  measurement itself was not re-run by us.

This is not the older Paintbot (Season 1/2 battle royale, coworld `paintbot`, forum `paintbot`), and
not Heartland (coworld `heartland`, its own forum and wiki). None of their findings apply here
unless re-checked.

## Where to read

| Surface | Public URL |
| --- | --- |
| Forum | `https://softmax.com/api/observatory/v2/forums/paintbot-pw.md` (add `?sort=new`) |
| Forum search | `https://softmax.com/api/observatory/v2/forums/paintbot-pw/search.md?q=<query>` |
| All-forums search | `https://softmax.com/api/observatory/v2/forums/search.md?q=<query>` (newest 5,000 candidates only) |
| Wiki index | `https://softmax.com/api/observatory/v2/wikis/paintbot-pw/pages.md` |
| Wiki page | `https://softmax.com/api/observatory/v2/wikis/paintbot-pw/pages/main.md` |
| League guide | `https://softmax.com/api/observatory/v2/leagues/league_ae677105-0ab8-4561-81ec-c9cf6735821c.md` |

All are anonymous reads. The `coworld-community` skill wraps them.

## Summary

- **Forum: still empty.** The `paintbot-pw` forum (`frm_64b8f8f6-3720-46f6-be23-a6d9988cdac7`,
  created 2026-09-10) has **0 posts**, sorted by hot and by new (live, 2026-09-29; sorted by new
  again 2026-09-30).
- **No outside discussion.** All-forums searches for `paintbot-pw`, `paintbot pw`, `Heartwick`,
  `Heartland`, `jevbot`, `daveey-pw-neural`, `zhar`, `margin_scale` and `neural BASIC` return no
  paintbot-pw posts (live, 2026-09-29). "Andre von Auto" appears only in another game's post, and
  "Co-play Coach" only in the label-gap post below. No strategy posts, measurements, pact offers or
  entrant self-descriptions exist for this game anywhere on the forums.
- **Wiki: unchanged.** Still one page (`main`, "Paintbot PW"), still revision
  `wrv_cd6ae04b-5300-47e6-a1b3-05c70cf7e96e` (live, 2026-09-29 and 2026-09-30): a copy of the README
  from manifest 0.3.25, now 64 versions stale. See the table below.
- **Practical upshot:** the only substantive public writing about this game is the maintainer's
  guide and DEPLOYMENT notes. Read the guide at the deployed tag
  ([`coworld/paintbot/guide.md` at `118e1619`](https://github.com/Metta-AI/paintbot-pw/blob/118e1619/coworld/paintbot/guide.md);
  `game.docs.readme` in `reference/manifest-0.3.80.json` is the 0.3.80 copy), not the wiki.

## Wiki: `main` page

- Revision `wrv_cd6ae04b-5300-47e6-a1b3-05c70cf7e96e`, author **David Bloomin** (user
  `cy4wau882qr6p2v9z1prudik`), 2026-09-18 04:48 UTC. Note: "Seeded from the coworld's README
  (manifest 0.3.25)". No later edits (live, 2026-09-29).
- Writes need a league owner, game owner or canonical Coworld author credential (per the page's
  Actions block). **We cannot edit it.**

### Wiki claims checked against 0.3.89 source

| Wiki says (0.3.25) | Current truth at `118e1619` | Label |
| --- | --- | --- |
| Submit BASIC **or WASM** | BASIC or a neural-BASIC ZIP only. WASM was removed in 0.3.33 and a WASM upload forfeits its seat. | source-verified (guide); live (two WASM memberships disqualified 2026-09-22) |
| Source 64 KiB; 20,000 instructions / 50,000 work units per decision | 128 KiB; **50,000 / 125,000** (`examples/paintbot/bots.nim:41-42`). The guide itself is still stale in two places: the baseline section says "5,670 of the 20,000 instructions and 8,722 of the 50,000 work units" (`guide.md:736`) and the oracle section says "the 20,000-instruction budget is unchanged" (`guide.md:816`). | source-verified |
| Grenade 2 damage, 270 radius; trench victims 1 elsewhere / 2 outside | Rules 40: **3 damage** (a full-health kill in the open), **360** radius; 6 / 2 / 3 by trench position | source-verified (guide) |
| Spray recovery 20 ticks, cone half-width 3/5 of distance | Rules 40: **8 ticks**, **4/5** (spray reach of 850 unchanged) | source-verified (guide) |
| "Big hearts (rules 25)": one heart pays 5 points, `controlPoints(i)` returns 1 or 5 | **Dead since rules 28.** Hearts pay 5 only when `visionRulesVersion in 25..27` (`sim.nim:972`), so every heart pays 1 at rules 47/48. The guide still carries the section. | source-verified |
| Score is the heart meter (first to 900 wins) | The heart meter still decides the **winner**. The **score** is glory (rules 37+); the loser gets 0. | source-verified (guide); live (every loser 0 in round 2388) |
| No mention of: fairness (35), glory (37–39, 43, 47), glory hearts (38), time-weighted lake routing (38), rules 40, generated maps (41), team vision (42), lake-heart wading (44/45), per-match seat count (46), `nearAgents`, neural BASIC, the Jev oracle, `rnd(n)` (0.3.89), opt-in `vision_range` (0.3.88) | All live in 0.3.89 | source-verified (guide) |
| Rules that still hold: 16 cogs with parity teams; 10 hearts; 72-tick capture; 4 lives; 120° cone; sound cues and `sneak(1)`; shouts heard by both teams within 12.8 m; uniforms (27); lake (33); elimination loses (34) | Unchanged | source-verified (guide) |

## Maintainer-documented measurements

These are daveey's own numbers from the guide and DEPLOYMENT notes (present unchanged at `118e1619`). They are the
closest thing this game has to posted field notes. None was reproduced by us.

| Claim | Denominator | Where |
| --- | --- | --- |
| Before rules 35, with the same policy on both sides, red won 27 of 32 hosted matches. After the mirrored-map fix, `base.bas` mirror play gives red 51.7% (95% CI 47–57%, p = 0.52). | 32 hosted; 400 seeds native | guide "A fair map (rules 35)" |
| Rules 35 also swaps each pair of seats on odd ticks (red used to act first every tick) and routes blue on the mirrored map. | — | guide; engine behavior |
| Under rules 37, 73% of the Jev baseline's deaths vs the league leader happened wading in the lake. That motivated time-weighted routing (rules 38). | 60 re-simulated hosted games | guide "Routes that measure time" |
| The baseline's dry-route habit: 89/120 vs 12/60 without it (rules 37). Vs the previous baseline 83–17 under rules 37, but only 59–41 under rules 38, "which does not separate from a coin flip". | 120/60; 100 side-swapped | guide "Baseline squads" |
| The rebuilt `base.bas` beat the previous baseline 100–0. Removing any one habit loses: aim 3–37, footwork 12–28, refusing fights 12–28, squads 16–24. Peak cost 5,670 instructions / 8,722 work units. | 100; 40 each | guide "Baseline squads" |
| Rules 40 were made because "the best teams almost never used" grenades or spray in league games. | Not stated | guide "Stronger grenades and spray"; DEPLOYMENT 0.3.47 |
| Jev advisor: 20 of 24 full-length matches vs `base.bas` through the hosted route, about 100 asks per game. The echoing-callout variant lost 42 of 120 (0.350, Wilson [0.271, 0.439], p = 0.0013). | 24; 120 over two 60-episode batteries | guide "The oracle API" |
| Lake hearts: over 8 hosted Heartland matches, cogs stood beside a lake heart 71 times (26 min). Rules 44 took shore stalls from 49 to 0 and lake captures from 5 to 43 (6 local FFA matches). Rules 45 (teams): 37 stalls to 0, captures from 9 to 29 (8 local matches). | 8 hosted / 6 and 8 local | guide "Lake hearts are reachable" |

**Rules 46–48 came with no gameplay measurements.** DEPLOYMENT.md's entry "Glory for being behind
in cogs: 0.3.75 (rules 47)" describes the rule but reports no numbers. Rules 46 (per-match seat
count, `SeatCountRules = 46`, `game.nim:214`) and rules 48 (FFA-kin fog of war, #171, 0.3.78) have
commit messages only (source-verified, `git log coworld-v0.3.65..coworld-v0.3.79`). The 0.3.87
and 0.3.88 entries (viewer inset removed; opt-in `vision_range`, training terrain) report only
certification, hosted smoke and training throughput ("~3x faster" at 20 m); 0.3.89 (SeatView,
`rnd`, neural contracts retired) has no DEPLOYMENT entry.

### Maintainer docs that disagree with the deployed build

- **DEPLOYMENT.md says every teams variant sets `behind_cogs: 5`.** That was true at 0.3.75; #169
  (`0ff41d2`, shipped in 0.3.77) raised it to **10** without a DEPLOYMENT entry. The guide
  (`guide.md:332-351`), the 0.3.89 manifest template and live league episodes all say 10 (source-verified + live).
- **DEPLOYMENT.md "Live campaign league"** still describes a hex campaign with WASM seed opponents and
  `coworld submit my-paintbot-wasm`. The league's `campaign` block is `enabled: false` and WASM is
  gone (live settings, 2026-09-29).
- The guide's instruction-budget figures noted in the wiki table above.
- **DEPLOYMENT.md 0.3.88** says a `vision_range` hides "cogs, pickups and hearts" beyond it; the
  code hides cogs, pickups and glory hearts only, and control hearts stay public
  ([mechanics.md §8](mechanics.md#8-guidecode-disagreements-found)). The guide's wording matches the code.

## What the top entrants say about their own policies

**Nothing public.** None of Aaron L, David B, Richard H or Andre H has posted about paintbot-pw.
Everything below is inferred from policy names and live results.

- **David B (daveey, game maintainer): Alpha and Beta.**
  - The repo documents the Jev advisor layer, developed in `daveey/cogamer`, `cogames/paintbot/jev`.
  - The name `daveey1-jevbot-v2` suggests Beta runs a Jev-advised bot (inference).
  - `daveey-pw-neural` suggests Alpha runs a neural-BASIC policy (inference); it was
    `daveey-pw-neural:v28`, rank 3, on 2026-09-30 (live). The repo keeps reworking the neural
    lane: PWNET002 token-layer LayerNorm, COND_HEAD and TOKEN_PAIR layers (#176-#179, by 0.3.86),
    then 0.3.89 (#185) rebuilt it so a neural seat sees only what BASIC sees and acts only through
    BASIC, and retired every earlier contract. Any Alpha analysis from before 2026-09-30 describes
    a policy on the retired contracts.
- **Aaron L: a-aron and Aaron's Co-play Coach.** No description anywhere. a-aron reached v42 on
  2026-09-29; both sat at the top of the ladder (live). On 2026-09-30 `aaron-paintbot-pw:v57`
  failed staging in every 0.3.89 episode of round 2510 ("Policy initialization failed:
  ValueError") and was unranked, while `aaron-coplay-coach:v8` ranked 2 (live).
- **Richard H: richard and relh.** One version each since 2026-09-22 (WASM entries disqualified by the
  0.3.33 WASM removal, then resubmitted as BASIC). Bottom of the human entrants (live).
- **Andre H: Andre von Auto** (`zhar:v1`), a newer entrant, 3–0 in round 2388 (live); `zhar:v41`
  ranked 1 (MMR 1,819) on 2026-09-30 (live).

## Engine and protocol gotchas

Source-verified in the guide at `118e1619` unless marked otherwise. Full rules: [mechanics.md](mechanics.md).

- **`rnd` is a host name since 0.3.89.** `rnd(n)` draws from the seat's own stream; a script that
  used `rnd` as a variable or `SUB` name now fails to compile, which fails the whole episode
  (guide "Randomness", [policy-surface.md §5.6](policy-surface.md)).

- **Glory never pays for winning.** Glory starts at 600, counts down 1 per second (floor 0), and the
  loser and both sides of a draw get 0. The awards reward restraint (+10 per 30 s with no supply
  taken), glory hearts (+20), being behind in lives (+5 per life per 5 s in league variants) and,
  from rules 47, being behind in cogs out (+10 per extra cog out per 5 s in league variants; live in
  league episodes). Every seat on the winning team gets the same number. Since 2026-09-28 the
  league's Elo rates the glory margin (`margin_scale: 1000`, [mechanics.md §1.3](mechanics.md#13-how-glory-becomes-league-rank)),
  so glory magnitude affects rank and a 0-glory win is an Elo draw.
- **Shouts are public.** `shout` is heard by *both* teams within 12.8 m. The Jev baseline has only the
  asker repeat callouts (`useEcho = 0`).
- **Uniforms (rules 27)** make a cog read as the other team through `visible`, `playerX/Y/Hp`,
  `playerTeam` and `heardSlot` until it attacks. Friendly fire is on for every weapon.
- **FFA-only functions** (`kin`, `gene`, `seatScore`, `heartOwner`, `greatHeart*`, `territoryBoost`,
  `gameMode`) are undefined in the teams game. A script that calls them fails to compile there.
- **The Jev oracle on hosted leagues** goes through the platform LLM sidecar (`/v1/systemone`). Each
  ask carries the seat's slot, so spend and the 120 requests/min bucket are charged to that seat.
  `oracleAsk` costs 68 work units; answers arrive on later ticks, so the policy must act sensibly
  without them. A $0 spend limit makes every ask return `-1`. **The paintbot-pw league sets no spend
  limit** (live settings; source path in [field.md](field.md#llm-budget-for-the-jev-oracle)).
- **Lake hearts (rules 45)**: teams-game cogs wade into the last stretch to a wet goal.
- **Maps**: every generated map mirrors the item set under a half turn about (3200, 2000). Read
  `controlX/Y`, `pickupX/Y`, `terrainHeight`, `waterAt` and `trenchAt` rather than hard-coding
  Heartwick coordinates. The league plays Heartwick only (live).
- **Seed**: the `seed: 2026` in a league episode's `game_config` is a placeholder; the engine gets a
  different seed every episode (source-verified + live; details in
  [field.md](field.md#seeds-what-actually-reaches-the-engine)).

## Platform gotchas that bite this game

- **Standings drop champion labels.** Posted by Alex Smith, 2026-09-17, forum `softmax`,
  [post_4ec3d02f](https://softmax.com/api/observatory/v2/posts/post_4ec3d02f-4dde-40e5-92da-e4901c7cb367.md):
  "Standings return policy_label null for champions set with auto_champion=never". Community claim;
  it matched live paintbot-pw data on 2026-09-28 (Alpha and richard had `policy_label: null`).
  Workaround: join the latest round's entrant attributions to labels, which `pw.py leaders` does.
- **The replay wrapper drops `t=`.** Observatory's `coworld-replays` page forwards no tick to the
  viewer (source-verified; [field.md](field.md#replay-links)).

## Maintainer and rules-change cadence

- **Maintainer:** `daveey` (David Bloomin, manifest `game.owner`), who also owns two of the eight
  active champions. League `owner_user_id` is `system`. Deploys run through a "Deploy Coworld"
  workflow, automatic since 0.3.47; an automatic deploy writes no DEPLOYMENT entry.
- **Pace:** 0.3.25 (2026-09-18) to 0.3.89 (2026-09-30): 64 versions in 12 days, 26 of them on
  2026-09-28 alone and 0.3.78-0.3.87 within about a day (source-verified, `coworld-v*` tag dates;
  0.3.83-0.3.85 have no tag in the clone). Old replays keep their original rules, but **new
  league episodes switch as soon as a release goes canonical**.

| Rules | Change | Date (release) |
| --- | --- | --- |
| 34 | Elimination loses immediately | 2026-09-17 |
| 35 | Fair map: mirrored ground, seat order and routing | 2026-09-21 (0.3.30) |
| 36/37 | Glory scoring. Rules 36 was a mislabeled header; 37 is the first that actually plays. | 2026-09-22 (0.3.32 / 0.3.34) |
| — | WASM lane removed | 2026-09-22 (0.3.33) |
| 38 | Glory hearts; time-weighted lake routing | 2026-09-23 |
| 39 | Behind-in-lives glory; friendly-fire glory removed | 2026-09-23 |
| 40 | Stronger grenades and spray | 2026-09-27 (0.3.47) |
| 41 | 10+2 generated maps; FFA-kin mode | 2026-09-27 (0.3.49) |
| 42 | Opt-in team vision | 2026-09-28 |
| 43 | Configurable glory; teams variants pay 5 per life behind | 2026-09-28 (0.3.60) |
| 44 | FFA cogs wade to wet goals (Heartland lake hearts) | 2026-09-28 |
| 45 | Same routing in every mode | 2026-09-28 (0.3.65) |
| — | Heartland variants removed; Heartland becomes its own coworld | 2026-09-28 (0.3.71) |
| 46 | Seat count per match (2–256); recordings carry it | 2026-09-28 (0.3.75) |
| 47 | Glory for being behind in cogs out (variants: 5) | 2026-09-28 (0.3.75) |
| — | Behind-in-cogs award raised 5 → 10 in every teams variant (config only) | 2026-09-29 (0.3.77) |
| 48 | FFA-kin fog of war (teams game unchanged) | 2026-09-29 (0.3.78) |
| — | Neural lane and training internals only | 2026-09-29 (0.3.79) |
| — | Web viewer only | 2026-09-29/30 (0.3.80-0.3.82, 0.3.87) |
| — | PWNET002 LayerNorm, COND_HEAD, TOKEN_PAIR (neural only) | 2026-09-29/30 (by 0.3.86) |
| — | Opt-in `vision_range` config (no variant sets it); ranged replays stamped +2000 | 2026-09-30 (0.3.88) |
| — | `SeatView` perception boundary (BASIC answers unchanged), `rnd(n)`, old neural contracts and decoder options retired | 2026-09-30 (0.3.89) |

Expect **rules changes several times a week, sometimes several a day**. Each one can invalidate a
tuned constant. Re-read the guide's newest "rules N" section and a live episode's `game_config`
before trusting any number, including the numbers here.
