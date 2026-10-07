# webdiplomacy_lab working context

Resolve live state (league settings, champion, policy versions, filler roster) through the
platform before acting. This file holds only the current state and next decision. The
unattended-loop recipe is [LOOP.md](LOOP.md). Measured lessons are in
[best_practices.md](best_practices.md).

## State (2026-10-07)

- **Champion:** `webdip-dumbbot:v8` (policy version `41938ab8…`), submitted 2026-10-07.
  It is the Kissinger policy:
  - search with level-1 opponents and the competent-belief fix;
  - convoy approximation;
  - the modular SearchBot refactor with the Nim integer/boolean adjudicator.

  Its behaviour is bit-identical to v7 (golden contract `webdip_bot/tests/golden.json`, 334
  exact decisions), with decisions a median 27% faster.
  - Hosted check `xreq_38daed76…`: 0 exceptions, 0 rejected orders, max decision 2.8 s.
- **Final-policy decision:** in paired games, no variant beats plain Kissinger (risk
  aversion, build search, Castlereagh diplomacy, mixed strategy, Fabius, level 2, triples,
  rollout). Details are in `experiments/ledger.jsonl`.
- **League fillers (12):** Random, Calhamer, Machiavelli v3, Bismarck v2, Metternich v2,
  Talleyrand v2, Napoleon v2, Blücher v2, Kissinger v2, Fabius v1, Garibaldi v1, Rasputin v1.
  The Kissinger filler still runs the Python adjudicator, with identical behaviour.
- **Competition:** relh (`co-gas-webdiplomacy-relh:v2`) is the only other entrant. It scores
  about 0.0–0.03 per game in hosted tests against us and the fillers.
- **The continuous loop is wound down.** Crons are deleted and `evolve.py` is stopped at
  generation 53; its state is in `experiments/evolve_state.json`.

## Open directions (not started)

- A better position evaluation: the measured bottleneck (see `TENTATIVE_LESSONS.md`).
- Diplomacy that changes the opponent model, not only centre values.
- An LLM press player, if the league moves to a press variant.
