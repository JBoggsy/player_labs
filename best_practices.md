# Best practices for the improvement cycle

A small, **battle-tested, game/world-agnostic** set of practices for the
evaluate → diagnose → improve loop, distilled from many prior optimization
campaigns. `AGENTS.md` tells you to read these. Treat them as your defaults, and
**warn the human if a request would contravene one** before proceeding (then do
what they decide).

## Speed first — iterations per day is the KPI

Everything below serves one goal: **more iterations through the loop, faster.** The
loop's cost is dominated by the agent being careful, not by the agent being wrong —
a broken upload costs one free eval round; a cautious afternoon costs the whole
afternoon. Defaults:

- **Write code fast; ship it now.** Make the focused change, rebuild, upload, move on.
  No polishing, no defensive code, no restructuring "while you're in there", no test
  scaffolding around the change.
- **No smoke tests, no pre-upload gate.** Upload straight after the rebuild. The next
  experience request both catches breakage and measures gameplay — one step, hosted,
  free, parallel. Local runs (`coworld-local-run`) are a *debugging tool* for when an
  eval shows the artifact can't even connect/play — never a routine step.
- **Only the most critical testing survives.** Run a test only when it's the fastest
  path to an answer you need right now — a pure function you just changed, a parser
  against a captured fixture. Never test-first, never a suite run as ritual, never
  "just to be safe."
- **Careful is reserved for the irreversible.** League submission (the human's gate)
  and destroying data. Everything else — code, uploads, versions, evals — is cheap
  and retryable; treat hesitation there as the real cost.
- **Rigor lives in *reading* results, not in shipping code.** The measurement and
  diagnosis disciplines below are about not fooling yourself when you interpret an
  eval — they gate *conclusions*, not uploads. Don't let them slow the ship step.

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
- **🚩 NO CAUSAL CLAIM WITHOUT THE FALSIFYING QUERY — this is the single most-violated discipline; treat every "because / since / due to" in your own draft as an un-run query, not a conclusion.** When a result appears, the reflex is to narrate a plausible mechanism and ship it as a finding. *Every* such mechanism has **observable preconditions**, and the query to check them is almost always one cheap join away — and it *repeatedly* overturns the story, often showing the **opposite**. This failure recurred **three times in a single session**, each refuted by one query: (1) "self-report helps us win by voting a crewmate out" → ejections were ~1%; nobody gets voted out. (2) "self-report helps win" → the win delta was **not even significant** (p=0.12) — there was no effect to explain. (3) "the crew-aware room change hurt because it put us in crowds where kills get witnessed" → the data showed the **reverse**: we moved *less* and were near *fewer* crew, alone *more* often. The mechanism wasn't subtly wrong, it was backwards. **The procedure, every time, before writing the "why":** (a) **is the effect even real?** effect size + a significance test (a 10-pt swing at n=100 may be noise); (b) **name what this mechanism would make observable, and what the *competing* mechanism would** — including a game rule you may have forgotten (e.g. meetings teleport all players home); (c) **run the query that separates them and report it, refutations included.** Watch your own language: borrowed metaphors ("snowball", "momentum") smuggle in a model the game doesn't have. A claim about *why* is not done until a number distinguishes it from the alternatives — and you should expect to be wrong about half the time, so go look.
- **Normalize every stat by seat-holding.** When a policy occupies a different number
  of roster seats than others (round-robin with duplicates, or any uneven roster),
  *always* report **per-seat-game rates, never raw totals** — a policy with 4 of 8
  seats racks up ~4× the totals (wins, kills, chat, votes) for the same per-seat skill.
  Two traps beyond the obvious: (1) **counting non-events as events** (e.g. an
  abstain/skip message logged as "chat") inflates volume — exclude them first; (2)
  **team-outcome metrics carry a composition confound that per-seat normalization does
  NOT remove** — in a team game with a *fixed* roster, the team result is determined by
  who's on the *other* team, so a policy's "team win rate" entangles its own skill with
  its seat-mates' and opponents' identities. Per-seat rates fix the totals problem;
  isolating individual contribution to a team outcome needs a **controlled design**
  (vary one seat, hold the rest fixed) or at least conditioning on composition.
  Individual stats (kills, tasks) are clean per-seat; team stats (win) are not.
- **Experience requests are your primary eval — they aren't scarce.** They run many
  episodes in parallel on Softmax infra and are currently free, so use them liberally
  rather than rationing them; just **target them to the question** (matched roles when
  the change was role-specific; the specific opponents the policy struggles against)
  and harvest async (the value is in the results, not babysitting the wait) — the
  streaming pipeline (the `coworld-experience-requests` skill, step 4) makes the
  harvest overlap the run by default, so "async" costs nothing.
- **Local runs are a debugging tool — not a gate, never comparative.** Don't run
  locally before uploading; upload and let the eval speak. Drop to a local run only
  when an eval shows the artifact can't connect/play and you need to watch it fail.
  You generally can't download and run other users' policies locally anyway, so
  **all competitive judgment comes from experience requests.** (A local zero from a
  trivial fixture is still not a broken player; and join scores to role/player by the
  authoritative per-policy field, never by list position.)

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
- **Pre-register the expected effect** — one written sentence predicting what the
  eval will show, *before* the run. Costs nothing, keeps the readout honest. (Not a
  test suite — a prediction.)
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
