# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

All entries below come from source-verified mechanics, not gameplay evidence. Each needs
an A/B on the live roster before it is a lesson.

- **Win before glory decays to zero.** Mechanics: winner's glory is 600 minus elapsed
  seconds plus awards, and Elo treats equal side scores as a draw, so a win at the
  10:00 limit with no awards rates as a draw. Evidence needed: distribution of win times
  and winning glory for our policy; any winning episodes scored 0.
- **Avoid pickups when they are not needed.** Mechanics: the team earns +10 glory for
  every 30 s in which no teammate takes a pickup, and a pickup is taken only when useful
  (a medkit only when hurt). Glory size does not move Elo, so this matters only near the
  zero-glory draw line. Evidence needed: winning-glory change and win-rate change versus
  the starter.
- **Falling behind on lives pays glory only if the team still wins.** Mechanics: +5 per life
  behind every 5 s in the league config. Evidence needed: whether leaders' wins cluster
  with a lives deficit (replay stats), before treating it as anything but a side effect.
