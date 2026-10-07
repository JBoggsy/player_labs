# webDiplomacy best practices

Apply the [shared practices](../best_practices.md) with these game-specific rules.

- Judge every result per power against the same-batch field par at that power; pooled
  scores mostly measure which countries the policy happened to draw.
- Treat a nonzero `rejected` count in the bot's decision log as a bug: upstream drops
  invalid orders silently, so the orders that were adjudicated are not the ones chosen.
- Take final centre counts from `results.json` members, not the replay's `Finished`
  history entry (it shows pre-final-autumn ownership).
