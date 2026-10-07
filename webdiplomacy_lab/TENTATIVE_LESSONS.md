# Candidate guidance

Keep unresolved, testable ideas here with the current evidence needed to evaluate them.
Promote supported guidance to best_practices.md, and remove resolved or unsupported
claims. This is a current working document, not a session log.

- **More search optimization can hurt.** Every version with `SEARCH_RESTARTS=3` (v4b 0.549,
  v5a 0.559) scored below v4a (1 ascent, 0.756) against the DumbBot field. Hypothesis:
  optimizer's curse on a flawed static evaluation + 16 opponent samples. Test running:
  `arena-v5c-restarts1-vs-dumb`.
- **A correlational learned eval is exploitable by search.** Kutuzov (ridge model predicting
  centres two years ahead, R² 0.75) dropped arena score from 0.636 to 0.330. Features like
  "reachable neutral centres" reward staying next to targets instead of taking them. Any
  learned eval needs either causal-ish features or blending; evolution now explores the
  blend weight.
- **Opponent-type inference must not equate "unlike DumbBot" with "random".** The adaptive
  model compared orders only to DumbBot samples, so competent search-bot opponents scored as
  random and our search planned against random play (hosted v4 vs personality fillers:
  0.137 vs par 0.18). Discriminate on order *sensibility* (foreign supports/convoys mark
  random play). A/B: `local_runs/ab-likelihood`.
