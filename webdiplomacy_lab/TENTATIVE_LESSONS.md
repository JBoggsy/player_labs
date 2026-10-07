# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

- **Implicit diplomacy (Castlereagh) is null as built.** Hostility memory with grudge/peace
  centre weights tied Kissinger against both the filler field and a strong-only field. A
  version that also changes the *opponent model* (expecting peace from non-aggressors) is
  untested.
- **The evaluation function is the likely bottleneck.** Every lookahead and learned-
  evaluation attempt failed, and more search over the current evaluation does not help. The
  next real gain probably needs a better position evaluation, for example one trained
  causally from self-play outcomes rather than by regression over observed positions.
