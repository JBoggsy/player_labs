# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

All entries below come from source-verified mechanics and the scaling model, not from
gameplay evidence. Each needs an A/B on the live roster before it is a lesson.

- **Hold the ultimate for a hero in the burst phase.** Mechanics: every ultimate is 33–53%
  of an enemy hero at level 1 and the engine auto-casts it on the first combat target, so a
  policy that avoids engine combat until it can open on a hero should convert more early
  kills. Evidence needed: kill rate and first-blood timing versus the starter, levels 1–5.
- **Target last hits explicitly.** Mechanics: all income is the killing hit; `objectHp` is
  visible; poison (35) always kills a footman below 35. Evidence so far (local, 2026-09-17):
  the last-hit module takes about 1,000 of 1,080 enemy footmen per team per match in mirror
  play; hosted rate 4.4 per hero per 1,000 ticks against the field. Still open: the starter's
  own last-hit count is not measurable without the replay expander.
- **Waiting for kill windows loses to continuous attacking against the live field.** Exact per-seat
  last hits from 72 re-simulated hosted replays (2026-09-17): our window-waiting policy ranks 11th of
  16 policies at 4.3 last hits per hero per 1,000 ticks; the unmodified starter, which attacks the
  nearest enemy without pause, gets 6.5, and the top farmers 6 to 7. Under test: v5 (engine attacks
  at the standoff point for every class) versus v4, 32 episodes per arm.
- **Punish heroes that an allied tower is firing at.** Hosted one-copy A/B (2026-09-17, 48 games
  per arm): attacking the enemy hero our tower is shooting raised hero kills per match from 0.20
  to 1.04 (adapter: improved, p = 0.02) and last hits per 1,000 ticks from 5.8 to 6.5 with fewer
  deaths. Distance to the tower alone is a false trigger: heroes farm at the edge of tower range
  untouched. Adopted in v7; the tower-fire signal is `objectTarget` of an allied tower.
- **Farming beside busy enemy towers and chasing past tower cover showed no gain.** One-copy
  three-arm A/B (2026-09-17, 48 games each): v10 (tower-adjacent farming when the tower is busy
  or two allied footmen are in its reach, plus a punish chase rule gated on expected time to
  kill, relative speed and an adjacent teammate) scored 6.0 last hits per 1,000 ticks against v9's
  6.3 and v7's 6.0, with fewer top-of-team finishes; the chase rule activated for only 74 ticks
  in 48 games. Both stay behind knobs, off. The last-hit module is above the field mean (6 versus
  4.5) and further single changes are inside noise; farm gains now come from fights and objectives.
- **Weak hitters farm better by letting the engine attack.** Local mirror evidence (Codex
  variant B): standing at the standoff point and letting auto-acquire fight raised last hits
  for Vanguard Knight, Druid Warden, Death Knight and Warlock (+14 to +61 per match) and
  lowered them for Ranger, Demon Hunter and Crossbowman (-21 to -48). Adopted per class in v3;
  needs a hosted A/B per class.
- **Skipping footmen an allied hero is attacking costs farm in mixed-team play.** Local
  evidence: with two of our seats among starter allies, turning the rule off raised last hits
  per 1,000 ticks from 4.5 to 5.2, and mirror play also improved (201 to 208 per hero) once the
  hit prediction was fixed. Off since v3.
- **Spend gold immediately, damage first.** Mechanics: item value is set at purchase and
  eroded by every level; +14 damage is 30–64% of L1 damage. Evidence needed: level-10
  arrival time and duel win rate with early weapon purchases versus the starter's order.
- **Taking the finishing blow in teammates' fights is the largest XP lever found.** One-copy A/B
  (2026-09-17, 48 games per arm): predicting enemy-hero HP at the landing tick of the basic hit
  or a ready strike and joining only engaged fights raised XP per 1,000 ticks from 146 to 183,
  hero kills per match from 0.62 to 2.48, the share of nearby enemy deaths we finish from 8% to
  30%, and cut deaths from 2.67 to 1.90; the level gap to the enemy mean closed from -1.1 to
  -0.1. Holding spells while an enemy hero is within 10 tiles (window-only farming) did not cost
  farm (5.6 to 6.2).
