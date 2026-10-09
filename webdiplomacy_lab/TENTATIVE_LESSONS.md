# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

- **Implicit diplomacy (Castlereagh) is null as built.** Hostility memory with grudge/peace
  centre weights tied Kissinger against both the filler field and a strong-only field. A
  version that also changes the *opponent model* (expecting peace from non-aggressors) is
  untested.
- **Our press layer currently loses centres relative to its own floor.** Against the diverse field,
  castlereagh scored 0.126 (100 games) while silent Kissinger, the same search engine without
  press, scored 0.174; the gap held after the geometry fix (wave 2). Which LLM actions cost centres
  (stances, pins, trusted deals) is not isolated. Evidence needed: per-phase comparison of committed
  orders vs the floor's expected centres, and the v8/rotation A/Bs.
- **We re-trust powers that betrayed us.** In 100 wave-1 games, after a first breach or trusted
  attack we returned to trusting the same power 94 times in 46 relationships (Talleyrand: 62 of 64).
  The liar on gpt-6-luna was the best seat in both fields. Hypothesis under test: permanent liar
  marks on an observed trusted attack (v8). Model vs soul is under test in the rotation arms.
- **Recorded promise verdicts are unreliable.** 10 of 30 sampled "broken" verdicts were our own
  recording errors (reversed DMZs, invented holds, wrong season); only 10 were clean. Do not drive
  irreversible decisions from them; prefer observed orders against our units and centres.
- **LLM agents need the map handed to them.** Without a connectivity list the agents reasoned about
  adjacency from memory and often wrongly (about 66 claims per game; SER/BUL/GRE reported
  unconnected). With it, about 21. Whether this changes score is under test (v7).
- **Agents do not test deals unless forced, and override cost warnings.** v1 made zero
  `assess_deal` calls in local game 2; a code gate (v3) raised it to 17 per game. A cost warning
  with an override (v5) was overridden both times it fired. Whether either helps is unmeasured.
- **Kissinger may be a weak floor in press.** Its opponent model ignores alliances; the
  press policy (stances, expected orders) is the fix, but how often agents commit a policy
  that differs from the floor, and whether that helps, is unmeasured. Trace:
  `press_commit` vs the phase's floor orders.
- **The evaluation function is the likely bottleneck.** Every lookahead and learned-
  evaluation attempt failed, and more search over the current evaluation does not help. The
  next real gain probably needs a better position evaluation, for example one trained
  causally from self-play outcomes rather than by regression over observed positions.
