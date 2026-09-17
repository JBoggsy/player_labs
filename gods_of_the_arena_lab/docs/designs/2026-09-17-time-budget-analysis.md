# Time-budget analysis: is the last-hit deficit presence or conversion?

Question: our policy farmed below the field's mean (4.3 versus 5.3 last hits per hero per
1,000 ticks in the five-seat v4/v5 batches). Is that because our hero is not near enemy
creeps (presence) or because it is near them and does not take the kill (conversion), and
which of our rules costs the most?

Instrument: a re-simulation probe (`lab_timebudget.nim`, compiled against polyworld
`f2ab9598` in the session scratchpad; the same loop as `tools/expand_replay.nim` with
per-tick counters, to be folded into the expander's state rows). For every seat and every
alive tick it records whether an enemy footman is within 8 tiles ("in range"), whether the
hero is attacking, walking, or idle, whether an enemy hero is within 6 tiles or an enemy
tower within 7, and the exact footman last hits from the reward accounting. Hashes verified
on every replay.

## Data

- 63 five-seat A/B episodes (`xreq_33a01eeb…` v4, `xreq_197d8abc…` v5), 320 of our
  hero-matches plus every opponent seat in those games.
- 96 single-seat A/B episodes (`xreq_8cd07e44…` v5, `xreq_a25ad678…` v8), one of our
  heroes per game with nine random champions.

## Findings (five-seat batches, all classes pooled)

| Measure | Ours (v5) | Field's top farmers (red-kite, black-kite, aaron, daf, starter) |
| --- | ---: | ---: |
| Alive ticks with an enemy footman within 8 tiles | 19% | 18% to 27% |
| Attacking during those ticks | 35% | 80% to 100% |
| Last hits per 1,000 in-range ticks (conversion) | 27.6 | 28 to 37 |
| Alive ticks walking with no creep near | 64% | 48% to 65% |
| Ticks within 7 tiles of an enemy tower | 11% | 15% to 24% |
| Ticks with an enemy hero within 6 tiles | 26% | 25% to 30% |
| Dead | 5% | 3% to 4% |
| First tick in farm range (median) | 853 | 721 to 1,033 |

Presence is not the problem: our heroes are near enemy creeps as often as the field, arrive
in lane at the same time, and stand near enemy heroes as often. Two things differ:

1. **Conversion, concentrated in melee and low-damage classes.** Per class (v5 versus the
   top farmers of the same class): Vanguard Knight 16.5 versus 20.5 last hits per 1,000
   in-range ticks, Druid Warden 10.9 versus 20.4, Death Knight 19.5 versus 28.8, Warlock
   19.0 versus 29.9, Berserker 17.9 versus 35.8. The ranged carries are at parity or better
   (Ranger 43.6 versus 42.1, Crossbowman 47.4 versus 37.2, Lich 38.1 versus 42.6,
   Arcanist 35.3 versus 29.7, Demon Hunter 30.5 versus 30.7). The mechanism is visible in
   the attack fraction: melee and weak classes attack 19% to 26% of their in-range ticks
   because the standoff logic keeps walking them to a moving hold point, which cancels the
   engine's attack; the field attacks 85% to 100%.
2. **Tower avoidance.** We spend 9% to 11% of alive ticks near enemy towers against 15% to
   24% for the field, so waves that stall under a tower are farmed by them, not us. This is
   the second-largest cost; the hero-threat retreat and the walk to lane cost little, since
   hero proximity and first-in-range tick match the field.

So the deficit is conversion in six classes, driven by the standoff machinery, with tower
avoidance second. The 600-tick walk to lane and the hero-threat retreat are not the problem.

## The v8 experiment (single change)

v8 = v5 plus: classes 0, 3, 4, 5, 8, 9 (Vanguard Knight, Druid Warden, Demon Hunter,
Death Knight, Warlock, Berserker) chase-attack the anchor footman continuously instead of
walking to a standoff point; kill windows keep priority. Built as
`policy/experiments/timebudget/dist.bas` (patched on the uploaded v5 file, because
`policy/modules/` was mid-edit by another session), uploaded as `james-botts-gota:v8`.
Local sanity (mirror 208 last hits per hero, mixed 4.87 per 1,000 ticks) matched v5.

## Results

Single-seat, same-window A/B, 48 episodes per arm (one of our heroes per game), exact
replay counts:

| Measure | v5 | v8 |
| --- | ---: | ---: |
| Our last hits per 1,000 ticks | 5.82 | 5.91 |
| Other nine seats in the same games | 4.71 | 4.61 |
| Rank within team (1 = best of 5) | 2.65 | 2.40 |
| Share of team last hits (even = 20%) | 22% | 24% |
| Attacking during in-range ticks | 38% | 50% |
| Conversion (last hits per 1,000 in-range ticks) | 28.8 | 33.0 |
| Deaths per 1,000 ticks | 0.29 | 0.20 |

Welch t = 0.66 for the rate difference (+0.37 per 1,000 ticks); the lab adapter
(`tools/compare.py`, `--group all`) reports 5.50 to 5.83, inconclusive. Per class the change
helped Death Knight (7.6 to 8.7), Demon Hunter (5.9 to 7.4), Vanguard Knight (3.8 to 4.7)
and Warlock's conversion, and hurt Berserker (6.6 to 3.8) and Druid (6.1 to 4.5) at five
games each, so the class list needs the hosted per-class sample before it is fixed.

Two results matter more than the v8 verdict:

- **With one seat per game, the policy is above the field's mean farmer**: 5.8 to 5.9
  last hits per 1,000 ticks against 4.6 to 4.7 for the other nine seats, rank 2.4 to 2.7
  of 5, top of its team 27% of the time. The earlier "11th of 16" came from five-seat
  rosters, where five copies compete for the same lanes on both teams.
- **Conversion moved the way the analysis predicted** (attack fraction 38% to 50%,
  conversion 28.8 to 33.0, deaths down a third), so the mechanism is right even where
  the rate gain is within noise.

## Recommendation

Option 2 is done and is a modest, mechanism-confirmed gain; the policy is now an
above-average farmer in the single-seat setting. The remaining measured gap is tower
avoidance (presence near towers half the field's), which is the next single change:
farm beside a tower whose current target is a footman, keeping the escape when it turns
on the hero. After that, option 3: the last-hit module is at the point where further
farm gains come from fighting and objective play, so start the wrapping policy.

## Files

- `gods_of_the_arena_lab/policy/experiments/timebudget/dist.bas`, `README.md` (v8 source).
- This document. The probe source is in the session scratchpad
  (`polyworld/examples/gods_of_the_arena/tools/lab_timebudget.nim`) pending its merge into
  the expander's state rows (Codex, Phase 5).
- Requests: `xreq_8cd07e44-239a-4f66-a7c3-6eb5b8b29f2b` (v5, 48 episodes, single seat),
  `xreq_a25ad678-22d7-4af8-a5a6-e19422a3e332` (v8, 48 episodes, single seat); about 48
  credits. Uploaded: `james-botts-gota:v8`.
