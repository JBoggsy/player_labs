# Best practices for the improvement cycle

A small, **battle-tested, game/world-agnostic** set of practices for the
evaluate → diagnose → improve loop, distilled from many prior optimization
campaigns. `AGENTS.md` tells you to read these. Treat them as your defaults, and
**warn the human if a request would contravene one** before proceeding (then do
what they decide).

## Measurement — know whether a change actually helped

- **Evaluate on a batch, never a single game.** Within-game variance (std can exceed
  the mean), role/seat asymmetry, and opponent dependence each swamp one game.
- **Decompose before judging; the aggregate headline is a trap.** Cut results by
  **role** (the most important cut — an aggregate has historically hidden one role
  being completely broken), by **opponent/matchup** (pairwise), and by **behavioral
  sub-metrics** (wins, mean *and* median, action counters). Their disagreement
  localizes *why*.
- **Apply statistical rigor.** Report effect sizes (not just means), run a mean-based
  *and* a rank-based test, and apply multiple-comparison correction; pool matched
  batches for power. A leaderboard that looks cleanly ranked is mostly noise until
  corrected.
- **Evaluate across the WHOLE field's strength, not just the top-N — the EV is in
  beating the players you *can* beat.** A leaderboard scores your **mean over every
  opponent you're seated against**, and the top few are a minority of that field. Tuning
  and A/B-ing only against the top-N systematically *hides* gains that exist against the
  weaker majority: the strongest opponents can cap a behavior regardless of your policy
  (so a real improvement reads as a no-op), while the same change pays off clearly
  against beatable opponents. **Always test a candidate against a strength *spread*
  (strong / mid / weak), and bucket results by opponent strength** — a change that's
  neutral vs elites and a win vs the rest is still a net EV gain, and you'd miss it
  testing top-N only. Leaving the weak-opponent upside on the table is leaving points on
  the table. (Mechanically: pin a representative spread, or draw randomly and bucket by
  opponent leaderboard score; don't default the opponent roster to the top-N.)
- **Experience requests are your primary eval — they aren't scarce.** They run many
  episodes in parallel on Softmax infra and are currently free, so use them liberally
  rather than rationing them; just **target them to the question** (matched roles when
  the change was role-specific; the specific opponents the policy struggles against)
  and harvest async (the value is in the results, not babysitting the wait).
- **Local testing is smoke/correctness only — never comparative.** You generally
  can't download and run other users' policies locally (currently broken, and strong
  policies may be private), so local play proves only that your artifact runs, speaks
  the protocol, and that your change took. **All competitive judgment comes from
  experience requests.** (A local zero from a trivial fixture is still not a broken
  player; and join scores to role/player by the authoritative per-policy field, never
  by list position.)

## Diagnosis — from "it lost" to "it does X in situation Y because Z"

- **You can't debug an outcome, only a trace.** Pivot immediately from the result to
  the player's internal reasoning stream.
- **Observability is something you build, not something you're given** — reason traces
  (mode / options / choice + a *why*), belief/perception snapshots, tick-keyed lines,
  tiered verbosity, replays. If you can't see the behavior you can't improve it;
  building the instrument often precedes the fix.
- **Triage by failure class; chase the surprise.** Aggregate, then sample the worst
  case per class. The most informative game is the one that "should have been a win."
- **Variance carries the mechanism — and the lucky wins are findings too.** Don't stop
  at the aggregate; look at *which* episodes moved and what they share. A change that
  helps one cluster and hurts another points straight at the gating fix, and the
  positive outliers ("we got lucky here") are a hypothesis source — find the mechanism
  behind them and make it fire on purpose, not by chance.
- **Don't optimize the obvious intermediate metric.** Confirm it actually maps to the
  objective before chasing it; counterintuitive correlations (e.g. dying *more* while
  scoring *more*) are signal, not noise — the "safe" metric can be the losing one.
- **Name the layer first** — perception / belief / strategy / execution — because the
  layer determines where the fix goes. Keep **operations** failures (can't
  connect/build) strictly separate from **behavior** failures (plays badly).
- **Ground truth beats inference.** When the player's view or the tooling could be
  lying, verify against the game's authoritative source/logs before building on it.

## Hypothesis discipline — make a diagnosis actionable

- **Name a specific mechanism and predict an observable effect.** Pin it to a
  rule/timer/threshold and the trace line that proves it; propose a scoped change to
  *that* mechanism only.
- **Plausibility is not evidence.** "This should obviously help" is a reason to *test*,
  never to assert or ship — roughly half of "obviously good" ideas regress. A
  hypothesis you can't tie to something you actually observed (a trace line, a code
  path) is a vibe, not a hypothesis.
- **Pre-register the expected effect**, ideally as a test written *before* the run —
  the test is the hypothesis made falsifiable.
- **"Capability exists" ≠ "capability is used."** A signal the policy never consults
  is a silent no-op; verify it's consumed, not just emitted.
- **Validate from the trace, not the scoreboard.** A win can be noise; confirm the
  intended mechanism actually fired.

## Provenance — never trust an unverified green result

- **Change one component at a time** so the next evaluation is attributable.
- **Rebuild after every change** — a stale artifact reads as "the change did nothing."
- **Upload freely; submit rarely.** Uploading a new policy version is routine and
  doesn't touch any league — it's how you get a testable artifact for experience
  requests. **Submitting to a league is the irreversible, champion-making action** —
  submit only when the player is demonstrably better and the human has approved.
  *Not* submitting is your rollback.
- **Keep a version log** mapping each uploaded version to the changes it carries, so
  you always know what each version is testing and capable of.
- **Use explicit positive/negative controls** — a silent fallback can run a reference
  player, not yours; a verified A/B beats a source review.
- Stay alert to **local↔live drift**, **stale rotating IDs / docs**, **over-reading a
  small batch**, and **position-based score joins** — the classic looked-like-success
  failures.
