# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

- **More search optimization can hurt.** Every version with `SEARCH_RESTARTS=3` (v4b 0.549,
  v5a 0.559) scored below v4a (1 ascent, 0.756) against the DumbBot field. Hypothesis:
  optimizer's curse on a flawed static evaluation + 16 opponent samples. Test running:
  `arena-v5c-restarts1-vs-dumb`.
