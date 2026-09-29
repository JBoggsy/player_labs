# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

Entries come from source-verified mechanics or local tool runs, not hosted gameplay evidence.
Each needs an A/B on the live roster before it is a lesson.

- **Win before glory decays to zero.** Mechanics: winner's glory is 600 minus elapsed
  seconds plus awards, and the ladder rates the glory margin (`margin_scale: 1000`), so every
  second of delay costs rank and a win at the 10:00 limit with no awards rates as a draw. Evidence needed: distribution of win times
  and winning glory for our policy; any winning episodes scored 0.
- **Avoid pickups when they are not needed.** Mechanics: the team earns +10 glory for
  every 30 s in which no teammate takes a pickup, and a pickup is taken only when useful
  (a medkit only when hurt). Glory size moves Elo under `margin_scale: 1000`, so +10 glory
  is +0.005 of Elo outcome per episode. Evidence needed: outcome-score change and win-rate
  change versus the starter.
- **Falling behind pays glory only if the team still wins.** Mechanics: in the league config
  a team earns +5 per life behind and +10 per extra cog out of the match, each every 5 s
  ([mechanics.md §1.2](docs/mechanics.md)). Evidence needed: whether leaders' wins cluster
  with a lives or cogs deficit (replay stats), before treating it as anything but a side effect.
- **Stop aiming at disguised teammates.** Local evidence: `base.bas` picks its target by observed
  seat parity, and a uniform makes a teammate answer to an enemy seat, so base.bas aimed at a
  disguised teammate on 35 of 4,718 target lines (6 local matches, `pw.py intent audit`). Friendly
  fire is on. Evidence needed: how often it actually fires on them and the lives it costs
  (`pw.py metrics` friendly-fire columns), then an A/B of a check that skips a disguise-candidate
  target standing where a teammate was last seen.
- **Lives decide matches, not the meter.** Local and public evidence: 38 of 40 league episodes and
  57 of 60 local ones ended by elimination, and in the win-probability fit lives dominate while
  meter plus hearts alone predicted nothing held-out (`pw.py winprob`, thin data: 40 league
  episodes). Evidence needed: a larger league sample; then whether survival changes (refusing
  fights earlier, fewer lone deaths) raise the Elo outcome more than capture changes do.
- **Never abandon a grenade charge.** Local evidence (28 seeds, base.bas vs base.bas, 2026-09-29):
  the engine throws a charged grenade on the first tick the script stops calling
  `chargeGrenade`, and base.bas stops mid-charge whenever its conditions fail (target died,
  teammate near the target, out of range; `reference/base.bas` grenade block). The throw then
  flies ~197 units, inside the 415-unit blast. 86 of 340 throws were such short throws (mean 264
  units); they killed the thrower 60 times, teammates 12 times and enemies 4 times; own-team
  grenades caused 104 of 1,675 deaths (6.2%). Example: local seed 24, seat 2 at t=454-465 killed
  itself and seats 4 and 6. Candidate fix: keep charging and throw at the last good aim point, or
  cancel only while the charge is 0. Evidence needed: a hosted A/B; the league field may punish
  or ignore this differently.

