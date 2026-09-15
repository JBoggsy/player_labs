# Crewrift best practices

Use the [shared practices](../best_practices.md) for experiment design, provenance,
authorization and iteration speed. The following constraints are specific to Crewrift.

## Measurement

- Measure crew and imposter behavior separately. Match role, imposter count, seat,
  allied policy, opponents, game configuration and time window across a comparison.
- Resolve the current champion field. Include the opponent strengths relevant to the
  hypothesis; kill opportunities depend on the crew's isolation and movement behavior.
- Condition tactical metrics on actual opportunities: a kill rate can fall because
  victims are absent, because they are witnessed, or because execution fails.
- Report whole-episode operational failures separately from gameplay. A missing or
  disconnected opponent changes the game for every seat; filtering only that seat
  leaves contaminated outcomes in the comparison.
- Pace hosted batches according to observed connection and model-call failures. Check
  the entire roster and model telemetry before diagnosing all-zero games as strategy errors.
  Capacity and quotas are live constraints, not fixed concurrency constants.
- Keep episode, job, request, policy-version and seat identities explicit. Warehouse
  tables can use internal episode IDs while filesystem tools use directory names.
- Inspect flat or surprising aggregates for empty joins, missing events, incorrect
  team/role attribution and result-schema mismatch before treating them as discoveries.

## Gameplay and observation

- Verify rules against the exact game configuration. Kill cooldown, meeting behavior,
  role assignment and scoring can differ across configurations.
- Body reports and emergency-button calls are different actions. Check their cooldown
  effects independently rather than treating every meeting as an equivalent reset.
- Scene labels, object IDs, camera offsets and shadow/walkability data define perception.
  Derive them from the game source; apparent screen location alone is not world position.
- Use actual visible roster membership for observed witnesses. Prospective vantage
  scoring is a separate geometry query and must respect viewport and wall occlusion.
- Diagnose imposter seeking separately from killing. Trace when a victim becomes
  reachable, isolated, killable and actually attacked.
- Idle behavior needs a specific purpose and exit condition. Check arrival/interaction
  tolerances when a policy can stop just outside a task or meeting boundary.
- Validate movement predictions against held-out trajectories and candidate decisions,
  rather than only against a summary score.
- Meeting intent, submitted vote and resolved ejection are separate events. Inspect
  event ordering when a vote or death occurs at the meeting boundary.
- Treat chat associations as hypotheses. Timing, speaker role, votes remaining and
  opponent quality can explain apparent persuasion effects.
- Verify a claimed lie against ground truth before adding persistent distrust.
  Perception errors must not become permanent accusations.

## Instruments and model calls

- Match replay decoding to the recorded game artifact and verify complete expansion.
  A binary's existence is not proof it incorporates current source.
- Decode compressed payloads according to their actual format; do not assume a filename
  extension defines compression. Report incomplete traces and parser errors.
- Keep policy and game clocks distinct. Join actions, requests and traces by explicit
  identifiers rather than approximate wall time.
- Model failures need outcome, deadline, backend, token and cost telemetry. Inspect
  the runner-provided endpoint and supported API before blaming strategy for fallback behavior.
- Do not infer artifact retention from an empty query or inaccessible file. Check the
  current route, selection and participant access; elevated opponent access is not allowed.
- Keep mutable policy state episode-local and avoid sharing cached geometry across games.

Read the [game references](docs/README.md), [Crewborg guide](crewrift/crewborg/README.md),
and [lab preferences](user_preferences.md) before changing behavior.
