# webdiplomacy_lab working context

Resolve live state (league settings, champion, policy versions) through the platform
before acting. This file holds only the active objective, state and next decision. The
overnight loop runbook is [LOOP.md](LOOP.md).

## Objective

Standing authority from James (2026-10-06): run the self-play optimization loop
autonomously overnight. Grow a diverse population of strong, distinctively styled agents.
Submit the best one to the league and curate the league's filler roster.

## State (update every tick)

- **League champion line:** `webdip-dumbbot:v5` was submitted on 2026-10-07. It is
  Machiavelli: fastadj search, 1 restart, and the competent-vs-random opponent likelihood fix.
  - v4 was the same without the fix. Hosted against the fillers it scored 0.137 vs par 0.18,
    because the bug labelled search opponents as random.
  - Hosted check `xreq_6c3fe219…` (14 episodes against 6 fillers) is running.
- **League fillers (8):** Random, Calhamer, Machiavelli (v2), Bismarck, Metternich,
  Talleyrand, Napoleon, Blücher. All except Random still use the OLD likelihood. Once v5 is
  confirmed, re-upload them with the fix to strengthen the league field.
- **Championship-1** (36 games): Machiavelli-r1 +0.058, Kissinger +0.030, Bismarck +0.029,
  Blücher ≈0, Talleyrand <0, Nash −0.04, Calhamer −0.09.
- **Negative results:** Kutuzov (learned evaluation, exploited by search), 3 restarts, and
  Kissinger and Nash against the DumbBot field.
- **Running:**
  - `evolve.py`: image v8a, anchor = champion, generation 15+.
  - `ab-likelihood`: finishing.

## Known hazards

- The disk is about 98% full. Local replays are slimmed automatically.
- Other sessions prune Docker images; `wd.py` re-pulls them.
- Other sessions switch the shared Softmax login; use the private HOME copy.
