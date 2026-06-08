# The Player Improvement Loop

A high-level, game-agnostic playbook for iteratively optimizing a competitive
game-playing **player** (an agent that perceives a game, forms beliefs, and acts).
This is my (the coding agent's) reference for *how the work flows* and *what the
loop requires of me* — deliberately free of API/CLI/tool specifics, which drift
and go stale. Those live in the per-lab READMEs and are re-verified live each
time; this document is the durable conceptual layer.

It was distilled from a large corpus of prior player-improvement sessions. Treat
it as a living document: revise it as the lab teaches us more.

---

## 0. The one thing to internalize first

**The human originates the jumps; I make them real and tell the truth about
whether they landed.**

Every qualitative leap in player capability in the historical record — reframing
an ad-hoc score as a principled probabilistic model, inventing a new behavioral
mode from game first-principles, adding a whole belief layer — *originated with
the human*. My autonomous proposals tend to be incremental patches. So the loop
is not "agent optimizes player while human supervises." It is closer to: **the
human is the strategist and the eyes; I am the implementer, the instrument-maker,
the measurer, and the gate-keeper of correctness.** My highest-leverage job is to
make the human's strategic judgment *cheap and well-informed* — by building the
observability that reveals where a jump is possible, surfacing decision-ready
options, and measuring rigorously enough that he can trust what changed.

Designing for autonomy means widening what I can do *between* his decisions —
not replacing the decisions.

---

## 1. The macro loop

```
        ┌──────────────────────────────────────────────────────────────────┐
        │                                                                  │
        ▼                                                                  │
   [DIRECTION]      a hypothesis about why we underperform, or a new        │
   (human-led)      capability worth adding. Usually human-originated.      │
        │                                                                  │
        ▼                                                                  │
   [DESIGN]         update the living design doc / model / state machine;   │
   (human + me)     agree the *model* before writing code.                 │
        │                                                                  │
        ▼                                                                  │
   [IMPLEMENT]      change one component: a behavior, a belief, a threshold.│
   (me)                                                                     │
        │                                                                  │
        ▼                                                                  │
   ╔═══ GATE 1: LOCAL CORRECTNESS ═══════════════════════════════════════╗ │
   ║ tests green · clean lifecycle (connect→play→exit) · run a local      ║ │
   ║ episode and WATCH it · confirm the change does what was intended     ║ │  inner
   ╚══════════════════════════════════════════════════════════════════════╝ │  loop
        │  (fails → back to IMPLEMENT)                                       │ (fast)
        ▼                                                                  │
   [BUILD ARTIFACT] package the player for the real competition environment │
   (me)                                                                     │
        │                                                                  │
        ▼                                                                  │
   ╔═══ GATE 2: HUMAN APPROVAL ══════════════════════════════════════════╗ │
   ║ shipping is public + irreversible + spends scarce live games.        ║ │
   ║ Explicit go-ahead required.                                          ║ │
   ╚══════════════════════════════════════════════════════════════════════╝ │
        │                                                                  │
        ▼                                                                  │
   [SHIP]           submit as a new VERSION; the prior best stays as the    │  outer
   (me, gated)      baseline/champion until something beats it.            │  loop
        │                                                                  │ (slow)
        ▼                                                                  │
   [MEASURE]        run a BATCH of games vs the real field; break results   │
   (me)             down by role/opponent; apply statistical rigor.        │
        │                                                                  │
        ▼                                                                  │
   [DIAGNOSE]       compare good-but-not-top games against the field;       │
   (me + human eyes)pull replays + traces; localize the failure mechanism. │
        │                                                                  │
        └──────────────────────────────────────────────────────────────────┘
```

The two **gates** are the spine. Gate 1 exists so I never spend slow, public,
scarce live games proving something a local test could have caught. Gate 2 sits
on the single irreversible outward action and belongs to the human.

---

## 2. Two interleaved loops

The work runs at two very different time constants. **Deciding which loop a
change belongs in is itself a recurring judgment.**

| | **Inner loop** | **Outer loop** |
|---|---|---|
| Time constant | minutes | hours–days |
| Where | local | live competition |
| Autonomy | I run it autonomously | human-gated to enter |
| What it answers | "is the change correct / does it do what I intended?" | "is the player actually more competitive?" |
| Cost | cheap, repeatable | slow, scarce, public, rate-limited |
| Leans on | observability I build myself | the real opponent field |

**Allocation rule:** anything falsifiable by watching one local game stays in the
inner loop. The outer loop is reserved for what local play *cannot* reveal —
performance against the live field, opponents I don't have locally, and emergent
dynamics over many games. Live data is a scarce instrument, not a debugger; don't
reach for it to answer a question a local replay would settle.

---

## 3. The stages, in detail

### 3.1 Direction (human-led)
A direction is a *behavioral theory* ("good opponents in role X won't dwell, so
dwell-evidence is mostly noise") or a new capability worth adding. The human
originates most directions; he watches play, forms a causal hypothesis, and hands
me a model to build. When I propose, I propose *incrementally* — useful, but not
where the jumps come from.

**My job here:** surface decision-ready forks, not a fait accompli. When several
approaches are plausible, lay out the meaningful options with enough context
(tradeoffs, expected effect, cost) that the human can decide. Number the open
design decisions and carry them as explicit forks rather than silently
pre-deciding. Welcome and invite pushback; a grounded objection from me that
saves a wrong direction is high-value, but the call is his.

### 3.2 Design (human + me)
**Design precedes code.** Update the living design doc and sketch the model /
state machine, iterate with the human until the *model* is agreed, then implement.
The doc is the cross-session memory of a long campaign: it records *why* (decisions
and tradeoffs), lets a fresh session re-orient, and keeps a moving target coherent.
Slice big campaigns into ordered, independently-reviewable phases.

**Guard against doc/code drift.** Stale design docs naming things that no longer
exist send investigations down dead ends. Reconcile doc against implementation as
part of the work, and treat any mismatch as a finding.

### 3.3 Implement (me, autonomous)
Change **one** component at a time so the next measurement is attributable. Keep
tuning knobs in a typed, overridable config layer *separate from logic* so they
can be swept and reported without touching code. Get the structure right first;
leave the numbers open to tune later.

### 3.4 Gate 1 — local correctness (me, autonomous)
Before anything ships: tests green, types/lint clean, a clean protocol lifecycle
(connect → play → exit cleanly), and — critically — **run a local game and watch
it.** Confirm the change produces the *intended behavior*, judged from the
player's own trace, not merely that a game completed. This gate is cheap; honor it
every time.

### 3.5 Build artifact (me, autonomous)
Package the player for the **real competition environment**, which is not my dev
machine — architecture, entrypoint, and policy-resolution must match where it will
actually run. **Always rebuild after a code change**; testing a stale artifact and
concluding "the change did nothing" is a classic wasted cycle.

### 3.6 Gate 2 — human approval to ship (human)
Submitting is public, irreversible, and consumes scarce live games. I package and
locally test freely; I **submit only on explicit go-ahead.** Same for merging the
work that underlies it — I hold at the phase boundary rather than treating my own
merge as permission.

### 3.7 Ship (me, gated)
Submit as a **new version** of a stably-named policy. The previous best remains the
active baseline/champion until something demonstrably beats it — which makes
**rollback nearly free**: a regressing candidate isn't "undone," it's simply not
promoted. Re-query the live competition's identifiers every time; they rotate, and
a stale identifier silently points at a dead leaderboard.

### 3.8 Measure (me) — see §4
### 3.9 Diagnose (me + human eyes) — see §5

---

## 4. Measurement: how to know if a change helped

**The single most important discipline in the loop, and the one most often gotten
wrong by intuition.**

### 4.1 The unit of evaluation is a *batch*, never a single game
Three independent sources of variance swamp any single game:
- **Within-game stochasticity** — score distributions are wide and skewed; the
  standard deviation can exceed the mean, with a few big wins dragging the average
  up. One sample tells you almost nothing.
- **Role/seat asymmetry** — the same policy can be strong in one role and broken in
  another, and roles have wildly different baseline scores. A game exercises one
  role assignment, so it measures at most half the player.
- **Opponent dependence** — performance is only meaningful relative to *whom* you
  played. Choose the field deliberately (typically the live top-N, excluding your
  own entries), and force balanced role coverage rather than trusting random draws.

### 4.2 Decompose before judging — aggregate score is a trap
Never trust one headline number. Cut results by:
- **Role** (the most important cut — an aggregate "wins most games" has historically
  hidden one role being completely broken),
- **Opponent / matchup** (pairwise, not just "vs the field"),
- **Behavioral sub-metrics** (wins, mean *and* median score, and action counters
  like "objectives completed" / "attacks made"). These can disagree, and the
  disagreement localizes *why* a score is what it is.

Be aware that the competition's headline ranking is often a *role-conditioned*
statistic, so the raw score distribution can be bimodal by hidden role — averaging
across roles produces a number corresponding to no real game state.

### 4.3 Statistical rigor — separate signal from noise
When asking "is A really different from B" over batch distributions:
- report **effect sizes**, not just point means (standardized mean difference,
  rank-based delta, full-distribution distance);
- run **two families of test** (mean-based and rank-based) — they answer different
  questions and disagree on skewed data;
- apply **multiple-comparison correction** across all the pairs you compare, and
  report corrected values.

The payoff is avoiding confident wrong conclusions: historically, a leaderboard
that *looked* cleanly ranked by mean survived correction in only one pair — the
rest was noise. High per-game variance + few games = underpowered; **pool matched
batches to gain power** before making strong claims. Skipping this means
attributing a noise swing to your last change and shipping a "fix" for a
difference that doesn't exist.

### 4.4 Local vs live, and the degenerate-fixture trap
- **Local eval proves the artifact *works*** (speaks the protocol, loads the right
  policy, produces a score) — *not* that it's competitive. Local opponents are
  often trivial baselines; beating them proves connectivity and basic competence
  only.
- **Live eval proves it's *competitive*** — the only regime trusted for
  competitive judgments, because only there do you face the real top-N under real
  conditions.
- **Traps:** degenerate local fixtures legitimately score zero (a zero is *not* a
  broken player — don't act on it); fresh leaderboards show everyone at max until
  matches accumulate (don't read them yet); and joining a score back to the right
  player/role by list *position* is unsafe — validate against the authoritative
  per-policy field, or every downstream breakdown is silently corrupted.

### 4.5 Cost shapes cadence
Live games are slow and run-to-completion with no cancel. So: filter cheaply
(local gate) before spending live budget; spend live budget on **decision-critical
batches** (does this candidate beat the champion in *both* roles?); run
asynchronously — submit the batch, stop babysitting the wait, and put the value in
the *results*; and when a batch reveals a clear qualitative failure, pivot to
forensics on the games you already have rather than buying more games.

---

## 5. Diagnosis: from "it lost" to "it does X in situation Y because Z"

**You cannot debug an outcome, only a trace.** The result ("lost", "got killed")
carries almost no diagnostic information; every investigation pivots immediately to
the player's internal reasoning stream.

### 5.1 Observability is something I build, not something I'm given
The player must externalize its own reasoning so its behavior is inspectable:
- **per-decision reason traces** — active mode/strategy, the options considered, the
  one chosen, and a human-readable *why* on each action (these reason strings are
  the workhorse of diagnosis);
- **belief/perception snapshots** — what the player *believed* (positions, role
  beliefs, occupancy estimates), so you can compare belief against ground truth at a
  given moment;
- **tick-keyed lines** so a human's "around tick 1750 it started thrashing" maps to
  a precise slice;
- **tiered verbosity** — low-noise event-driven lines by default (a deep dive can
  produce hundreds of thousands of lines), with an opt-in firehose;
- **replays** for the outside-observer view. Diagnosis happens at the *seam*
  between the replay (what the body did) and the trace (what it was thinking) —
  remember visible effects can lag the causing decision by many ticks.

If I can't see the behavior, I can't improve it. Building the instrument often
*precedes* the fix.

### 5.2 Triage — inspect by failure class, never watch everything
Aggregate first, then sample *representative worst cases per failure class* (e.g. a
full-objective loss vs a different failure pattern). The most informative game is
the most *surprising* one — a loss that "should have been a win," where the gap
between expectation and outcome localizes the bug. Use a small seed sweep to
separate "happens every game" from "happens on this seed," and verify the
*environment* matched production before blaming the player.

### 5.3 Name the layer — the first diagnostic question
A failure isn't diagnosed until you've placed it in a layer, because the layer
determines where the fix goes:
- **Perception** — the player misreads the raw world.
- **Belief / modeling** — perception is fine, but the model built on it is wrong or
  missing (e.g. no route/destination inference over correct position percepts).
- **Strategy / policy** — perception and belief are right, the decision rule is
  wrong. Common archetypes: *thrashing/limit cycles* from a threshold with no
  hysteresis; *over-narrow activation* where a mode is entered on a loose predicate
  but acts on a stricter one.
- **Execution / control** — the decision is right but actuation lags or is rejected
  (momentum, conflicting inputs, dropped actions).

Keep **operations failures** ("can't connect / build / complete a game") strictly
separate from **behavior failures** ("runs but plays badly"). They live in
different layers and conflating them wastes effort. The discriminating question:
*did it perceive/believe correctly and choose badly, or choose reasonably given a
wrong belief?* — which requires the trace to show belief and choice at the same
tick.

### 5.4 Ground truth beats inference
When the player's view, the viewer, or the tooling could be lying, go to the
game's **authoritative source / logs** and verify empirically — don't chain
inferences on a shaky base. Prefer the least-surprising, most-authoritative source;
confirm assumptions (the config matches production, the new signal is actually
consumed, the kill/event log says what you think) before building on them. A
parity oracle against the game's own logic is the gold standard for a perception
port.

### 5.5 Surprise is the trigger
Treat your own surprise and confusion as signal, not noise to smooth over. A
human-pointed surprise ("why did it leave without doing the task?") turns an
open-ended "why did we lose" into a bounded forensic question. A self-detected
surprise ("the signal fires but is never used") often redirects the fix entirely.
Confusion gets a post-mortem with a root cause, not a paper-over.

---

## 6. Hypothesis discipline (how a diagnosis becomes a change)

A diagnosis is not actionable until it **names a specific mechanism** *and*
**predicts an observable effect**:
1. **Localize to a mechanism with evidence** — pin it to a specific rule/timer/
   threshold and the trace line that proves it.
2. **Propose a scoped change** addressing *that* mechanism only.
3. **Pre-register the expected effect** — ideally as a test written *before* the
   run that encodes the predicted belief/behavior. The test is the hypothesis made
   falsifiable; if the player doesn't produce it, the hypothesis is wrong
   regardless of whether the score moved.
4. **Distinguish "capability exists" from "capability is used"** — a new signal the
   policy never consults is a silent no-op. Verify it's actually consumed, not just
   emitted.
5. **Validate from the trace, not just the scoreboard** — confirm the intended
   mechanism fired. A win can be noise; the trace shows the change actually did what
   you claimed.

---

## 7. The human-in-the-loop contract

### 7.1 Where the human is essential
- **Originating directions and strategic reframes** — every big jump. I implement
  what he designs; I don't pretend to own the strategy.
- **Judging gameplay quality** — I run games but I cannot reliably tell a good game
  from a bad one. He supplies that signal from watching replays.
- **Resolving the open design forks** and choosing what to pursue next.
- **The ship/merge gate** — the irreversible, public actions.

### 7.2 Where I run autonomously
Local implement/test/watch iteration; building artifacts; running and harvesting
local games; **building observability tooling**; running and analyzing measurement
batches; documentation audits; preparing the change up to the gate. Inside a phase
and inside the inner loop, autonomy is wide.

### 7.3 The propose-and-pause boundary (do not violate)
"**Then let's do X**" means *we* do X — which means starting that work *with the
human in the loop*, not immediately chaining into it. When a thread of work
finishes, **propose the next step and pause**; do not auto-chain into unrequested
work, especially strategy/gameplay changes. Scope creep is a correction the human
has had to issue repeatedly; pre-empt it. When he explicitly fences a task as
operations-only, do not drift into behavior changes.

### 7.4 Kinds of human intervention to expect (and serve well)
Direction-origination · replay-diagnosis-with-hypothesis (often "don't change code
yet, just investigate") · world-model corrections (verify against source) ·
prioritization/sequencing one thread at a time · scope-creep veto · hard
simplify/pivot/"step back to the north star" · "instrument before you fix" ·
demands for a post-mortem on an error · and frequent low-content approvals that
just confirm I'm on the rails he laid. Most of my turns should make his next
intervention *cheaper*: clear options, visible behavior, trustworthy numbers.

---

## 8. Anti-patterns (looked-like-success-but-wasn't)

The throughline: **never trust a green-looking result whose provenance you didn't
verify.**
- **Stale artifact** — tested the old build; the change appears to do nothing.
- **Silent fallback** — launch flags not passed explicitly, so the runner ran a
  *reference* player, not yours. Use explicit positive/negative controls; an A/B
  with verified launches beats a source-review.
- **Degenerate fixture** — a zero from a trivial local fixture read as failure (or a
  pass on a degenerate mission read as competitive success).
- **Local↔live drift** — local artifacts/replays are not a faithful proxy for live;
  architecture/timing differences flip behavior.
- **Stale identifiers / docs** — rotating competition IDs pointing at dead
  leaderboards; design docs naming things that no longer exist.
- **Over-reading a small batch** — attributing a noise swing to your last change.
- **Position-based score joins** — mislabeling which role/player a score belongs to.
- **A signal that's emitted but never consumed** — a live-but-inert capability.

---

## 9. What this means for the lab

The lab's job is to make every stage above **cheaper and more trustworthy**:
- a clean way to run measurement batches and produce role/opponent/behavioral
  breakdowns with proper statistics;
- a home for experiment configs, results, and the diagnosis-to-hypothesis record;
- enough observability tooling that watching a game and reading a trace is fast;
- and a discipline that keeps me on the right side of the two gates.

The thing the lab should *not* try to automate away is §7.1 — the human's
direction-origination and gameplay-quality judgment. Optimize for putting him in
the best possible position to make those calls.
