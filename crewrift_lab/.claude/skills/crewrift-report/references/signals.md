# Crewrift report — signals, data, and formats

Reference for the `crewrift-report` skill: the "interesting episode" taxonomy (what's
flagged, why, and from which data tier), the artifact fields the scripts read, the
score model, and the `expand_replay` line formats the Tier-2 parser depends on.
**Verified 2026-06-09** against crewrift `d9f6b30` and live Observatory episodes.

## Interesting-episode taxonomy

Tier = cheapest data that detects it (1 = `results.json`/`episode.json`; 2 =
`expand_replay`; 3 = policy logs). Every category is read **per role**.

| Category | Tier | Meaning / why it matters |
| --- | :--: | --- |
| `score_low` / `score_high` | 1 | Score is a robust-z outlier vs **this role's** batch norm. Low = what broke; high = positive exemplar. |
| `crew_lost_nearly_won` | 1 | Crew loss with crew tasks ≈ complete (≥85%). The "should've been a win" — most informative. |
| `imposter_no_kills` | 1 | Imposter with 0 kills — failed the core objective. |
| `imposter_lost` | 1 | Imposter on the losing side. |
| `imposter_won_no_kills` | 1 | Imposter won *without* killing (vote manipulation) — a strategy worth studying. |
| `crew_low_tasks` | 1 | Crewmate completed ≤4/8 tasks — low contribution + idle-penalty risk. |
| `no_vote_penalty` | 1 | `vote_timeout ≥ 1` — abstained (−10 each). Never abstain; skip is free. |
| `penalty_leak` | 1 | Points bled to penalties (idle-with-tasks etc.) beyond missed votes. |
| `operational_failure` | 1 | `connect_timeout`/`disconnect_timeout ≥ 1` (−100). **A crash, not a strategy flaw** — kept separate. |
| killed-by-imposter vs ejected-by-vote vs survived | 2 | How the policy died (or didn't). Killed → named killer (a real imposter); ejected → which meeting; both distinguished. |
| vote correctness | 2 | As crew: voted a *real* imposter (good) vs ejected a *real* crewmate (threw a teammate). |
| unusual event profile | 2 | Outlier on the per-episode feature vector (kills/bodies/meetings/ticks/votes/ticks-alive), reported with the deviating feature. |
| kill hygiene / fled / missed body / stuck | 2–3 | Behavioral patterns from the timeline + logs (kill near witnesses, didn't flee, walked past a body, idle/oscillating nav). |
| high variance / matchup-specific | 1 | Distributional: inconsistent scores, or losing specifically to certain opponents (decompose by co-slot policy). |

## Artifact fields

**`results.json`** — all per-slot arrays, index = slot/position:

| key | meaning |
| --- | --- |
| `names` | display name per slot |
| `scores` | final score per slot (net of penalties) |
| `win` | bool, did this slot's side win |
| `tasks` | tasks completed |
| `kills` | kills (imposters only) |
| `imposter` / `crew` | role flags (1/0) — **authoritative role**, no inference needed |
| `vote_players` | votes this slot cast against players |
| `vote_skip` | skip votes this slot cast |
| `vote_timeout` | meetings this slot failed to vote (the −10 trigger) |
| `connect_timeout` / `disconnect_timeout` | operational-failure counts (−100 trigger) |

**`episode.json`** — `id`; the **slot→policy** map, in one of two shapes (the scripts
handle both via `slot_entries()`): **league** episodes carry `policy_results[]` =
`{position, policy:{name,version,id}, avg_reward, agents:[{reward}]}` (plus `game_stats`,
`tags`, `steps`); **experience-request** episodes — what XP requests produce — carry
`participants[]` = `{position, policy_name, version, policy_version_id, player_name,
label}`. Join either to `results.json` by `position`.

> Note: `results.json` has **no** explicit "died"/"ejected" field — those are Tier-2
> (parse kills + per-meeting vote tallies). And per-slot **chat** content is not in
> `results.json`; it's in the timeline (Tier 2) / logs (Tier 3).

## Score model

A slot's final score (crewrift sim): `score = 100·win + 1·tasks + 10·kills − penalties`,
penalties = `10` per missed vote (`vote_timeout`) + `1` per idle-with-tasks interval.
So Tier 1 derives `penalty_points = 100·win + tasks + 10·kills − score` (points bled
to penalties). Tier 2 itemizes them exactly from the timeline's `score …` lines.

## `expand_replay` line formats (Tier-2 parser contract)

Top-level `tick N` lines; events are indented 2 spaces under their tick. Players are
`color(name)` (color may contain spaces: "pale blue", "light blue", "dark navy").

```
  phase RoleReveal | Playing | Voting | VoteResult | GameOver
  player <color>(<name>) joined
  player <killer> killed <victim>
  body <victim> room <Room>
  player <reporter> reported body <victim> room <Room>
  player <voter> voted <target>            # or "voted skip"
  player <caller> called emergency button
  score player <who> <+/-N> (for completing task | killing | winning | standing still | …)
  player <who> started|completed task <N>  # may end "while dead"
```

Parser notes (`scripts/profile_replay.py`):
- **Ejection** has no explicit line — infer per meeting (a `Voting` phase): tally
  `voted <target>`; the player-target with the most votes is ejected **iff** it beats
  skip and is a unique max.
- **Death** = the policy's color appearing as a `killed` victim (→ killed-by-imposter,
  killer is a real imposter) takes precedence; else check ejection; else survived.
- **Role/identity join:** results arrays are slot-indexed; the timeline is by color.
  Bridge via the shared **name**: `name_to_color` from `joined` lines, then map the
  target's `names[slot]` → color, and the `imposter`-flagged slots' names → the
  imposter color set.
- **`expand_replay` must be version-matched** to the recording build or it prints
  `hash failed` and stops early — `profile_replay.py` detects this and tells you to
  rebuild. See `crewrift_lab/docs/crewrift-replays.md` §B.
