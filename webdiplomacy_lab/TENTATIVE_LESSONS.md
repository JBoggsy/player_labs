# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

- **Implicit diplomacy (Castlereagh) is null as built.** Hostility memory with grudge/peace
  centre weights tied Kissinger against both the filler field and a strong-only field. A
  version that also changes the *opponent model* (expecting peace from non-aggressors) is
  untested.
- **Press agents over-communicate and under-search.** In local self-play (glm-5.3-flash,
  `castlereagh` soul) agents sent about 5 messages per search and accepted most deals
  without `assess_deal`. Hypothesis: requiring a search-based deal check before agreeing
  improves results. Evidence needed: a matched comparison against real press opponents
  (see the measurement decision in `WORKING_CONTEXT.md`).
- **Kissinger may be a weak floor in press.** Its opponent model ignores alliances; the
  press policy (stances, expected orders) is the fix, but how often agents commit a policy
  that differs from the floor, and whether that helps, is unmeasured. Trace:
  `press_commit` vs the phase's floor orders.
- **The evaluation function is the likely bottleneck.** Every lookahead and learned-
  evaluation attempt failed, and more search over the current evaluation does not help. The
  next real gain probably needs a better position evaluation, for example one trained
  causally from self-play outcomes rather than by regression over observed positions.
