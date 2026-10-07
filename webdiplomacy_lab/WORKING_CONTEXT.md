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
- **Evolution loop** (`tools/evolve.py`, image v6b, state in `experiments/evolve_state.json`):
  at generation 5 the elites are aggressive Bismarck × Talleyrand crosses. g2-0ed5 was
  promoted as **Blücher** (`webdip-blucher:v1`, 4247912e) and added to the league fillers.
- **v4a is about equal to Machiavelli with 1 restart** against DumbBot: pooled v4a 0.71 over 45 games
  vs 0.64 over 30, p≈0.2.
- **Running:**
  - `evolve.py`: 3 games in parallel.
  - `leaguesim-blucher` and `leaguesim-machiavelli`: 24 games each, with the candidate fixed and
    6 opponents drawn from the filler roster. This decides the next main-line submission
    (champion: v3).
- **League fillers (8):** Random, Calhamer, Machiavelli, Bismarck, Metternich, Talleyrand,
  Napoleon, Blücher.

## Known hazards

- The disk is about 98% full. Local replays are slimmed automatically.
- Other sessions prune Docker images; `wd.py` re-pulls them.
- Other sessions switch the shared Softmax login; use the private HOME copy.
