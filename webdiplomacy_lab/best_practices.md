# webDiplomacy best practices

Apply the [shared practices](../best_practices.md) with these game-specific rules. Each is
backed by a measured result in `experiments/ledger.jsonl`.

## Measuring

- Judge every result per power against the same-batch field par at that power. Pooled
  scores mostly measure which countries the policy happened to draw.
- Compare two policies by **seating both in the same games** (`wd.py tourney --fixed 'a;b'`
  plus `tools/paired.py`). Separate arms need 2–3× more games for the same precision.
  Treat |z| < 2 as no result: three "+0.08 at z≈1.4" leads (Castlereagh, Rasputin, build
  search) shrank to zero on replication.
- Judge a policy against the field it will meet. The same bot ranked first or last depending
  on the opponents. Kissinger scored 0.38 against DumbBots (its opponent model is too pessimistic
  there) but won against search-bot fields.
- Treat a nonzero `rejected` count in the bot's decision log as a bug: upstream drops
  invalid orders silently, so the adjudicated orders are not the ones chosen.
- Take final centre counts from `results.json` members, not the replay's `Finished`
  history entry (it shows pre-final-autumn ownership).

## Building search bots

- **Model opponents as one step smarter than a heuristic, no more.** The best model gives
  each competent opponent its DumbBot plan improved by one pass of that opponent's own best
  response ("level 1", Kissinger):
  - Level 0 lost by 0.135 (paired).
  - A 50/50 mix of level 0 and level 1 lost by 0.10.
  - Level 2 lost by 0.11.
- **Classify opponents by whether their orders are sensible, not by whether they match
  your model.** Equating "unlike DumbBot" with "random" made every bot treat strong
  opponents as random. Fixing it was worth +0.106 (paired, z = 2.25). Supports or convoys of
  another power's units are what mark random play.
- **Keep the adjudicator on the fast path.** A falling-back-to-the-package path for convoy
  orders was 95% of decision time. Approximating convoys inside `fastadj` made decisions
  about 9× faster with no strength change. Profile (`profile_search.py`) before adding
  search features.
- **More optimization of the same evaluation does not help and often hurts.** Each of these
  was null or negative, likely because the search finds the evaluation's errors:
  - 3 restarts instead of 1
  - Three-unit attack alternatives
  - 24 instead of 16 opponent samples
  - Spring rollouts judged by a DumbBot autumn
- **A correlational learned evaluation is exploitable.** A ridge model predicting centres
  two years ahead (R² 0.75) dropped arena score from 0.64 to 0.33. Its features reward
  standing next to targets instead of taking them. Use learned terms only as small blends
  and verify them in paired games.
- **Evolution needs a strong anchor.** With Calhamer as the anchor, evolved genomes won by
  tuning against each other's quirks. With the champion as the anchor, none beat it over 53
  generations. Use evolution to suggest knobs (it repeatedly found risk aversion ≈ 0.5), then
  test them with paired A/Bs.
- **Freeze reference opponents and pin images by tag.** Other sessions prune Docker images
  and rebuild tags. `wd.py` re-pulls game images, refuses missing candidate images, and
  slims replays (the disk runs near full).
