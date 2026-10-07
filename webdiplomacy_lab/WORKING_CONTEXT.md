# webdiplomacy_lab working context

Resolve live state (league settings, champion, policy versions) through the platform
before acting. This file holds only the active objective, state and next decision. The
overnight loop runbook is [LOOP.md](LOOP.md).

## Objective

Standing authority from James (2026-10-06): run the self-play optimization loop
autonomously overnight. Grow a diverse population of strong, distinctively styled agents.
Submit the best one to the league and curate the league's filler roster.

## State (update every tick)

- **League:** `webdip-dumbbot:v3` submitted 2026-10-06 (search + joint moves + adaptive
  opponent model). Hosted against random filler it won 26 of 26 scored games (score 1.0).
  The v1 champion scores 0.91.
- **Personalities uploaded (v1, James Botts):** calhamer, machiavelli, bismarck,
  metternich, talleyrand, napoleon. Version UUIDs are in
  `experiments/personality_versions.txt`. Hosted validation (`xreq_6ed8198a…`) passed:
  0 rejections; one disband IndexError, now fixed in source. **League fillers set on
  2026-10-07** to Random, Calhamer, Machiavelli, Bismarck, Metternich, Talleyrand and
  Napoleon. Hosted evaluations should now use this roster as opponents.
- **Local evidence against six DumbBot v1** (slot-0 score; parity 0.143):

  | Version | Score | Games |
  | --- | --- | --- |
  | v2 search | 0.556 | 24 |
  | v3a | 0.571 | 23 |
  | v3b share objective | 0.679 | 19 |
  | v4a fastadj | 0.756 | 15 |
  | v4b rollout + restarts | 0.549 | 23 |

- **Population and arena findings, 2026-10-07:**
  - Restarts=3 hurts. Machiavelli with 1 restart scored 0.636 over 30 games, against about 0.55 for the 3-restart versions.
  - Bismarck tops the mixed population but scores only 0.48 against the DumbBot field.
  - Kissinger scores 0.38 against the DumbBot field.
- **Evolution loop** (`tools/evolve.py`, state in `experiments/evolve_state.json`): generation 0
  elites are Talleyrand, Bismarck-share and Bismarck. The Calhamer anchor scores −0.10.
- **Running:**
  - `evolve.py`: continuous generations, 2 games in parallel.
  - `arena-v4a-rerun-vs-dumb`: 30 games, to calibrate noise against v5c with 1 restart.
- **Next promotion candidate:** a fastadj search with 1 restart, probably with the share objective.
  It is far cheaper per phase on hosted pods than v3, which uses the package adjudicator and
  took about 21 s per phase. Decide after the v4a rerun and 2–3 more generations.

## Known hazards

- The disk is about 98% full. Local replays are slimmed automatically.
- Other sessions prune Docker images; `wd.py` re-pulls them.
- Other sessions switch the shared Softmax login; use the private HOME copy.
