# webdiplomacy_lab working context

Resolve live state (league settings, champion, policy versions) through the platform
before acting. This file holds only the active objective, state and next decision. The
overnight loop runbook is [LOOP.md](LOOP.md).

## Objective

Standing authority from James (2026-10-06): run the self-play optimization loop
autonomously overnight. Grow a diverse population of strong, distinctively styled agents.
Submit the best one to the league and curate the league's filler roster.

## State (update every tick)

- **Champion:** `webdip-dumbbot:v6` = Kissinger (level-1 opponents + competent-belief fix).
  Hosted: 0.474 against the fillers (par +0.38) and 0.375 head to head with relh (relh 0.028).
- **League fillers (11):** Random, Calhamer, Machiavelli v3, Bismarck v2, Metternich v2,
  Talleyrand v2, Napoleon v2, Blücher v2, Kissinger v1, Fabius v1, Garibaldi v1.
- **Settled (paired A/Bs against Kissinger, 36 games each):**

  | Variant | Paired difference | Verdict |
  | --- | --- | --- |
  | Level-2 opponents | −0.11 | negative |
  | 50% level-1 opponent mix | −0.10 | negative |
  | Share objective | ≈ −0.05 | negative |
  | 24 opponent samples | null | |
  | Triples | −0.06 | negative |
  | Spring rollout | −0.13 | negative |
  | Build search (slow image) | +0.04 | null |

  Full level-1 is the right opponent model, and adding search breadth or features to it so far hurts.
- **Speed:** the convoy approximation in fastadj makes a decision about 9× faster (the package
  fallback was ~95% of search time). It is about neutral on strength locally (ab-convoyapprox),
  but valuable for hosted deadline safety. Ship it as v7 unless it turns negative.
- **Running:**
  - `ab-convoyapprox`
  - `ab-builds-fast`: build search on the fast image.
  - `evolve.py`: anchor Kissinger, generation 40+.

## Live competition

- **relh** (Richard H) entered with `co-gas-webdiplomacy-relh:v2` (policy version 15563512…).
  The ladder after round 2: James Botts 0.084 (2 rounds), relh 0.0 (1 round). Hosted
  `xreq_72926300…` (v6 vs relh vs 5 fillers, 14 episodes) is running. Use relh as a real
  opponent in hosted evaluations from now on. Its private artifacts stay off-limits.

## Known hazards

- The disk is about 98% full. Local replays are slimmed automatically.
- Other sessions prune Docker images; `wd.py` re-pulls them.
- Other sessions switch the shared Softmax login; use the private HOME copy.