- **Casting a finisher before the retreat walk has no demonstrated gain.** v19 issued
  accepted retreat casts in 28/96 confirmation games (90 total), but XP/1,000 ticks
  read 171.99 to 163.72, kills 1.98 to 1.77 and deaths 2.06 to 2.26 versus v13.
  Joint win with strict team XP lead was 0/96 in both. All replays verified; one v13
  instruction-limit failure stayed in the comparison. Differences are inconclusive;
  the exploratory XP gain did not replicate, so the rule was not adopted.
- **Changing lanes to follow a higher-level ally costs too much farm.** One-copy hosted
  A/B (48 games per arm, exact replays verified): the rule activated in 47/48 games but
  XP per 1,000 ticks fell 168.24 to 112.78, farm 5.50 to 3.56 and kills 2.10 to 1.62.
  Nearby-death exposure barely changed (27% to 29%). Joint wins with a strict team
  XP lead were 0/48 versus 1/48, unresolved. Reject this lane-selection rule; this
  does not settle bounded positioning within the current lane before fights.
- **Walking far into a teammate's fight for the kill loses more than it steals.** One-copy A/B
  (2026-09-17, 48 games per arm): letting the kill-steal approach an engaged enemy hero from up
  to 12 tiles instead of 3 cut hero kills per match from 2.65 to 1.58 and raised deaths from 1.73
  to 2.42; the hero arrived late, into the fight, without a window. Kill windows are taken from
  where the hero already stands; joining fights is a positioning decision to make before they
  start, not a chase.
- **Delayed area casts do not steal kills.** One-copy A/B (2026-09-17, 48 games per arm): adding
  24-tick area and ring spells to the finishing table for targets that stood still last tick
  raised finishing casts from 16 to 44 but cut hero kills from 2.10 to 1.54; the target is dead or
  gone by impact, and the cast pre-empts the basic hit that would have landed. Instant strikes and
  projectiles only.
- **The level race is decided by hero kills, not farm.** One-copy hosted games (2026-09-17,
  96 games): our hero out-farms every enemy on footmen (141 XP per 1,000 ticks against 109)
  yet ends 0.7 levels below the enemy team's mean hero and 3.5 below its best, because the
  enemies earn 75 XP per 1,000 ticks from hero kills (the best, 160) against our 8. A hero kill
  is six last hits. Cutting our deaths from 2.8 to 1.7 per match (v12) denies them about 165
  XP per game but does not close the gap.
- **Do not take late fights for the bounty.** Mechanics: hero-kill rewards are flat and worth
  a tenth of a level by level 19; duels at level 10+ have no burst. Evidence needed: whether
  declining even fights after level 10 raises fort-kill rate.
- **A lone siege behind the wave takes structures but has not raised the win rate.** One-copy
  A/B (2026-09-17, 48 games per arm): the siege module took 0.98 structures per game (from 0)
  with farm and deaths unchanged, but hero kills fell (0.83 to 0.58) and the team win rate read
  44% to 31%, inconclusive at this size. Hypothesis: sieging alone pulls the hero out of the
  fights that decide games; gate it on an allied hero within reach or a lane where our wave
  leads. Needs 96 games per arm or the tightened gate to resolve.
- **Siege behind a creep wave early, solo later.** Mechanics: a gate tower kills a level-1
  hero in 7–12 seconds and targets footmen first, while a lone level-1 hero needs 33–68
  seconds to kill a tower; by level 10 the tower needs 24–51 seconds to kill and dies in
  12–24, so solo sieges become viable from mid levels (class-dependent). Evidence needed:
  tower kills per episode when attacks are gated on a nearby allied footman, split by level.
- **Barracks are a siege objective, not a farm objective.** Mechanics: a barracks has 950 HP,
  pays the tower bounty, is exposed only after all three lane towers fall, and its death
  removes 3 enemy creeps per wave from that lane, which also removes your own team's farm
  there. Evidence needed: fort-kill rate and time-to-fort when the policy takes the barracks
  before pushing the fort versus skipping it.
- **Per-class roles beat one shared behavior.** Mechanics: fixed rosters, no crowd control,
  and level-invariant DPS ordering mean each hero has a stable job (burst killer, duelist,
  siege front, healer; [docs/roles.md](docs/roles.md)). Provisionally adopted as the policy's
  structure. Evidence needed: a role-branched file against a single-behavior file on the live
  roster, per class.
- **Decisiveness beats fighting (forum claim).** Another entrant reports +250 MMR from
  objective-first targeting because a timeout scores zero for everyone. Consistent with the
  scoring rule; unverified by us.
