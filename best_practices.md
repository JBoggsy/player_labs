# Best practices for policy improvement

These game-agnostic practices support the evaluate → diagnose → improve loop.
Use the owning game's reference for mechanics and the current user request for scope.

## Keep iterations fast

- Make one focused change, rebuild and upload promptly. Hosted evaluation is the
  primary competitive test; do not add routine pre-upload smoke gates or test suites.
- Use local runs for a specific mechanism, transport problem, recorded-wire parity,
  or own-policy self-play. Do not spend hosted XP on self-play.
- Run focused checks for shared analysis tools: parsing, identity joins and statistics
  must be reliable before their output can support a conclusion.
- Start with a working deterministic policy and useful observability. Add an LLM
  when the decision requires it. Reassess the largest observed gap after each evaluation.
- Uploading registers an artifact. League submission and public writing require
  explicit authorization; existing authorization for the action counts.

## Measure the actual objective

- Use multiple independent episodes. Size the sample for the effect, variance,
  role assignments and intended uncertainty; do not choose a batch size by habit.
- Report effect size, uncertainty and completion coverage. Use appropriate mean-
  and rank-based comparisons, and account for multiple comparisons.
- Separate roles, opponents and behavioral metrics before interpreting an aggregate.
  Report means and distributions where they answer different questions.
- Normalize individual statistics by seat appearances. A team's shared result is
  one outcome per episode, not one independent outcome per hero or teammate.
- Control team composition when isolating a player's contribution. Merely dividing
  totals by appearances does not remove teammate and opponent effects.
- Treat technical failures separately from gameplay outcomes. Learn the game's
  failure contract; a valid game-time draw is not an infrastructure timeout.
  Keep failed attempts in operational coverage rather than silently dropping them.
- Use opponents that represent the objective and the field's strength spread.
  Include strong, middle and weak opponents; report those groups separately.
  Do not silently replace a multi-policy field with one representative policy.
- A live survey locates weaknesses. A fresh, matched, same-window A/B comparison
  isolates a change. Replicate meaningful gains before promotion.
- Offline and local proxies can rank candidates but do not establish improvement
  against the field. Verify that any intermediate metric maps to the actual objective.
- Target hosted requests to the question and stream artifacts as episodes finish.
  Use the [credit allowance](docs/xp-credits.md); communicate the design and cost.

## Diagnose before explaining

- Require a falsifying check before stating a causal explanation. First establish
  that the effect is real, then name its observable prerequisites and an alternative
  explanation, and run the query that distinguishes them.
- Inspect distributions before choosing a story. Mixed event types, phase changes,
  missing observations and pooled roles can reverse an apparent mechanism.
- Trace state → perception → belief → strategy → action → accepted execution → effect.
  Use stable IDs and time keys and verify what the downstream evaluator received.
- Log the inputs to each decision gate, its selected action and activation count.
  An unused capability or a gate reading missing data must be distinguishable from
  a behavior that fired without helping.
- Separate operational failures from gameplay failures. Identify the responsible
  layer before editing code, and sample surprising failures within each class.
- Compare the policy's own wins and losses to find variable behavior. A behavior
  present in every episode cannot explain its score spread. Check reverse causation.
- Use repeated, role-conditioned evidence for opponent profiles. Respond to observed
  behavior rather than hard-coding opponent names.
- Preserve temporal order for spatial questions. Use trajectories and event-centered
  windows; a summed heatmap cannot establish who moved first or caused an engagement.
- Inspect authoritative game code and actual logs when observations disagree.
  Verify exact thresholds, timers, scoring and failure signals before rule-based changes.

## Make hypotheses testable

- Name one mechanism and its predicted observable effect before running an experiment.
  Choose a primary metric, control conditions and stopping rule in advance.
- Plausibility motivates a test; it is not evidence. Avoid point forecasts inferred
  from correlations or small observational samples.
- Verify activation and downstream impact. Winning an episode does not prove that
  the intended mechanism ran or caused the outcome.
- When an investigation repeats, keep the active hypotheses, separating checks and
  unresolved observations concise. Replace disproven explanations directly.
- Protect the objective and measuring environment. An environment fix changes the
  comparison contract and requires a fresh baseline.

## Engineering and evidence

See [player engineering](docs/player-engineering.md) for architecture and navigation.

- Check current SDK/CLI behavior and the game's manifest before assuming a feature
  is absent. Match protocol, configuration and artifact identity to the evaluation.
- Account for renderer offsets when decoding sprite positions. A logical entity
  position and the drawn object's position need not be equal.
- Blocking decision work can starve transport keepalives. Inspect the actual bridge
  and configure its heartbeat behavior for the execution model.
- Clear action-completion latches on phase transitions. A missing self-observation
  must not permanently wedge a policy.
- A stuck-state escape must change persistent state and verify progress, not merely
  emit a different action for one tick.
- Rebuild after code changes. Use explicit controls to distinguish the candidate
  from a fallback or unintended baseline, and verify successful integration calls.
- Check return values and actual effects separately. An accepted command does not
  guarantee arrival, damage, completion or objective progress.
- If a regression occurs outside the edited path, inspect shared inputs, dependencies,
  image contents, opponent composition and operational failures before attributing it.
- Keep the active experiment's exact artifact identities in its machine-readable
  inputs/results. Resolve upload and membership state from the platform; do not
  maintain a documentation version log.
- Commit only attributable changes after checking documentation. Keep credentials
  out of source, reports and logs. Do not include unrelated work in a checkpoint.
- Keep documentation complete and current. Promote supported rules with their limits;
  replace obsolete claims and remove resolved working notes. Do not accumulate
  change narratives, audit records or historical reports.
